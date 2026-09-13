import json
import os
import re
import sqlite3
from contextlib import closing
from urllib.parse import urlparse

from flask import current_app, url_for
from werkzeug.utils import secure_filename

from app.utils import save_optimized_image

from app.models.shared import DB_PATH, _slugify, get_connection


def get_or_create_category(category_name, conn=None):
    name = (category_name or 'General').strip() or 'General'
    should_close = conn is None
    conn = conn or get_connection()
    row = conn.execute('SELECT id FROM categories WHERE name = ?', (name,)).fetchone()
    if row is not None:
        category_id = row['id']
        if should_close:
            conn.close()
        return category_id

    cursor = conn.execute(
        'INSERT INTO categories (name, slug) VALUES (?, ?)',
        (name, _slugify(name))
    )
    category_id = cursor.lastrowid
    if should_close:
        conn.commit()
        conn.close()
    return category_id


def get_all_categories():
    with closing(get_connection()) as conn:
        rows = conn.execute('SELECT name FROM categories ORDER BY name').fetchall()
    return [row['name'] for row in rows]


def coerce_image_urls(value):
    if value is None:
        return []

    if isinstance(value, (list, tuple)):
        values = value
    elif isinstance(value, str):
        text = value.strip()
        if not text:
            return []
        if text.startswith('[') and text.endswith(']'):
            try:
                parsed = json.loads(text)
                values = parsed if isinstance(parsed, list) else [parsed]
            except (TypeError, ValueError):
                values = [text]
        else:
            values = re.split(r'[\n,;]+', text)
    else:
        values = [str(value)]

    urls = []
    for item in values:
        item_text = str(item).strip()
        if not item_text:
            continue
        if item_text.startswith('[') and item_text.endswith(']'):
            try:
                nested = json.loads(item_text)
                if isinstance(nested, list):
                    urls.extend(str(entry).strip() for entry in nested if str(entry).strip())
                    continue
            except (TypeError, ValueError):
                pass
        urls.append(item_text)

    seen = set()
    ordered = []
    for url in urls:
        if url not in seen:
            seen.add(url)
            ordered.append(url)
    return ordered


def save_image_file_for_product(image_file, product_id, image_index=None):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    original_filename = secure_filename(image_file.filename)
    # Always save uploads as JPEG to reduce size and standardize format
    if image_index in (None, 0):
        filename = f'{product_id}.jpg'
    else:
        filename = f'{product_id}-{image_index}.jpg'
    image_path = os.path.join(upload_folder, filename)
    # Ensure stream is at start
    try:
        image_file.stream.seek(0)
    except Exception:
        pass
    save_optimized_image(image_file.stream, image_path, max_size=(800, 800), quality=80)
    return url_for('static', filename=f'images/uploads/{filename}')


def save_image_file_for_hero(image_file, hero_name):
    upload_folder = current_app.config['UPLOAD_FOLDER']
    os.makedirs(upload_folder, exist_ok=True)
    original_filename = secure_filename(image_file.filename)
    slug = _slugify(hero_name or 'hero')
    filename = f'hero-{slug}.jpg'
    image_path = os.path.join(upload_folder, filename)
    try:
        image_file.stream.seek(0)
    except Exception:
        pass
    save_optimized_image(image_file.stream, image_path, max_size=(800, 800), quality=80)
    return url_for('static', filename=f'images/uploads/{filename}')


def delete_uploaded_product_image(image_url):
    if not image_url:
        return

    parsed = urlparse(image_url)
    filename = parsed.path
    static_prefix = '/static/'
    if not filename.startswith(static_prefix):
        return

    filename = filename[len(static_prefix):]
    if not filename.startswith('images/uploads/'):
        return

    file_path = os.path.join(current_app.static_folder, filename.replace('/', os.sep))
    if os.path.exists(file_path):
        try:
            os.remove(file_path)
        except OSError:
            pass


def delete_uploaded_product_images(image_value):
    for image_url in coerce_image_urls(image_value):
        delete_uploaded_product_image(image_url)


def _coerce_quantity(value, default=1):
    try:
        quantity = int(value)
    except (TypeError, ValueError):
        return default
    return max(0, quantity)


def _coerce_sale_percent(value, default=0):
    try:
        sale_percent = int(float(value))
    except (TypeError, ValueError):
        return default
    return max(0, min(100, sale_percent))


def _format_price_display(value):
    try:
        normalized = float(value)
        return str(int(normalized)) if normalized.is_integer() else f"{normalized:.2f}"
    except (TypeError, ValueError):
        return str(value)


