from .product_detail_routes import (
    admin_create_product,
    admin_delete_product,
    admin_update_product,
    product_detail_bp,
    product_details,
    product_review,
)
from .shop_routes import shop, shop_bp


def register_products_routes(app):
    for blueprint in (
        product_detail_bp,
        shop_bp,
    ):
        app.register_blueprint(blueprint)

    app.add_url_rule('/product/<int:product_id>', endpoint='main.product_details', view_func=product_details, methods=['GET'])
    app.add_url_rule('/product/<int:product_id>/<path:product_slug>', endpoint='main.product_details_slug', view_func=product_details, methods=['GET'])
    app.add_url_rule('/shop', endpoint='main.shop', view_func=shop)
    app.add_url_rule('/admin/products', endpoint='main.admin_create_product', view_func=admin_create_product, methods=['POST'])
    app.add_url_rule('/product/<int:product_id>/review', endpoint='main.product_review', view_func=product_review, methods=['POST'])
    app.add_url_rule('/admin/products/<int:product_id>/update', endpoint='main.admin_update_product', view_func=admin_update_product, methods=['POST'])
    app.add_url_rule('/admin/products/<int:product_id>/delete', endpoint='main.admin_delete_product', view_func=admin_delete_product, methods=['POST'])

