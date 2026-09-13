from flask import Blueprint, render_template

from app.models.catalog import get_all_products
from app.models.order import initialize_cart

shop_bp = Blueprint('shop_bp', __name__)


@shop_bp.route('/shop')
def shop():
    initialize_cart()
    return render_template('shop.html', products=get_all_products(), title='Shop')

