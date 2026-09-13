from contextlib import closing

from app.models.shared import DB_TYPE, get_connection


def get_default_page_content(slug):
    if slug == 'about':
        return (
            'Welcome to Banta Bazar! We are committed to providing the best products and services.\n\n'
            'Founded in 2020, Banta Bazar has grown to serve thousands of customers worldwide, offering a wide range of electronics with a focus on quality and customer satisfaction. '
            'Our mission is to make technology accessible and affordable for everyone.'
        )
    if slug == 'contact':
        return (
            'Reach out to us for help with products, orders, or general questions.\n\n'
            'We value your privacy and strive to protect your personal data. Our terms of service and privacy policy outline how we collect, use, and safeguard your information.\n\n'
            'Phone: +1 (555) 123-4567\n'
            'Email: support@bantabazar.com\n'
            'Address: 123 Tech Avenue, Suite 400, Silicon City, CA 94025'
        )
    return ''


def get_page_content(slug):
    """Return the content string for a given page slug (e.g., 'about' or 'contact')."""
    with closing(get_connection()) as conn:
        row = conn.execute('SELECT content FROM pages WHERE slug = ?', (slug,)).fetchone()
        if row is None or not str(row['content']).strip():
            return get_default_page_content(slug)
        return row['content']


def update_page_content(slug, content):
    """Create or update the content for a given page slug."""
    with closing(get_connection()) as conn:
        if DB_TYPE == 'mysql':
            conn.execute(
                'INSERT INTO pages (slug, content) VALUES (?, ?) ON DUPLICATE KEY UPDATE content = VALUES(content)',
                (slug, content)
            )
        else:
            conn.execute('INSERT INTO pages (slug, content) VALUES (?, ?) ON CONFLICT(slug) DO UPDATE SET content=excluded.content', (slug, content))
        conn.commit()


__all__ = [
    'get_default_page_content',
    'get_page_content',
    'update_page_content',
]

