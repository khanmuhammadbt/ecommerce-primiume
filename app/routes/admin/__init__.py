from .about_routes import admin_about_bp, admin_edit_about
from .contact_routes import admin_contact_bp, admin_edit_contact
from .dashboard_routes import (
    admin_dashboard_bp,
    admin_add_hero_slide,
    admin_change_password,
    admin_create_offer,
    admin_dashboard,
    admin_dashboard_analytics,
    admin_delete_hero_slide,
    admin_delete_offer,
    admin_delete_order,
    admin_update_delivery_charge,
    admin_update_hero,
    admin_update_hero_slide,
    admin_update_homepage_filters,
    admin_update_offer,
    admin_update_order_status,
    admin_update_trust_badge,
)
from .login_routes import admin_login_bp, admin_login, admin_logout


def register_admin_routes(app):
    for blueprint in (
        admin_login_bp,
        admin_dashboard_bp,
        admin_about_bp,
        admin_contact_bp,
    ):
        app.register_blueprint(blueprint)

    app.add_url_rule('/admin/login', endpoint='main.admin_login', view_func=admin_login, methods=['GET', 'POST'])
    app.add_url_rule('/admin/logout', endpoint='main.admin_logout', view_func=admin_logout)
    app.add_url_rule('/admin/dashboard', endpoint='main.admin_dashboard', view_func=admin_dashboard)
    app.add_url_rule('/admin/dashboard/analytics', endpoint='main.admin_dashboard_analytics', view_func=admin_dashboard_analytics)
    app.add_url_rule('/admin/about', endpoint='main.admin_edit_about', view_func=admin_edit_about, methods=['GET', 'POST'])
    app.add_url_rule('/admin/contact', endpoint='main.admin_edit_contact', view_func=admin_edit_contact, methods=['GET', 'POST'])
    app.add_url_rule('/admin/hero', endpoint='main.admin_update_hero', view_func=admin_update_hero, methods=['POST'])
    app.add_url_rule('/admin/hero/add', endpoint='main.admin_add_hero_slide', view_func=admin_add_hero_slide, methods=['POST'])
    app.add_url_rule('/admin/hero/<int:slide_id>/update', endpoint='main.admin_update_hero_slide', view_func=admin_update_hero_slide, methods=['POST'])
    app.add_url_rule('/admin/hero/<int:slide_id>/delete', endpoint='main.admin_delete_hero_slide', view_func=admin_delete_hero_slide, methods=['POST'])
    app.add_url_rule('/admin/filters', endpoint='main.admin_update_homepage_filters', view_func=admin_update_homepage_filters, methods=['POST'])
    app.add_url_rule('/admin/delivery_charge', endpoint='main.admin_update_delivery_charge', view_func=admin_update_delivery_charge, methods=['POST'])
    app.add_url_rule('/admin/trust_badges/<int:badge_id>/update', endpoint='main.admin_update_trust_badge', view_func=admin_update_trust_badge, methods=['POST'])
    app.add_url_rule('/admin/offers', endpoint='main.admin_create_offer', view_func=admin_create_offer, methods=['POST'])
    app.add_url_rule('/admin/offers/<int:offer_id>/update', endpoint='main.admin_update_offer', view_func=admin_update_offer, methods=['POST'])
    app.add_url_rule('/admin/offers/<int:offer_id>/delete', endpoint='main.admin_delete_offer', view_func=admin_delete_offer, methods=['POST'])
    app.add_url_rule('/admin/change-password', endpoint='main.admin_change_password', view_func=admin_change_password, methods=['POST'])
    app.add_url_rule('/admin/orders/<int:order_id>/status', endpoint='main.admin_update_order_status', view_func=admin_update_order_status, methods=['POST'])
    app.add_url_rule('/admin/orders/<int:order_id>/delete', endpoint='main.admin_delete_order', view_func=admin_delete_order, methods=['POST'])

