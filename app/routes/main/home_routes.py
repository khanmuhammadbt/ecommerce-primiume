import os

from flask import Blueprint, Response, flash, redirect, render_template, request, session, url_for, jsonify, send_from_directory

from app.models.admin import (
    get_homepage_filters,
    get_homepage_hero,
    get_homepage_hero_slides,
    get_homepage_trust_badges,
)
from app.models.catalog import get_all_categories, get_all_product_ids, get_all_products, search_products
from app.models.order import get_all_offers, initialize_cart
from app.models.shared import get_connection

main_home_bp = Blueprint('main_home_bp', __name__)


@main_home_bp.context_processor
def inject_cart_count():
    initialize_cart()
    return {'cart_count': sum(session['cart'].values())}


@main_home_bp.context_processor
def inject_seo_defaults():
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


@main_home_bp.route('/')
def home():
    frontend_dist = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..', 'frontend', 'dist'))
    if os.path.exists(os.path.join(frontend_dist, 'index.html')):
        return send_from_directory(frontend_dist, 'index.html')

    initialize_cart()
    category = request.args.get('category', '').strip()
    price = request.args.get('price', '').strip()
    page_size = 6
    products = get_all_products(page=1, per_page=page_size + 1, category=category, price_range=price)
    has_more = len(products) > page_size
    products = products[:page_size]
    hero_slides = get_homepage_hero_slides()
    homepage_category_filters = get_homepage_filters('category')
    actual_categories = get_all_categories()
    merged_categories = []
    seen = set()
    for item in homepage_category_filters:
        if item['value'] not in seen:
            merged_categories.append(item)
            seen.add(item['value'])
    for category_name in actual_categories:
        if category_name not in seen:
            merged_categories.append({'label': category_name, 'value': category_name})
            seen.add(category_name)

    return render_template(
        'index.html',
        products=products,
        has_more=has_more,
        hero=get_homepage_hero(),
        hero_slides=hero_slides,
        trust_badges=get_homepage_trust_badges(),
        offers=get_all_offers(),
        title='Home',
        selected_category=category,
        selected_price=price,
        category_filters=merged_categories,
        price_filters=get_homepage_filters('price'),
    )


@main_home_bp.route('/load-more-products')
def load_more_products():
    category = request.args.get('category', '').strip()
    price = request.args.get('price', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    per_page = 6
    products = get_all_products(page=page, per_page=per_page + 1, category=category, price_range=price)
    has_more = len(products) > per_page
    products = products[:per_page]
    html = render_template('partials/product_cards.html', products=products)

    return jsonify({
        'html': html,
        'has_more': has_more,
    })
    category = request.args.get('category', '').strip()
    price = request.args.get('price', '').strip()
    try:
        page = max(1, int(request.args.get('page', 1)))
    except (ValueError, TypeError):
        page = 1

    per_page = 12
    products = get_all_products(page=page, per_page=per_page + 1, category=category, price_range=price)
    has_more = len(products) > per_page
    products = products[:per_page]

    return {
        'products': products,
        'has_more': has_more,
    }


@main_home_bp.route('/robots.txt')
def robots_txt():
    content = 'User-agent: *\nAllow: /\nSitemap: ' + request.url_root.rstrip('/') + '/sitemap.xml\n'
    return Response(content, mimetype='text/plain')


@main_home_bp.route('/llms.txt')
def llms_txt():
    content = (
        'Banta Bazar\n'
        'Banta Bazar is an electronics and accessories storefront focused on quality products, dependable service, clear pricing, and practical shopping guidance.\n'
        'Primary pages:\n'
        '- /\n'
        '- /about\n'
        '- /contact\n'
        '- /shop\n'
        'Sitemap: ' + request.url_root.rstrip('/') + '/sitemap.xml\n'
    )
    return Response(content, mimetype='text/plain')


@main_home_bp.route('/sitemap.xml')
def sitemap_xml():
    base_url = request.url_root.rstrip('/')
    product_urls = ''.join(
        f'<url><loc>{base_url}/product/{product_id}</loc></url>'
        for product_id in get_all_product_ids()
    )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
        f'<url><loc>{base_url}/</loc></url>'
        f'<url><loc>{base_url}/about</loc></url>'
        f'<url><loc>{base_url}/contact</loc></url>'
        f'<url><loc>{base_url}/shop</loc></url>'
        f'{product_urls}'
        '</urlset>'
    )
    return Response(xml, mimetype='application/xml')

