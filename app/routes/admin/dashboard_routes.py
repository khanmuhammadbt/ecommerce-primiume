import logging
from contextlib import closing
from datetime import datetime, timedelta, timezone
from math import ceil

from flask import Blueprint, current_app, flash, jsonify, redirect, render_template, request, session, url_for

from app.models.admin import (
    delete_homepage_hero_slide,
    get_homepage_filters,
    get_homepage_hero,
    get_homepage_hero_slides,
    get_homepage_trust_badges,
    get_site_setting,
    save_homepage_filters,
    save_homepage_hero,
    save_homepage_hero_slide,
    save_homepage_trust_badge,
    set_site_setting,
)
from app.models.analytics import (
    get_category_analytics_summary,
    get_customer_behavior_analytics,
    get_product_analytics_summary,
)
from app.models.catalog import (
    get_all_products,
    save_image_file_for_hero,
)
from app.models.order import (
    get_all_offers,
    get_all_orders,
    send_admin_success,
)
from app.models.shared import get_connection
from app.models.order import is_admin

admin_dashboard_bp = Blueprint('admin_dashboard_bp', __name__)
SECURITY_LOGGER = logging.getLogger('banta_bazar.security')


def _get_login_key(username):
    forwarded_for = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    client_ip = forwarded_for or request.remote_addr or 'unknown'
    return f'{username}:{client_ip}'


def _get_remaining_lockout_minutes(lock_until):
    if not lock_until:
        return 0
    remaining_seconds = max(0, int((lock_until - datetime.now(timezone.utc)).total_seconds()))
    return max(1, ceil(remaining_seconds / 60))


def _to_decimal(value):
    try:
        return float(value or 0)
    except (TypeError, ValueError):
        return 0.0


def _build_date_series(rows, days):
    today = datetime.now(timezone.utc).date()
    row_map = {row['date']: _to_decimal(row['revenue']) for row in rows}
    series = []
    for offset in range(days - 1, -1, -1):
        day = today - timedelta(days=offset)
        date_str = day.strftime('%Y-%m-%d')
        series.append({'date': date_str, 'revenue': float(row_map.get(date_str, 0))})
    return series


