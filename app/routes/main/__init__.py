from .about_routes import about, main_about_bp
from .cart_routes import cart, main_cart_bp
from .checkout_routes import checkout, main_checkout_bp
from .contact_routes import contact, main_contact_bp
from .home_routes import home, main_home_bp, llms_txt, robots_txt, sitemap_xml
from .search_routes import add_to_cart, main_search_bp, remove_from_cart, search, update_cart_quantity
from app.routes.api_routes import api_bp


def register_main_routes(app):
    app.register_blueprint(api_bp)
    for blueprint in (
        main_home_bp,
        main_about_bp,
        main_contact_bp,
        main_search_bp,
        main_cart_bp,
        main_checkout_bp,
    ):
        app.register_blueprint(blueprint)

    app.add_url_rule('/', endpoint='main.home', view_func=home)
    app.add_url_rule('/about', endpoint='main.about', view_func=about)
    app.add_url_rule('/contact', endpoint='main.contact', view_func=contact)
    app.add_url_rule('/robots.txt', endpoint='main.robots_txt', view_func=robots_txt)
    app.add_url_rule('/llms.txt', endpoint='main.llms_txt', view_func=llms_txt)
    app.add_url_rule('/sitemap.xml', endpoint='main.sitemap_xml', view_func=sitemap_xml)
    app.add_url_rule('/search', endpoint='main.search', view_func=search)
    app.add_url_rule('/cart', endpoint='main.cart', view_func=cart)
    app.add_url_rule('/add_to_cart', endpoint='main.add_to_cart', view_func=add_to_cart, methods=['POST'])
    app.add_url_rule('/remove_from_cart', endpoint='main.remove_from_cart', view_func=remove_from_cart, methods=['POST'])
    app.add_url_rule('/update_cart_quantity', endpoint='main.update_cart_quantity', view_func=update_cart_quantity, methods=['POST'])
    app.add_url_rule('/checkout', endpoint='main.checkout', view_func=checkout, methods=['GET', 'POST'])

