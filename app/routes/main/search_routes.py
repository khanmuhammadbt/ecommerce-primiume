from flask import Blueprint, flash, jsonify, redirect, render_template, request, session, url_for

from app.models.analytics import record_product_cart_event
from app.models.catalog import get_product, get_products_by_ids, search_products
from app.models.order import initialize_cart

main_search_bp = Blueprint('main_search_bp', __name__)


@main_search_bp.route('/search')
def search():
    initialize_cart()
    query = request.args.get('q', '').strip()
    page = request.args.get('page', 1)
    if query:
        matching = search_products(query, page=page, per_page=20)
    else:
        matching = []
    return render_template('search.html', products=matching, query=query, title='Search')


@main_search_bp.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    initialize_cart()
    
    # Handle both JSON and form data requests
    if request.is_json:
        data = request.get_json()
        product_id = data.get('product_id')
    else:
        product_id = request.form.get('product_id')
    
    if not product_id:
        message = 'Product not found.'
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 400
        else:
            flash(message, 'error')
            return redirect(request.referrer or url_for('main_home_bp.home'))

    product = get_product(int(product_id))
    if product is None:
        message = 'Product not found.'
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 404
        else:
            flash(message, 'error')
            return redirect(request.referrer or url_for('main_home_bp.home'))

    current_cart_quantity = int(session['cart'].get(product_id, 0) or 0)
    if product.get('quantity', 0) <= 0 or current_cart_quantity >= int(product.get('quantity', 0)):
        message = 'This product is out of stock.'
        if request.is_json:
            return jsonify({'success': False, 'message': message}), 400
        else:
            flash(message, 'error')
            return redirect(request.referrer or url_for('main_home_bp.home'))

    session['cart'][product_id] = current_cart_quantity + 1
    session.modified = True
    record_product_cart_event(
        int(product_id),
        user_session_id=session.get('sid'),
        user_ip=request.remote_addr,
        quantity=1,
        source_page=request.referrer or request.path,
    )
    
    message = f'Added "{product["name"]}" to cart.'
    
    # Calculate total cart count
    total_cart_count = sum(int(qty) for qty in session.get('cart', {}).values())
    
    if request.is_json:
        return jsonify({
            'success': True,
            'message': message,
            'cart_count': total_cart_count,
            'product_name': product['name']
        }), 200
    else:
        flash(message, 'success')
        return redirect(request.referrer or url_for('main_home_bp.home'))


@main_search_bp.route('/remove_from_cart', methods=['POST'])
def remove_from_cart():
    initialize_cart()
    product_id = request.form.get('product_id')
    if product_id in session['cart']:
        session['cart'].pop(product_id)
        session.modified = True
        flash('Item removed from cart.', 'success')
    return redirect(url_for('main_cart_bp.cart'))


@main_search_bp.route('/update_cart_quantity', methods=['POST'])
def update_cart_quantity():
    initialize_cart()
    product_id = request.form.get('product_id')
    action = request.form.get('action')
    if not product_id or product_id not in session['cart']:
        flash('Invalid cart item.', 'error')
        return redirect(url_for('main_cart_bp.cart'))

    current_quantity = int(session['cart'].get(product_id, 0) or 0)
    product = get_product(int(product_id))
    if product is None:
        flash('Product not found.', 'error')
        return redirect(url_for('main_cart_bp.cart'))

    available_stock = int(product.get('quantity', 0) or 0)

    if action == 'increase':
        if current_quantity >= available_stock:
            flash('Cannot increase quantity; not enough stock.', 'error')
        else:
            session['cart'][product_id] = current_quantity + 1
            session.modified = True
    elif action == 'decrease':
        if current_quantity <= 1:
            session['cart'].pop(product_id, None)
            session.modified = True
            flash('Item removed from cart.', 'success')
        else:
            session['cart'][product_id] = current_quantity - 1
            session.modified = True
    else:
        flash('Invalid cart action.', 'error')

    return redirect(url_for('main_cart_bp.cart'))