def get_dashboard_stats():
    today = datetime.now(timezone.utc).date()
    today_string = today.strftime('%Y-%m-%d')
    week_string = (today - timedelta(days=6)).strftime('%Y-%m-%d')
    month_string = today.replace(day=1).strftime('%Y-%m-%d')
    month_30_string = (today - timedelta(days=29)).strftime('%Y-%m-%d')
    customers_7d_string = week_string

    with closing(get_connection()) as conn:
        total_orders_today = conn.execute(
            'SELECT COUNT(*) AS count FROM orders WHERE DATE(created_at) = ?',
            (today_string,),
        ).fetchone()['count']
        total_orders_week = conn.execute(
            'SELECT COUNT(*) AS count FROM orders WHERE DATE(created_at) >= ?',
            (week_string,),
        ).fetchone()['count']
        total_orders_all_time = conn.execute(
            'SELECT COUNT(*) AS count FROM orders',
        ).fetchone()['count']

        total_revenue_today = conn.execute(
            'SELECT COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE DATE(o.created_at) = ? AND o.status = ?',
            (today_string, 'delivered'),
        ).fetchone()['revenue']
        total_revenue_month = conn.execute(
            'SELECT COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE DATE(o.created_at) >= ? AND o.status = ?',
            (month_string, 'delivered'),
        ).fetchone()['revenue']
        total_revenue_all_time = conn.execute(
            'SELECT COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE o.status = ?',
            ('delivered',),
        ).fetchone()['revenue']

        pending_orders_count = conn.execute(
            "SELECT COUNT(*) AS count FROM orders WHERE status = 'pending'",
        ).fetchone()['count']
        out_of_stock_count = conn.execute(
            'SELECT COUNT(*) AS count FROM products WHERE quantity <= 0',
        ).fetchone()['count']
        total_customers_count = conn.execute(
            'SELECT COUNT(*) AS count FROM customers',
        ).fetchone()['count']

        revenue_rows = conn.execute(
            'SELECT DATE(o.created_at) AS date, COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS revenue FROM order_items oi JOIN orders o ON oi.order_id = o.id WHERE DATE(o.created_at) >= ? AND o.status = ? GROUP BY DATE(o.created_at) ORDER BY DATE(o.created_at)',
            (month_30_string, 'delivered'),
        ).fetchall()
        daily_revenue_last_30_days = _build_date_series(revenue_rows, 30)
        daily_revenue_last_7_days = daily_revenue_last_30_days[-7:]

        status_rows = conn.execute(
            'SELECT status, COUNT(*) AS count FROM orders GROUP BY status',
        ).fetchall()
        order_status_breakdown = {
            'pending': 0,
            'on_the_way': 0,
            'delivered': 0,
        }
        for row in status_rows:
            order_status_breakdown[row['status']] = row['count']

        top_selling_products = [
            {
                'name': row['name'],
                'quantity_sold': row['quantity_sold'],
            }
            for row in conn.execute(
                'SELECT p.name AS name, SUM(oi.quantity) AS quantity_sold FROM order_items oi JOIN products p ON oi.product_id = p.id GROUP BY p.id ORDER BY quantity_sold DESC LIMIT 5',
            ).fetchall()
        ]

        category_wise_sales = [
            {
                'category': row['category'],
                'sales': _to_decimal(row['sales']),
            }
            for row in conn.execute(
                'SELECT COALESCE(c.name, ?) AS category, COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS sales FROM order_items oi JOIN products p ON oi.product_id = p.id LEFT JOIN categories c ON p.category_id = c.id GROUP BY category ORDER BY sales DESC',
                ('Uncategorized',),
            ).fetchall()
        ]

        low_stock_products = [
            {
                'name': row['name'],
                'category': row['category'],
                'quantity': row['quantity'],
            }
            for row in conn.execute(
                'SELECT p.name AS name, COALESCE(c.name, ?) AS category, p.quantity AS quantity FROM products p LEFT JOIN categories c ON p.category_id = c.id WHERE p.quantity < 5 ORDER BY p.quantity ASC, p.name ASC',
                ('Uncategorized',),
            ).fetchall()
        ]

        recent_orders = [
            {
                'id': row['id'],
                'customer_name': row['customer_name'] or 'Guest',
                'total': f"PKR {_to_decimal(row['total']):,.2f}",
                'status': row['status'],
                'date': row['created_at'],
            }
            for row in conn.execute(
                "SELECT o.id, c.full_name AS customer_name, o.status AS status, o.created_at, COALESCE(SUM(oi.quantity * (oi.unit_price + 0)), 0) AS total FROM orders o LEFT JOIN customers c ON o.customer_id = c.id LEFT JOIN order_items oi ON oi.order_id = o.id WHERE o.status IN ('pending', 'on_the_way') GROUP BY o.id, c.full_name, o.status, o.created_at ORDER BY o.created_at DESC LIMIT 10",
            ).fetchall()
        ]

        coupon_usage_stats = [
            {
                'code': row['code'],
                'title': row['title'],
                'usage_count': row['usage_count'],
            }
            for row in conn.execute(
                'SELECT f.code AS code, f.title AS title, COUNT(o.id) AS usage_count FROM offers f LEFT JOIN orders o ON o.coupon_code = f.code GROUP BY f.id ORDER BY usage_count DESC, f.code ASC',
            ).fetchall()
        ]

        customer_rows = conn.execute(
            'SELECT DATE(created_at) AS date, COUNT(*) AS count FROM customers WHERE DATE(created_at) >= ? GROUP BY DATE(created_at) ORDER BY DATE(created_at)',
            (customers_7d_string,),
        ).fetchall()
        new_customers_per_day_last_7_days = []
        date_map = {row['date']: row['count'] for row in customer_rows}
        for offset in range(6, -1, -1):
            day = today - timedelta(days=offset)
            date_str = day.strftime('%Y-%m-%d')
            new_customers_per_day_last_7_days.append({'date': date_str, 'count': date_map.get(date_str, 0)})

        product_analytics = get_product_analytics_summary()
        category_analytics = get_category_analytics_summary()

    return {
        'total_orders': {
            'today': total_orders_today,
            'this_week': total_orders_week,
            'all_time': total_orders_all_time,
        },
        'total_revenue': {
            'today': float(total_revenue_today),
            'this_month': float(total_revenue_month),
            'all_time': float(total_revenue_all_time),
        },
        'pending_orders_count': pending_orders_count,
        'out_of_stock_count': out_of_stock_count,
        'total_customers_count': total_customers_count,
        'daily_revenue_last_7_days': daily_revenue_last_7_days,
        'daily_revenue_last_30_days': daily_revenue_last_30_days,
        'order_status_breakdown': order_status_breakdown,
        'top_selling_products': top_selling_products,
        'category_wise_sales': category_wise_sales,
        'low_stock_products': low_stock_products,
        'recent_orders': recent_orders,
        'coupon_usage_stats': coupon_usage_stats,
        'new_customers_per_day_last_7_days': new_customers_per_day_last_7_days,
        'product_analytics': product_analytics,
        'category_analytics': category_analytics,
        **get_customer_behavior_analytics(),
    }


