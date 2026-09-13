from contextlib import closing

from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.models.admin import get_site_setting
from app.models.catalog import get_products_by_ids
from app.models.order import get_offer_by_code, initialize_cart, save_order
from app.models.shared import get_connection

main_checkout_bp = Blueprint('main_checkout_bp', __name__)


@main_checkout_bp.route('/checkout', methods=['GET', 'POST'])
def checkout():
    initialize_cart()
    cart_items = []
    subtotal = 0
    product_ids = [int(product_id) for product_id in session.get('cart', {}) if product_id is not None]
    products = get_products_by_ids(product_ids)
    missing_product_ids = [product_id for product_id in session.get('cart', {}) if product_id is not None and int(product_id) not in products]
    if missing_product_ids:
        flash('One or more products in your cart are no longer available. Please review your cart.', 'error')
        return redirect(url_for('main_cart_bp.cart'))

    coupon_code = ''
    discount_text = ''
    discount_amount = 'PKR 0'

    for product_id_str, quantity in session.get('cart', {}).items():
        product = products.get(int(product_id_str))
        if product:
            available_quantity = int(product.get('quantity', 0) or 0)
            if available_quantity <= 0:
                flash(f'"{product["name"]}" is out of stock.', 'error')
                return redirect(url_for('main_cart_bp.cart'))
            if int(quantity) > available_quantity:
                flash(f'Only {available_quantity} unit(s) of "{product["name"]}" remain in stock.', 'error')
                return redirect(url_for('main_cart_bp.cart'))
            price_value = float(product.get('sale_price', product.get('price', 0)))
            item_total = round(price_value * quantity, 2)
            subtotal += item_total
            price_text = product.get('sale_price_display') if product.get('sale_percent', 0) > 0 else product['price']
            cart_items.append({
                'id': product['id'],
                'name': product['name'],
                'price': price_text,
                'regular_price': product['price'] if product.get('sale_percent', 0) > 0 else None,
                'quantity': quantity,
                'image': product['image'],
                'category': product['category'],
                'sale_percent': product.get('sale_percent', 0),
                'item_total': f"PKR {item_total:.2f}",
            })

    raw_delivery_charge = get_site_setting('delivery_charge', '250')
    try:
        delivery_charge = int(float(raw_delivery_charge))
    except (TypeError, ValueError):
        delivery_charge = 250
    total = subtotal + delivery_charge
    action = request.form.get('action', 'place_order') if request.method == 'POST' else 'place_order'
    form_user_details = session.get('user_details', {})

    if request.method == 'POST':
        customer_name = request.form.get('name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        address = request.form.get('address', '').strip()
        coupon_code = request.form.get('coupon_code', '').strip().upper()
        form_user_details = {'name': customer_name, 'email': email, 'phone': phone, 'address': address}

        offer = get_offer_by_code(coupon_code) if coupon_code else None
        if coupon_code and offer is None:
            discount_text = 'Invalid coupon code.'
            discount_amount = 'PKR 0'
            total = subtotal + delivery_charge
            if action == 'place_order':
                flash('Coupon code is not valid. Please check and try again.', 'error')
                return render_template('checkout.html', cart=cart_items, subtotal=f"PKR {subtotal}", delivery_charge=f"PKR {delivery_charge}", total=f"PKR {total}", discount_amount=discount_amount, discount_text=discount_text, coupon_code=coupon_code, user_details=form_user_details, title='Checkout')
        elif offer is not None:
            discount_pct = 0
            if offer.get('discount'):
                match = __import__('re').search(r'(\d+(?:\.\d+)?)', str(offer['discount']))
                if match:
                    discount_pct = float(match.group(1))
            if discount_pct > 0:
                discount_value = round((discount_pct / 100.0) * subtotal, 2)
                total = max(subtotal - discount_value, 0) + delivery_charge
                discount_text = f"{discount_pct}% off ({offer['code']})"
                discount_amount = f"PKR {discount_value:.2f}"
                if action == 'apply':
                    flash(f'Coupon applied: {discount_text}', 'success')
            else:
                discount_text = 'Coupon code is valid but contains no discount.'
                discount_amount = 'PKR 0'
                total = subtotal + delivery_charge
                if action == 'place_order':
                    flash('Coupon code is valid but contains no discount.', 'error')
                    return render_template('checkout.html', cart=cart_items, subtotal=f"PKR {subtotal}", delivery_charge=f"PKR {delivery_charge}", total=f"PKR {total}", discount_amount=discount_amount, discount_text=discount_text, coupon_code=coupon_code, user_details=form_user_details, title='Checkout')

        if action == 'place_order':
            if not all([customer_name, email, phone, address]):
                flash('Please provide your full details before placing the order.', 'error')
                return render_template('checkout.html', cart=cart_items, subtotal=f"PKR {subtotal}", delivery_charge=f"PKR {delivery_charge}", total=f"PKR {total}", discount_amount=discount_amount, discount_text=discount_text, coupon_code=coupon_code, user_details=form_user_details, title='Checkout')

            if coupon_code and offer is None:
                total = subtotal + delivery_charge
                discount_amount = 'PKR 0'
                discount_text = ''

            session['user_details'] = {'name': customer_name, 'email': email, 'phone': phone, 'address': address}
            session['last_coupon_code'] = coupon_code
            session['last_discount_text'] = discount_text
            with closing(get_connection()) as conn:
                for item in cart_items:
                    product = products.get(item['id'])
                    if product is None:
                        flash('One or more products in your cart are no longer available. Please review your cart.', 'error')
                        return redirect(url_for('main_cart_bp.cart'))
                    remaining_quantity = max(0, int(product.get('quantity', 0) or 0) - int(item['quantity']))
                    conn.execute('UPDATE products SET quantity = ? WHERE id = ?', (remaining_quantity, item['id']))
                conn.commit()
            order_id = save_order(
                customer_name,
                email,
                phone,
                address,
                cart_items,
                f"PKR {total}",
                coupon_code=coupon_code,
                discount_text=discount_text,
            )
            session['last_order_id'] = order_id
            session['last_order_total'] = f"PKR {total}"
            session['cart'] = {}
            session.modified = True
            flash('Order placed successfully. We will process it shortly.', 'success')
            return redirect(url_for('main_cart_bp.cart'))

    return render_template('checkout.html', cart=cart_items, subtotal=f"PKR {subtotal}", delivery_charge=f"PKR {delivery_charge}", total=f"PKR {total}", discount_amount=discount_amount, discount_text=discount_text, coupon_code=coupon_code, user_details=session.get('user_details', {}), title='Checkout')

