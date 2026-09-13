from flask import Blueprint, jsonify, request, session
from flask_wtf.csrf import generate_csrf

from app.models.admin import get_homepage_hero_slides
from app.models.catalog import get_all_categories, get_all_products, get_product
from app.models.order import get_cart_snapshot, initialize_cart

api_bp = Blueprint('api_bp', __name__, url_prefix='/api')


def product_json(product):
    return {
        'id': product['id'],
        'name': product['name'],
        'category': product.get('category') or 'General',
        'description': product.get('description') or '',
        'price': product.get('price') or '0',
        'currency': product.get('currency') or 'PKR',
        'image': product.get('image') or '',
        'images': product.get('images') or [product.get('image') or ''],
        'quantity': int(product.get('quantity') or 0),
        'sale_percent': int(product.get('sale_percent') or 0),
        'sale_price': product.get('sale_price') or 0,
        'sale_price_display': product.get('sale_price_display') or '',
        'average_rating': product.get('average_rating') or 0,
        'review_count': product.get('review_count') or 0,
    }


def cart_json():
    items, total = get_cart_snapshot()
    return {
        'items': items,
        'total': total,
        'count': sum(int(item['quantity']) for item in items),
    }


@api_bp.get('/products')
def products():
    category = request.args.get('category', '').strip()
    query = request.args.get('q', '').strip().lower()
    price = request.args.get('price', '').strip()
    items = get_all_products(category=category, price_range=price)
    if query:
        items = [
            item for item in items
            if query in item['name'].lower()
            or query in (item.get('description') or '').lower()
            or query in item['category'].lower()
        ]
    return jsonify({
        'products': [product_json(item) for item in items],
        'categories': get_all_categories(),
    })


@api_bp.get('/homepage')
def homepage():
    return jsonify({'hero_slides': get_homepage_hero_slides()})


@api_bp.get('/csrf-token')
def csrf_token():
    return jsonify({'csrf_token': generate_csrf()})


@api_bp.get('/products/<int:product_id>')
def product(product_id):
    item = get_product(product_id)
    if item is None:
        return jsonify({'message': 'Product not found'}), 404
    return jsonify({'product': product_json(item)})


@api_bp.get('/cart')
def get_cart():
    initialize_cart()
    return jsonify(cart_json())


@api_bp.post('/cart')
def add_cart():
    initialize_cart()
    data = request.get_json(silent=True) or {}
    product_id = str(data.get('product_id', ''))
    item = get_product(int(product_id)) if product_id.isdigit() else None
    if item is None:
        return jsonify({'message': 'Product not found'}), 404
    current = int(session['cart'].get(product_id, 0) or 0)
    if current >= int(item.get('quantity') or 0):
        return jsonify({'message': 'This product is out of stock'}), 400
    session['cart'][product_id] = current + 1
    session.modified = True
    return jsonify(cart_json())


@api_bp.patch('/cart/<int:product_id>')
def update_cart(product_id):
    initialize_cart()
    data = request.get_json(silent=True) or {}
    quantity = max(0, int(data.get('quantity', 0) or 0))
    key = str(product_id)
    if quantity == 0:
        session['cart'].pop(key, None)
    else:
        item = get_product(product_id)
        if item is None:
            return jsonify({'message': 'Product not found'}), 404
        session['cart'][key] = min(quantity, int(item.get('quantity') or 0))
    session.modified = True
    return jsonify(cart_json())


@api_bp.delete('/cart/<int:product_id>')
def remove_cart(product_id):
    initialize_cart()
    session['cart'].pop(str(product_id), None)
    session.modified = True
    return jsonify(cart_json())