def _compute_sale_price(price_text, sale_percent):
    price_value = parse_price_value(price_text)
    sale_percent_value = _coerce_sale_percent(sale_percent)
    if sale_percent_value <= 0:
        return price_value
    discounted_price = round(price_value * max(0.0, 1.0 - sale_percent_value / 100.0), 2)
    return discounted_price


def save_product(name, price, currency, image, category, description, quantity=1, sale_percent=0):
    category_id = get_or_create_category(category)
    quantity_value = _coerce_quantity(quantity, default=1)
    sale_percent_value = _coerce_sale_percent(sale_percent, default=0)
    image_value = ','.join(coerce_image_urls(image))
    with closing(get_connection()) as conn:
        cursor = conn.execute(
            'INSERT INTO products (name, price, currency, image, category_id, description, quantity, sale_percent) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',
            (name, price, currency, image_value, category_id, description, quantity_value, sale_percent_value)
        )
        conn.commit()
        product_id = cursor.lastrowid
    return product_id


def delete_product(product_id):
    with closing(get_connection()) as conn:
        row = conn.execute('SELECT image FROM products WHERE id = ?', (product_id,)).fetchone()
        if row is None:
            return

        try:
            conn.execute('DELETE FROM products WHERE id = ?', (product_id,))
            conn.commit()
        except sqlite3.IntegrityError:
            raise

    delete_uploaded_product_images(row['image'])


def parse_price_value(price_text):
    try:
        return float(str(price_text).replace('PKR', '').replace(',', '').split()[0])
    except (ValueError, IndexError):
        return 0.0


def get_all_products(page=None, per_page=20, randomize=False, category=None, price_range=None):
    category_filter = (category or '').strip()
    price_filter = (price_range or '').strip()

    with closing(get_connection()) as conn:
        order_clause = 'ORDER BY RANDOM()' if randomize else 'ORDER BY p.id'
        query = '''
            SELECT p.id, p.name, p.price, p.currency, p.image, c.name AS category, p.description, p.quantity,
                   COALESCE(p.sale_percent, 0) AS sale_percent,
                   COALESCE(rr.average_rating, 0) AS average_rating,
                   COALESCE(rr.review_count, 0) AS review_count
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN (
                SELECT product_id, AVG(rating) AS average_rating, COUNT(*) AS review_count
                FROM reviews
                GROUP BY product_id
            ) rr ON p.id = rr.product_id
        '''
        params = []
        filters = []

        if category_filter:
            filters.append('LOWER(c.name) = ?')
            params.append(category_filter.lower())

        if price_filter:
            if price_filter == 'under-1000':
                filters.append('CAST(REPLACE(REPLACE(p.price, "PKR", ""), ",", "") AS REAL) < 1000')
            elif price_filter == '1000-5000':
                filters.append('CAST(REPLACE(REPLACE(p.price, "PKR", ""), ",", "") AS REAL) BETWEEN 1000 AND 5000')
            elif price_filter == 'above-5000':
                filters.append('CAST(REPLACE(REPLACE(p.price, "PKR", ""), ",", "") AS REAL) > 5000')

        if filters:
            query += ' WHERE ' + ' AND '.join(filters)

        query += f' {order_clause}'

        if page is not None:
            page = max(1, int(page))
            per_page = max(1, int(per_page))
            offset = (page - 1) * per_page
            query += ' LIMIT ? OFFSET ?'
            params.extend([per_page, offset])

        rows = conn.execute(query, tuple(params)).fetchall()

    return [
        {
            'id': row['id'],
            'name': row['name'],
            'price': row['price'],
            'currency': row['currency'],
            'image': (coerce_image_urls(row['image']) or [''])[0],
            'images': coerce_image_urls(row['image']),
            'category': row['category'] or 'General',
            'description': row['description'],
            'quantity': _coerce_quantity(row['quantity'], default=1),
            'sale_percent': _coerce_sale_percent(row['sale_percent'], default=0),
            'sale_price': _compute_sale_price(row['price'], row['sale_percent']),
            'sale_price_display': _format_price_display(_compute_sale_price(row['price'], row['sale_percent'])),
            'average_rating': float(row['average_rating'] or 0),
            'review_count': int(row['review_count'] or 0),
        }
        for row in rows
    ]


def get_product(product_id):
    with closing(get_connection()) as conn:
        row = conn.execute(
            '''
            SELECT p.id, p.name, p.price, p.currency, p.image, c.name AS category, p.description, p.quantity,
                   COALESCE(p.sale_percent, 0) AS sale_percent
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id = ?
            ''',
            (product_id,),
        ).fetchone()

    if row is None:
        return None

    images = coerce_image_urls(row['image'])
    sale_percent = _coerce_sale_percent(row['sale_percent'], default=0)
    sale_price = _compute_sale_price(row['price'], sale_percent)

    return {
        'id': row['id'],
        'name': row['name'],
        'price': row['price'],
        'currency': row['currency'],
        'image': images[0] if images else '',
        'images': images,
        'category': row['category'] or 'General',
        'description': row['description'],
        'quantity': _coerce_quantity(row['quantity'], default=1),
        'sale_percent': sale_percent,
        'sale_price': sale_price,
        'sale_price_display': _format_price_display(sale_price),
    }


