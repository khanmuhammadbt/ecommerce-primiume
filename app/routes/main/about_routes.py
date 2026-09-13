from flask import Blueprint, render_template, request

from app.models.admin import get_page_content
from app.models.order import initialize_cart

main_about_bp = Blueprint('main_about_bp', __name__)


@main_about_bp.route('/about')
def about():
    initialize_cart()
    content = get_page_content('about')
    return render_template('about.html', title='About Us', dynamic_content=content)

