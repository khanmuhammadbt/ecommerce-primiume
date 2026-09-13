from flask import Blueprint, render_template

from app.models.admin import get_page_content
from app.models.order import initialize_cart

main_contact_bp = Blueprint('main_contact_bp', __name__)


@main_contact_bp.route('/contact')
def contact():
    initialize_cart()
    content = get_page_content('contact')
    return render_template('contact.html', title='Contact', dynamic_content=content)

