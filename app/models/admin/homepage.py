from contextlib import closing

from app.models.shared import get_connection


def get_default_hero_slides():
    return [
        {
            'id': 1,
            'sort_order': 1,
            'eyebrow': 'Smart Essentials',
            'headline': 'Power up daily routines with smarter tech.',
            'description': 'Discover practical gadgets, home upgrades, and everyday tech essentials designed to make life smoother.',
            'primary_button_text': 'Shop Deals',
            'secondary_button_text': 'Explore Products',
            'image': 'https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&q=80',
            'category': '',
        },
        {
            'id': 2,
            'sort_order': 2,
            'eyebrow': 'Fresh Arrivals',
            'headline': 'Built for work, travel, and everyday convenience.',
            'description': 'From portable audio to smart accessories, find reliable upgrades that fit your routine and budget.',
            'primary_button_text': 'Browse Collection',
            'secondary_button_text': 'See Offers',
            'image': 'https://images.unsplash.com/photo-1523275335684-37898b6baf30?auto=format&fit=crop&w=1200&q=80',
            'category': '',
        },
        {
            'id': 3,
            'sort_order': 3,
            'eyebrow': 'Trusted Quality',
            'headline': 'Upgrade your home with dependable electronics.',
            'description': 'Shop quality-driven solutions with clear pricing, dependable support, and value that lasts beyond the first purchase.',
            'primary_button_text': 'Start Shopping',
            'secondary_button_text': 'View Catalog',
            'image': 'https://images.unsplash.com/photo-1550009158-9ebf69173e03?auto=format&fit=crop&w=1200&q=80',
            'category': '',
        },
    ]


def get_homepage_hero():
    with closing(get_connection()) as conn:
        row = conn.execute(
            'SELECT eyebrow, headline, description,  image FROM homepage_hero WHERE id = 1'
        ).fetchone()
    if row is None:
        return {
            'eyebrow': '',
            'headline': '',
            'description': '',
            'primary_button_text': 'Shop Now',
            'secondary_button_text': 'View Products',
            'image': ''
        }
    return {
        'eyebrow': row['eyebrow'],
        'headline': row['headline'],
        'description': row['description'],
        'image': row['image']
    }


def _seed_default_homepage_hero_slides():
    defaults = get_default_hero_slides()
    if not defaults:
        return

    with closing(get_connection()) as conn:
        for slide in defaults[:1]:
            conn.execute(
                '''
                INSERT OR IGNORE INTO homepage_hero_slides (
                    id, sort_order, eyebrow, headline, description, image, category
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''',
                (
                    slide['id'],
                    slide['sort_order'],
                    slide['eyebrow'],
                    slide['headline'],
                    slide['description'],
                    slide['image'],
                    slide.get('category', ''),
                )
            )
        conn.commit()


def get_homepage_hero_slides():
    with closing(get_connection()) as conn:
        try:
            rows = conn.execute(
                'SELECT id, sort_order, eyebrow, headline, description, image, category FROM homepage_hero_slides ORDER BY sort_order, id'
            ).fetchall()
        except Exception:
            conn.execute('ALTER TABLE homepage_hero_slides ADD COLUMN category TEXT NOT NULL DEFAULT ""')
            rows = conn.execute(
                'SELECT id, sort_order, eyebrow, headline, description, image, category FROM homepage_hero_slides ORDER BY sort_order, id'
            ).fetchall()

    if not rows:
        _seed_default_homepage_hero_slides()
        with closing(get_connection()) as conn:
            rows = conn.execute(
                'SELECT id, sort_order, eyebrow, headline, description, image, category FROM homepage_hero_slides ORDER BY sort_order, id'
            ).fetchall()

    return [
        {
            'id': row['id'],
            'sort_order': row['sort_order'],
            'eyebrow': row['eyebrow'],
            'headline': row['headline'],
            'description': row['description'],
            'image': row['image'],
            'category': row['category'] if 'category' in row.keys() else '',
        }
        for row in rows
    ]


