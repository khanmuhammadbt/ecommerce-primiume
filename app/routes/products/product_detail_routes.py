import sqlite3
from contextlib import closing

from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.models.admin import get_homepage_filters
from app.models.analytics import record_product_view
from app.models.catalog import (
    coerce_image_urls,
    delete_product,
    get_all_products,
    get_or_create_category,
    get_product,
    get_reviews_for_product,
    parse_price_value,
    save_image_file_for_product,
    save_product_review,
)
from app.models.order import initialize_cart, is_admin, is_ajax_request
from app.models.shared import DB_PATH, _slugify, get_connection

product_detail_bp = Blueprint('product_detail_bp', __name__)


@product_detail_bp.route('/product/<int:product_id>')
@product_detail_bp.route('/product/<int:product_id>/<path:product_slug>')
def product_details(product_id, product_slug=None):
    initialize_cart()
    product = get_product(product_id)
    if product is None:
        return render_template('404.html', title='Product not found'), 404

    expected_slug = _slugify(product['name'])
    if product_slug is not None and product_slug != expected_slug:
        return redirect(url_for('product_detail_bp.product_details', product_id=product_id, product_slug=expected_slug), code=301)

    price_value = parse_price_value(product['price'])
    record_product_view(
        product_id,
        user_session_id=session.get('sid'),
        user_ip=request.remote_addr,
        user_agent=request.headers.get('User-Agent'),
        source_page=request.path,
    )
    product_reviews = get_reviews_for_product(product_id)
    review_count = len(product_reviews)
    average_rating = round(sum(review['rating'] for review in product_reviews) / review_count, 1) if review_count else 0.0

    structured_data = {
        '@context': 'https://schema.org',
        '@type': 'Product',
        'name': product['name'],
        'description': product['description'] or f"Shop {product['name']} at Banta Bazar.",
        'image': [product['image']] if product['image'] else [],
        'category': product['category'],
        'brand': {'@type': 'Brand', 'name': 'Banta Bazar'},
        'offers': {
            '@type': 'Offer',
            'priceCurrency': product['currency'] or 'PKR',
            'price': price_value,
            'availability': 'https://schema.org/InStock',
            'url': request.url_root.rstrip('/') + url_for('product_detail_bp.product_details', product_id=product_id, product_slug=expected_slug),
        },
    }
    if review_count > 0:
        structured_data['aggregateRating'] = {
            '@type': 'AggregateRating',
            'ratingValue': average_rating,
            'reviewCount': review_count,
            'bestRating': 5,
            'worstRating': 1,
        }

    return render_template(
        'product_details.html',
        product=product,
        product_reviews=product_reviews,
        average_rating=average_rating,
        review_count=review_count,
        title=product['name'],
        meta_description=f"Shop {product['name']} at Banta Bazar with premium features and competitive prices.",
        canonical_url=request.url_root.rstrip('/') + url_for('product_detail_bp.product_details', product_id=product_id, product_slug=expected_slug),
        structured_data=structured_data,
    )


@product_detail_bp.route('/product/<int:product_id>/review', methods=['POST'])
def product_review(product_id):
    initialize_cart()
    product = get_product(product_id)
    if product is None:
        flash('Product not found.', 'error')
        return redirect(url_for('main_home_bp.home'))

    reviewer_name = (request.form.get('reviewer_name', '') or '').strip()
    rating = request.form.get('rating')
    comment = (request.form.get('comment', '') or '').strip()
    if not rating or not comment:
        flash('Please provide both a rating and a review comment.', 'error')
        return redirect(url_for('product_detail_bp.product_details', product_id=product_id, product_slug=_slugify(product['name'])))

    save_product_review(product_id, reviewer_name, rating, comment)
    flash('Thank you! Your review has been submitted.', 'success')
    return redirect(url_for('product_detail_bp.product_details', product_id=product_id, product_slug=_slugify(product['name'])))