@admin_dashboard_bp.route('/admin/api/dashboard-stats')
def admin_dashboard_stats_api():
    if not is_admin():
        return jsonify({'error': 'Unauthorized access'}), 401
    return jsonify(get_dashboard_stats())


@admin_dashboard_bp.route('/admin/api/orders')
def admin_orders_api():
    if not is_admin():
        return jsonify({'error': 'Unauthorized access'}), 401

    orders = get_all_orders(request.args.get('search', ''))
    return jsonify({'orders': orders})


@admin_dashboard_bp.route('/admin/dashboard/analytics')
def admin_dashboard_analytics():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    return render_template('admin/analytics.html', title='Admin Dashboard Analytics')


@admin_dashboard_bp.route('/admin/dashboard')
def admin_dashboard():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    orders = get_all_orders()
    pending_orders = sum(1 for order in orders if order.get('status') == 'pending')
    products = get_all_products()
    out_of_stock_products = [product for product in products if int(product.get('quantity', 0)) <= 0]

    with closing(get_connection()) as conn:
        available_categories = [row['name'] for row in conn.execute('SELECT name FROM categories ORDER BY name').fetchall()]
    homepage_category_filters = get_homepage_filters('category')
    merged_category_filters = []
    seen = set()
    for item in homepage_category_filters:
        if item['value'] not in seen:
            merged_category_filters.append(item)
            seen.add(item['value'])
    for category_name in available_categories:
        if category_name not in seen:
            merged_category_filters.append({'label': category_name, 'value': category_name})
            seen.add(category_name)

    return render_template(
        'admin_dashboard.html',
        title='Admin Dashboard',
        products=products,
        offers=get_all_offers(),
        hero_settings=get_homepage_hero(),
        hero_slides=get_homepage_hero_slides(),
        trust_badges=get_homepage_trust_badges(),
        available_categories=available_categories,
        category_filters=merged_category_filters,
        price_filters=get_homepage_filters('price'),
        delivery_charge=get_site_setting('delivery_charge', '250'),
        orders=orders,
        pending_orders=pending_orders,
        out_of_stock_products=out_of_stock_products,
    )