def save_homepage_hero_slide(slide_id, eyebrow, headline, description, image_url, category=''):
    category = (category or '').strip()
    with closing(get_connection()) as conn:
        try:
            conn.execute(
                'INSERT INTO homepage_hero_slides (id, sort_order, eyebrow, headline, description, image, category) VALUES (?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(id) DO UPDATE SET sort_order=excluded.sort_order, eyebrow=excluded.eyebrow, headline=excluded.headline, description=excluded.description, image=excluded.image, category=excluded.category',
                (slide_id, slide_id, eyebrow, headline, description, image_url, category)
            )
        except Exception:
            conn.execute('ALTER TABLE homepage_hero_slides ADD COLUMN category TEXT NOT NULL DEFAULT ""')
            conn.execute(
                'INSERT INTO homepage_hero_slides (id, sort_order, eyebrow, headline, description, image, category) VALUES (?, ?, ?, ?, ?, ?, ?) '
                'ON CONFLICT(id) DO UPDATE SET sort_order=excluded.sort_order, eyebrow=excluded.eyebrow, headline=excluded.headline, description=excluded.description, image=excluded.image, category=excluded.category',
                (slide_id, slide_id, eyebrow, headline, description, image_url, category)
            )
        conn.commit()


def delete_homepage_hero_slide(slide_id):
    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM homepage_hero_slides WHERE id = ?', (slide_id,))
        conn.commit()


def get_homepage_trust_badges():
    with closing(get_connection()) as conn:
        rows = conn.execute(
            'SELECT id, title, description, icon FROM homepage_trust_badges ORDER BY id'
        ).fetchall()
    return [
        {
            'id': row['id'],
            'title': row['title'],
            'description': row['description'],
            'icon': row['icon']
        }
        for row in rows
    ]


def save_homepage_trust_badge(badge_id, title, description, icon):
    with closing(get_connection()) as conn:
        conn.execute(
            'UPDATE homepage_trust_badges SET title = ?, description = ?, icon = ? WHERE id = ?',
            (title, description, icon, badge_id)
        )
        conn.commit()


def save_homepage_hero(eyebrow, headline, description, image_url):
    with closing(get_connection()) as conn:
        conn.execute('INSERT OR IGNORE INTO homepage_hero (id) VALUES (1)')
        conn.execute(
            '''
            UPDATE homepage_hero
            SET eyebrow = ?, headline = ?, description = ?, image = ?
            WHERE id = 1
            ''',
            (eyebrow, headline, description, image_url)
        )
        conn.execute(
            '''
            UPDATE homepage_hero_slides
            SET eyebrow = ?, headline = ?, description = ?, image = ?
            WHERE id = (SELECT MIN(id) FROM homepage_hero_slides)
            ''',
            (eyebrow, headline, description, image_url)
        )
        conn.commit()


def get_homepage_filters(filter_type):
    with closing(get_connection()) as conn:
        rows = conn.execute(
            'SELECT id, label, value FROM homepage_filters WHERE filter_type = ? ORDER BY sort_order, id',
            (filter_type,)
        ).fetchall()
    return [
        {'id': row['id'], 'label': row['label'], 'value': row['value']}
        for row in rows
    ]


def save_homepage_filters(filter_type, items):
    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM homepage_filters WHERE filter_type = ?', (filter_type,))
        for index, item in enumerate(items, start=1):
            label = (item.get('label') or '').strip()
            value = (item.get('value') or '').strip()
            if not label or not value:
                continue
            conn.execute(
                'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
                (filter_type, label, value, index)
            )
        conn.commit()


__all__ = [
    'get_default_hero_slides',
    'get_homepage_hero',
    'get_homepage_hero_slides',
    'save_homepage_hero_slide',
    'get_homepage_trust_badges',
    'save_homepage_trust_badge',
    'save_homepage_hero',
    'get_homepage_filters',
    'save_homepage_filters',
]

