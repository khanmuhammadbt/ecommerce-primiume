import re
import uuid
from contextlib import closing
from datetime import datetime, timezone

from flask import jsonify, request, session, url_for

from app.models.catalog import get_product, get_products_by_ids, parse_price_value
from app.models.shared import get_connection


def get_all_offers():
    with closing(get_connection()) as conn:
        rows = conn.execute('SELECT id, title, description, discount, code FROM offers ORDER BY id').fetchall()
    return [
        {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'discount': row['discount'],
            'code': row['code'],
        }
        for row in rows
    ]


def initialize_cart():
    if 'sid' not in session:
        session['sid'] = uuid.uuid4().hex
        session.modified = True
    if 'cart' not in session:
        session['cart'] = {}
        session.permanent = True
        session.modified = True


def get_cart_snapshot():
    initialize_cart()
    product_ids = [int(product_id) for product_id in session['cart'].keys() if product_id is not None]
    products = get_products_by_ids(product_ids)
    cart_items = []
    total = 0
    for product_id_str, quantity in session['cart'].items():
        product = products.get(int(product_id_str))
        if product:
            item_total = int(parse_price_value(product['price']) * quantity)
            total += item_total
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': product['price'],
                'quantity': quantity,
                'image': product['image'],
                'category': product['category'],
                'item_total': f"PKR {item_total}"
            })
    return cart_items, total


def get_all_orders(search_query=''):
    search_query = (search_query or '').strip().lower()
    search_filter = ''
    query_params = []
    if search_query:
        if search_query.isdigit():
            search_filter = 'WHERE CAST(o.id AS TEXT) = ?'
            query_params = [search_query]
        else:
            search_filter = '''
                WHERE LOWER(COALESCE(c.full_name, '')) LIKE ?
                   OR LOWER(COALESCE(c.email, '')) LIKE ?
            '''
            search_pattern = f'%{search_query}%'
            query_params = [search_pattern, search_pattern]

    with closing(get_connection()) as conn:
        rows = conn.execute(
            f'''
            SELECT o.id, c.full_name AS customer_name, c.email, c.phone, c.address, o.total, o.status, o.created_at,
                   o.coupon_code, o.discount_text, p.name AS product_name, oi.quantity, oi.item_total
            FROM orders o
            LEFT JOIN customers c ON o.customer_id = c.id
            LEFT JOIN order_items oi ON o.id = oi.order_id
            LEFT JOIN products p ON oi.product_id = p.id
            {search_filter}
            ORDER BY o.id DESC, oi.id ASC
            ''',
            query_params
        ).fetchall()

    orders_by_id = {}
    for row in rows:
        order_id = row['id']
        if order_id not in orders_by_id:
            orders_by_id[order_id] = {
                'id': row['id'],
                'customer_name': row['customer_name'],
                'email': row['email'],
                'phone': row['phone'],
                'address': row['address'],
                'coupon_code': row['coupon_code'],
                'discount_text': row['discount_text'],
                'items_data': [],
                'total': row['total'],
                'status': row['status'],
                'created_at': row['created_at']
            }
        if row['product_name'] is not None:
            orders_by_id[order_id]['items_data'].append({
                'name': row['product_name'],
                'quantity': row['quantity'],
                'item_total': row['item_total'],
            })

    return list(orders_by_id.values())


def get_offer_by_code(code):
    if not code:
        return None
    with closing(get_connection()) as conn:
        row = conn.execute(
            'SELECT id, title, description, discount, code FROM offers WHERE UPPER(code) = ?',
            (code.upper(),)
        ).fetchone()
    if row is None:
        return None
    return {
        'id': row['id'],
        'title': row['title'],
        'description': row['description'],
        'discount': row['discount'],
        'code': row['code']
    }


def parse_discount_percent(discount_text):
    if not discount_text:
        return 0
    match = re.search(r'(\d+(?:\.\d+)?)', str(discount_text))
    if not match:
        return 0
    try:
        return float(match.group(1))
    except ValueError:
        return 0


def save_order(customer_name, email, phone, address, cart_items, total, coupon_code='', discount_text=''):
    with closing(get_connection()) as conn:
        existing_customer = conn.execute('SELECT id FROM customers WHERE email = ?', (email,)).fetchone()
        if existing_customer is None:
            customer_cursor = conn.execute(
                'INSERT INTO customers (full_name, email, phone, address, created_at) VALUES (?, ?, ?, ?, ?)',
                (customer_name, email, phone, address, datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'))
            )
            customer_id = customer_cursor.lastrowid
        else:
            customer_id = existing_customer['id']
            conn.execute(
                'UPDATE customers SET full_name = ?, phone = ?, address = ? WHERE id = ?',
                (customer_name, phone, address, customer_id)
            )

        order_cursor = conn.execute(
            'INSERT INTO orders (customer_id, total, status, created_at, coupon_code, discount_text) VALUES (?, ?, ?, ?, ?, ?)',
            (customer_id, total, 'pending', datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S'), coupon_code, discount_text)
        )
        order_id = order_cursor.lastrowid
        for item in cart_items:
            conn.execute(
                'INSERT INTO order_items (order_id, product_id, quantity, unit_price, item_total) VALUES (?, ?, ?, ?, ?)',
                (order_id, item['id'], item['quantity'], item['price'], item.get('item_total', total))
            )
        conn.commit()
    return order_id


__all__ = [
    'get_all_offers',
    'initialize_cart',
    'get_cart_snapshot',
    'get_all_orders',
    'get_offer_by_code',
    'parse_discount_percent',
    'save_order',
]