@admin_dashboard_bp.route('/admin/hero', methods=['POST'])
def admin_update_hero():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    eyebrow = request.form.get('eyebrow', '').strip()
    headline = request.form.get('headline', '').strip()
    description = request.form.get('description', '').strip()
    primary_button_text = request.form.get('primary_button_text', '').strip() or 'Shop Now'
    secondary_button_text = request.form.get('secondary_button_text', '').strip() or 'View Products'
    image_url = request.form.get('image', '').strip()
    image_file = request.files.get('image_file')

    if image_file and image_file.filename:
        image_url = save_image_file_for_hero(image_file, headline or eyebrow or 'hero')

    if not image_url:
        image_url = get_homepage_hero()['image']

    save_homepage_hero(eyebrow, headline, description, image_url)
    return send_admin_success('Hero section updated successfully.', 'hero-section')


@admin_dashboard_bp.route('/admin/hero/add', methods=['POST'])
def admin_add_hero_slide():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    eyebrow = request.form.get('eyebrow', '').strip()
    headline = request.form.get('headline', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    image_url = request.form.get('image', '').strip()
    image_file = request.files.get('image_file')

    if image_file and image_file.filename:
        image_url = save_image_file_for_hero(image_file, f"slide-new-{headline or eyebrow or 'hero'}")

    existing_slides = get_homepage_hero_slides()
    next_id = max((item['id'] for item in existing_slides), default=0) + 1

    if not image_url:
        image_url = 'https://images.unsplash.com/photo-1524758631624-e2822e304c36?auto=format&fit=crop&w=1200&q=80'

    save_homepage_hero_slide(next_id, eyebrow, headline, description, image_url, category)
    return send_admin_success('Hero slide created successfully.', 'hero-section')


@admin_dashboard_bp.route('/admin/hero/<int:slide_id>/update', methods=['POST'])
def admin_update_hero_slide(slide_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    eyebrow = request.form.get('eyebrow', '').strip()
    headline = request.form.get('headline', '').strip()
    description = request.form.get('description', '').strip()
    category = request.form.get('category', '').strip()
    primary_button_text = request.form.get('primary_button_text', '').strip() or 'Shop Now'
    secondary_button_text = request.form.get('secondary_button_text', '').strip() or 'View Products'
    image_url = request.form.get('image', '').strip()
    image_file = request.files.get('image_file')

    if image_file and image_file.filename:
        image_url = save_image_file_for_hero(image_file, f"slide-{slide_id}-{headline or eyebrow or 'hero'}")

    if not image_url:
        slide = next((item for item in get_homepage_hero_slides() if item['id'] == slide_id), None)
        image_url = slide['image'] if slide else ''

    save_homepage_hero_slide(slide_id, eyebrow, headline, description, image_url, category)
    return send_admin_success('Hero slide updated successfully.', 'hero-section')


@admin_dashboard_bp.route('/admin/hero/<int:slide_id>/delete', methods=['POST'])
def admin_delete_hero_slide(slide_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    delete_homepage_hero_slide(slide_id)
    flash('Hero slide deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard', _anchor='hero-section'))


@admin_dashboard_bp.route('/admin/filters', methods=['POST'])
def admin_update_homepage_filters():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    categories = []
    for raw_value in request.form.getlist('categories'):
        for item in str(raw_value).splitlines():
            cleaned = item.strip()
            if cleaned:
                categories.append({'label': cleaned, 'value': cleaned})

    price_ranges = []
    for raw_value in request.form.getlist('price_ranges'):
        for item in str(raw_value).splitlines():
            cleaned = item.strip()
            if not cleaned:
                continue
            if ':' in cleaned:
                label, value = cleaned.split(':', 1)
                price_ranges.append({'label': label.strip(), 'value': value.strip()})
            else:
                price_ranges.append({'label': cleaned, 'value': cleaned})

    save_homepage_filters('category', categories)
    save_homepage_filters('price', price_ranges)
    return send_admin_success('Homepage filters updated successfully.', 'filters-section')


@admin_dashboard_bp.route('/admin/delivery_charge', methods=['POST'])
def admin_update_delivery_charge():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    delivery_charge = (request.form.get('delivery_charge') or '').strip()
    try:
        delivery_charge_value = int(float(delivery_charge))
        if delivery_charge_value < 0:
            raise ValueError()
    except ValueError:
        flash('Delivery charge must be a valid non-negative number.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    set_site_setting('delivery_charge', str(delivery_charge_value))
    flash('Delivery charge updated successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard', _anchor='delivery-settings-section'))


@admin_dashboard_bp.route('/admin/trust_badges/<int:badge_id>/update', methods=['POST'])
def admin_update_trust_badge(badge_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    icon = request.form.get('icon', '').strip()

    if not title or not description:
        flash('Badge title and description are required.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    save_homepage_trust_badge(badge_id, title, description, icon)
    return send_admin_success('Trust badge updated successfully.', 'badges-section')


@admin_dashboard_bp.route('/admin/offers', methods=['POST'])
def admin_create_offer():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    discount = request.form.get('discount', '').strip()
    code = request.form.get('code', '').strip()

    if not title or not description or not discount or not code:
        flash('Offer title, description, discount, and code are required.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    with closing(get_connection()) as conn:
        conn.execute(
            'INSERT OR IGNORE INTO offers (title, description, discount, code) VALUES (?, ?, ?, ?)',
            (title, description, f"{discount}% off", code.upper()),
        )
        conn.commit()
    return send_admin_success('Offer created successfully.', 'offers-section')


@admin_dashboard_bp.route('/admin/offers/<int:offer_id>/update', methods=['POST'])
def admin_update_offer(offer_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    discount = request.form.get('discount', '').strip()
    code = request.form.get('code', '').strip()

    if not title or not description or not discount or not code:
        flash('Offer title, description, discount, and code are required.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    with closing(get_connection()) as conn:
        conn.execute(
            'UPDATE offers SET title = ?, description = ?, discount = ?, code = ? WHERE id = ?',
            (title, description, f"{discount}% off", code.upper(), offer_id),
        )
        conn.commit()
    return send_admin_success('Offer updated successfully.', 'offers-section')


@admin_dashboard_bp.route('/admin/offers/<int:offer_id>/delete', methods=['POST'])
def admin_delete_offer(offer_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM offers WHERE id = ?', (offer_id,))
        conn.commit()
    flash('Offer deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))


@admin_dashboard_bp.route('/admin/change-password', methods=['POST'])
def admin_change_password():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    current_password = (request.form.get('current_password') or '').strip()
    new_password = (request.form.get('new_password') or '').strip()
    confirm_password = (request.form.get('confirm_password') or '').strip()

    with closing(get_connection()) as conn:
        row = conn.execute('SELECT password FROM admin_users WHERE username = ?', ('admin',)).fetchone()
        user_hash = row['password'] if row else ''

    if not current_password or not new_password or not confirm_password:
        flash('All password fields are required.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    if new_password != confirm_password:
        flash('New password and confirmation do not match.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    from werkzeug.security import check_password_hash, generate_password_hash

    if not check_password_hash(user_hash, current_password):
        flash('Current password is incorrect.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    with closing(get_connection()) as conn:
        conn.execute('UPDATE admin_users SET password = ? WHERE username = ?', (generate_password_hash(new_password), 'admin'))
        conn.commit()

    flash('Admin password updated successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))


@admin_dashboard_bp.route('/admin/orders/<int:order_id>/status', methods=['POST'])
def admin_update_order_status(order_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    status = (request.form.get('status') or 'pending').strip()
    valid_statuses = {'pending', 'on_the_way', 'delivered'}
    if status not in valid_statuses:
        status = 'pending'

    with closing(get_connection()) as conn:
        conn.execute('UPDATE orders SET status = ? WHERE id = ?', (status, order_id))
        conn.commit()

    status_label = {'pending': 'pending', 'on_the_way': 'on the way', 'delivered': 'delivered'}[status]
    flash(f'Order marked as {status_label}', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))


@admin_dashboard_bp.route('/admin/orders/<int:order_id>/delete', methods=['POST'])
def admin_delete_order(order_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM orders WHERE id = ?', (order_id,))
        conn.commit()

    flash('Order deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

