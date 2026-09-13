from flask import Blueprint, flash, redirect, render_template, request, url_for

from app.models.admin import get_page_content, update_page_content
from app.models.order import is_admin, send_admin_success

admin_about_bp = Blueprint('admin_about_bp', __name__)


@admin_about_bp.route('/admin/about', methods=['GET', 'POST'])
def admin_edit_about():
    if not is_admin():
        flash('Please log in to access the admin panel.', 'error')
        return redirect(url_for('admin_login_bp.admin_login'))
    if request.method == 'POST':
        content = request.form.get('content', '').strip()
        update_page_content('about', content)
        return send_admin_success('About page updated.', 'dashboard-overview')
    current = get_page_content('about')
    return render_template('admin_about.html', title='Edit About', content=current)