@product_detail_bp.route('/admin/products', methods=['POST'])
def admin_create_product():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    name = (request.form.get('name', '') or '').strip()
    price = (request.form.get('price', '') or '').strip()
    currency = (request.form.get('currency', 'PKR') or 'PKR').strip() or 'PKR'
    category = (request.form.get('category', '') or '').strip()
    new_category = (request.form.get('new_category', '') or '').strip()
    if category == '__new__':
        category = new_category
    description = (request.form.get('description', '') or '').strip()
    quantity = (request.form.get('quantity', '1') or '1').strip()
    sale_percent = (request.form.get('sale_percent', '0') or '0').strip()
    image_url = (request.form.get('image', '') or '').strip()
    image_files = request.files.getlist('image_file')

    try:
        sale_percent_value = max(0, min(100, int(float(sale_percent))))
    except (TypeError, ValueError):
        sale_percent_value = 0

    if not name or not price or not category:
        flash('Product name, price, and category are required.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    quantity_value = max(0, int(quantity) if quantity.isdigit() else 1)

    product_id = None
    with closing(get_connection()) as conn:
        category_id = get_or_create_category(category, conn)
        cursor = conn.execute(
            'INSERT INTO products (name, price, currency, image, category_id, description, quantity, sale_percent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (name, price, currency, image_url, category_id, description, quantity_value, sale_percent_value),
        )
        conn.commit()
        product_id = cursor.lastrowid

    uploaded_urls = []
    for image_index, image_file in enumerate(image_files or []):
        if image_file and image_file.filename:
            uploaded_urls.append(save_image_file_for_product(image_file, product_id, image_index=image_index))

    if uploaded_urls:
        combined_urls = coerce_image_urls(image_url) + uploaded_urls
        image_url = ','.join(combined_urls)
        with closing(get_connection()) as conn:
            conn.execute('UPDATE products SET image = ? WHERE id = ?', (image_url, product_id))
            conn.commit()
    elif image_url:
        image_url = ','.join(coerce_image_urls(image_url))
        with closing(get_connection()) as conn:
            conn.execute('UPDATE products SET image = ? WHERE id = ?', (image_url, product_id))
            conn.commit()

    if category:
        existing_filters = {item['value'] for item in get_homepage_filters('category')}
        if category not in existing_filters:
            from app.models.admin import save_homepage_filters
            save_homepage_filters('category', [
                *[{ 'label': item['label'], 'value': item['value'] } for item in get_homepage_filters('category')],
                {'label': category, 'value': category}
            ])

    return redirect(url_for('admin_dashboard_bp.admin_dashboard', _anchor='add-product-section'))


@product_detail_bp.route('/admin/products/<int:product_id>/update', methods=['POST'])
def admin_update_product(product_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    product = get_product(product_id)
    if product is None:
        flash('Product not found.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    name = (request.form.get('name', '') or '').strip()
    price = (request.form.get('price', '') or '').strip()
    currency = (request.form.get('currency', 'PKR') or 'PKR').strip() or 'PKR'
    category = (request.form.get('category', '') or '').strip()
    new_category = (request.form.get('new_category', '') or '').strip()
    if category == '__new__':
        category = new_category
    description = (request.form.get('description', '') or '').strip()
    quantity = (request.form.get('quantity', str(product.get('quantity', 1))) or str(product.get('quantity', 1))).strip()
    sale_percent = (request.form.get('sale_percent', str(product.get('sale_percent', 0))) or str(product.get('sale_percent', 0))).strip()
    image_url = (request.form.get('image', product['image']) or product['image']).strip()
    image_files = request.files.getlist('image_file')

    try:
        sale_percent_value = max(0, min(100, int(float(sale_percent))))
    except (TypeError, ValueError):
        sale_percent_value = 0

    image_urls = coerce_image_urls(image_url)
    for image_index, image_file in enumerate(image_files or []):
        if image_file and image_file.filename:
            image_urls.append(save_image_file_for_product(image_file, product_id, image_index=image_index))
    if image_urls:
        image_url = ','.join(image_urls)

    quantity_value = max(0, int(quantity) if quantity.isdigit() else product.get('quantity', 1))

    with closing(get_connection()) as conn:
        category_id = get_or_create_category(category, conn)
        conn.execute(
            'UPDATE products SET name = ?, price = ?, currency = ?, image = ?, category_id = ?, description = ?, quantity = ?, sale_percent = ? WHERE id = ?',
            (name, price, currency, image_url, category_id, description, quantity_value, sale_percent_value, product_id),
        )
        conn.commit()

    if category:
        existing_filters = {item['value'] for item in get_homepage_filters('category')}
        if category not in existing_filters:
            from app.models.admin import save_homepage_filters
            save_homepage_filters('category', [
                *[{ 'label': item['label'], 'value': item['value'] } for item in get_homepage_filters('category')],
                {'label': category, 'value': category}
            ])

    if is_ajax_request():
        return jsonify(success=True, message='Product updated successfully.', redirect=url_for('admin_dashboard_bp.admin_dashboard'))

    flash('Product updated successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))


@product_detail_bp.route('/admin/products/<int:product_id>/delete', methods=['POST'])
def admin_delete_product(product_id):
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))

    try:
        delete_product(product_id)
    except sqlite3.IntegrityError:
        flash('Product cannot be deleted because it is referenced by existing orders.', 'error')
        return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

    flash('Product deleted successfully.', 'success')
    return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

