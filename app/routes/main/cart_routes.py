from flask import Blueprint, flash, render_template, request, session, url_for

from app.models.catalog import get_products_by_ids
from app.models.order import initialize_cart

main_cart_bp = Blueprint('main_cart_bp', __name__)


@main_cart_bp.route('/cart')
def cart():
    cart_items = []
    total = 0
    product_ids = [int(product_id) for product_id in session.get('cart', {}) if product_id is not None]
    products = get_products_by_ids(product_ids)
    for product_id_str, quantity in session.get('cart', {}).items():
        product = products.get(int(product_id_str))
        if product:
            price_value = float(product.get('sale_price', product.get('price', 0)))
            item_total = round(price_value * quantity, 2)
            total += item_total
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
    return render_template('cart.html', cart=cart_items, total=f"PKR {total}", title='Cart')