def get_reviews_for_product(product_id):
    with closing(get_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT id, reviewer_name, rating, comment, created_at
            FROM reviews
            WHERE product_id = ?
            ORDER BY created_at DESC
            ''',
            (product_id,)
        ).fetchall()
    return [
        {
            'id': row['id'],
            'reviewer_name': row['reviewer_name'] or 'Anonymous',
            'rating': int(row['rating']),
            'comment': row['comment'],
            'created_at': row['created_at'],
        }
        for row in rows
    ]


def save_product_review(product_id, reviewer_name, rating, comment):
    reviewer_name = (reviewer_name or '').strip() or 'Anonymous'
    try:
        rating_value = max(1, min(5, int(rating)))
    except (TypeError, ValueError):
        rating_value = 5
    comment_text = (comment or '').strip()
    with closing(get_connection()) as conn:
        conn.execute(
            'INSERT INTO reviews (product_id, reviewer_name, rating, comment) VALUES (?, ?, ?, ?)',
            (product_id, reviewer_name, rating_value, comment_text),
        )
        conn.commit()


def get_products_by_ids(product_ids):
    product_ids = [int(pid) for pid in product_ids if pid is not None]
    if not product_ids:
        return {}

    placeholders = ','.join('?' for _ in product_ids)
    with closing(get_connection()) as conn:
        rows = conn.execute(
            f'''
            SELECT p.id, p.name, p.price, p.currency, p.image, c.name AS category, p.description, p.quantity,
                   COALESCE(p.sale_percent, 0) AS sale_percent
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE p.id IN ({placeholders})
            ORDER BY p.id
            ''',
            tuple(product_ids),
        ).fetchall()

    return {
        row['id']: {
            'id': row['id'],
            'name': row['name'],
            'price': row['price'],
            'currency': row['currency'],
            'image': (coerce_image_urls(row['image']) or [''])[0],
            'images': coerce_image_urls(row['image']),
            'category': row['category'] or 'General',
            'description': row['description'],
            'quantity': _coerce_quantity(row['quantity'], default=1),
            'sale_percent': _coerce_sale_percent(row['sale_percent'], default=0),
            'sale_price': _compute_sale_price(row['price'], row['sale_percent']),
            'sale_price_display': _format_price_display(_compute_sale_price(row['price'], row['sale_percent'])),
        }
        for row in rows
    }


def search_products(query, page=None, per_page=20):
    query = (query or '').strip()
    if not query:
        return []

    page = 1 if page is None else max(1, int(page))
    per_page = max(1, int(per_page))
    offset = (page - 1) * per_page
    wildcard = f'%{query.lower()}%'

    with closing(get_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT p.id, p.name, p.price, p.currency, p.image, c.name AS category, p.description, p.quantity,
                   COALESCE(p.sale_percent, 0) AS sale_percent
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            WHERE LOWER(p.name) LIKE ? OR LOWER(c.name) LIKE ?
            ORDER BY p.id
            LIMIT ? OFFSET ?
            ''',
            (wildcard, wildcard, per_page, offset),
        ).fetchall()

    return [
        {
            'id': row['id'],
            'name': row['name'],
            'price': row['price'],
            'currency': row['currency'],
            'image': (coerce_image_urls(row['image']) or [''])[0],
            'images': coerce_image_urls(row['image']),
            'category': row['category'] or 'General',
            'description': row['description'],
            'quantity': _coerce_quantity(row['quantity'], default=1),
            'sale_percent': _coerce_sale_percent(row['sale_percent'], default=0),
            'sale_price': _compute_sale_price(row['price'], row['sale_percent']),
            'sale_price_display': _format_price_display(_compute_sale_price(row['price'], row['sale_percent'])),
        }
        for row in rows
    ]


def get_all_product_ids():
    with closing(get_connection()) as conn:
        rows = conn.execute('SELECT id FROM products ORDER BY id').fetchall()
    return [row['id'] for row in rows]


__all__ = [
    'DB_PATH',
    'get_or_create_category',
    'save_image_file_for_product',
    'save_image_file_for_hero',
    'delete_uploaded_product_image',
    'save_product',
    'delete_product',
    'parse_price_value',
    'get_all_products',
    'get_product',
    'get_reviews_for_product',
    'save_product_review',
    'get_products_by_ids',
    'search_products',
    'get_all_product_ids',
]

