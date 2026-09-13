from contextlib import closing

from app.models.admin import init_admin_db
from app.models.analytics import (
    get_customer_behavior_analytics,
    get_category_analytics_summary,
    get_product_analytics_summary,
    record_product_cart_event,
    record_product_view,
)
from app.models.shared import get_connection


def test_product_analytics_summary_and_category_breakdown():
    init_admin_db()

    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM product_cart_events')
        conn.execute('DELETE FROM product_views')
        conn.execute('DELETE FROM reviews')
        conn.execute('DELETE FROM order_items')
        conn.execute('DELETE FROM orders')
        conn.execute('DELETE FROM customers')
        conn.execute('DELETE FROM products')
        conn.execute('DELETE FROM categories')
        conn.execute('INSERT INTO categories (id, name, slug) VALUES (?, ?, ?)', (1, 'Phones', 'phones'))
        conn.execute(
            'INSERT INTO products (id, name, price, currency, image, category_id, description, quantity, sale_percent) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)',
            (1, 'Demo Phone', '25000', 'PKR', 'demo.jpg', 1, 'Test product', 10, 0),
        )
        conn.execute('INSERT INTO reviews (product_id, reviewer_name, rating, comment) VALUES (?, ?, ?, ?)', (1, 'User', 5, 'Great'))
        first_customer = conn.execute(
            'INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)',
            ('New Buyer', 'new@example.com', '03000000001', 'Lahore'),
        ).lastrowid
        returning_customer = conn.execute(
            'INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)',
            ('Returning Buyer', 'returning@example.com', '03000000002', 'Lahore'),
        ).lastrowid
        conn.execute('INSERT INTO orders (customer_id, total) VALUES (?, ?)', (first_customer, '100'))
        conn.execute('INSERT INTO orders (customer_id, total) VALUES (?, ?)', (returning_customer, '100'))
        conn.execute('INSERT INTO orders (customer_id, total) VALUES (?, ?)', (returning_customer, '100'))
        conn.commit()

    record_product_view(1, user_session_id='s1', user_ip='127.0.0.1', user_agent='pytest', source_page='/product/1')
    record_product_view(1, user_session_id='s2', user_ip='127.0.0.1', user_agent='pytest', source_page='/product/1')
    record_product_cart_event(1, user_session_id='s3', user_ip='127.0.0.1', quantity=2, source_page='/search')
    for _ in range(12):
        record_product_cart_event(1, user_session_id='repeat-cart', user_ip='127.0.0.2', source_page='/search')
    record_product_view(1, user_session_id='repeat-view', user_ip='127.0.0.3', user_agent='pytest', source_page='/product/1')
    record_product_view(1, user_session_id='repeat-view', user_ip='127.0.0.3', user_agent='pytest', source_page='/product/1')

    product_rows = get_product_analytics_summary()
    category_rows = get_category_analytics_summary()

    assert any(row['product_id'] == 1 and row['total_views'] == 4 and row['total_add_to_cart'] == 14 for row in product_rows)
    assert any(row['category'] == 'Phones' and row['views_percentage'] >= 0 for row in category_rows)
    assert any(row['category'] == 'Phones' and row['total_rating_count'] == 1 for row in category_rows)

    behavior = get_customer_behavior_analytics()
    assert behavior['repeat_cart_customers'][0]['visitor_id'] == 'repeat-cart'
    assert behavior['repeat_cart_customers'][0]['add_to_cart_count'] == 12
    assert behavior['repeat_view_customers'][0]['visitor_id'] == 'repeat-view'
    assert behavior['repeat_view_customers'][0]['view_count'] == 2
    assert behavior['visitor_overview'] == {
        'total_visitors': 5,
        'new_visitors': 3,
        'returning_visitors': 2,
    }
    assert behavior['orders_customer_breakdown']['new_customer_orders'] == 1
    assert behavior['orders_customer_breakdown']['returning_customer_orders'] == 2
