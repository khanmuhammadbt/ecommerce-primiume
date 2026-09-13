import os
from datetime import timedelta
from flask import Flask, render_template, request, session, url_for, send_from_directory
from flask_socketio import SocketIO
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress

from app.config import Config

csrf = CSRFProtect()
socketio = SocketIO(cors_allowed_origins='*', manage_session=False, async_mode='threading')


def create_app():
    package_dir = os.path.dirname(__file__)
    template_dir = os.path.join(package_dir, 'templates')
    static_dir = os.path.join(package_dir, 'static')
    upload_dir = Config.UPLOAD_FOLDER

    app = Flask(
        __name__,
        template_folder=template_dir,
        static_folder=static_dir,
    )
    app.config.from_object(Config)
    app.config.setdefault('WTF_CSRF_TIME_LIMIT', 3600)
    app.config.setdefault('PERMANENT_SESSION_LIFETIME', timedelta(days=10))
    app.config.setdefault('SESSION_REFRESH_EACH_REQUEST', True)

    @app.before_request
    def _apply_testing_csrf_setting():
        if app.config.get('TESTING', False):
            app.config['WTF_CSRF_ENABLED'] = False
        elif app.config.get('WTF_CSRF_ENABLED') is None:
            app.config['WTF_CSRF_ENABLED'] = True

        session.permanent = True

    csrf.init_app(app)
    socketio.init_app(app)
    app.extensions['socketio'] = socketio

    # Enable response compression (gzip/deflate) for HTML/CSS/JS
    Compress(app)

    from app.live_viewers import register_live_product_viewers
    register_live_product_viewers(socketio)

    @app.context_processor
    def inject_global_site_context():
        cart = session.get('cart', {})
        if not isinstance(cart, dict):
            cart = {}
        try:
            cart_count = sum(int(quantity) for quantity in cart.values())
        except (TypeError, ValueError):
            cart_count = 0

        path = request.path
        default_description = 'Shop electronics, accessories, and daily deals at Banta Bazar.'
        if path == '/about':
            default_description = 'Learn about Banta Bazar and our commitment to quality electronics and dependable service.'
        elif path == '/contact':
            default_description = 'Contact Banta Bazar for support, inquiries, or help with your order.'
        elif path == '/cart':
            default_description = 'Review your selected products and complete your order securely at Banta Bazar.'
        elif path == '/checkout':
            default_description = 'Checkout securely and place your electronics order with confidence at Banta Bazar.'
        elif path == '/search':
            default_description = 'Search Banta Bazar for the products you need, from everyday essentials to premium electronics.'
        elif path.startswith('/product/'):
            default_description = 'Discover premium products and special deals at Banta Bazar.'
        elif path == '/shop':
            default_description = 'Browse the full catalog of electronics and accessories available at Banta Bazar.'

        return {
            'cart_count': cart_count,
            'meta_description': default_description,
            'canonical_url': request.url_root.rstrip('/') + path,
            'og_image_url': request.url_root.rstrip('/') + url_for('static', filename='images/logo.png'),
            'structured_data': {
                '@context': 'https://schema.org',
                '@type': 'Store',
                'name': 'Banta Bazar',
                'url': request.url_root.rstrip('/'),
                'description': default_description,
                'sameAs': ['https://www.example.com/banta-bazar'],
                'address': {
                    '@type': 'PostalAddress',
                    'addressLocality': 'Lahore',
                    'addressCountry': 'PK',
                },
            },
        }

    os.makedirs(upload_dir, exist_ok=True)

    from app.models.admin import init_admin_db
    from app.models.analytics import init_product_analytics_tables
    from app.routes.admin import register_admin_routes
    from app.routes.main import register_main_routes
    from app.routes.products import register_products_routes

    init_admin_db()
    init_product_analytics_tables()
    register_main_routes(app)
    register_admin_routes(app)
    register_products_routes(app)

    frontend_dist = os.path.abspath(os.path.join(package_dir, '..', 'frontend', 'dist'))

    @app.route('/assets/<path:filename>')
    def frontend_assets(filename):
        return send_from_directory(os.path.join(frontend_dist, 'assets'), filename)

    @app.errorhandler(404)
    def handle_not_found(error):
        return render_template(
            '404.html',
            title='Page not found',
            meta_description='The page you requested could not be found.',
            canonical_url=request.url_root.rstrip('/') + request.path,
            og_image_url=request.url_root.rstrip('/') + url_for('static', filename='images/logo.png'),
            structured_data={
                '@context': 'https://schema.org',
                '@type': 'WebPage',
                'name': 'Page not found',
                'url': request.url_root.rstrip('/') + request.path,
            },
        ), 404

    return app

