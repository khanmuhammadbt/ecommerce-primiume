import os
from contextlib import closing
from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.config import ADMIN_PASSWORD
from app.models.shared import DB_TYPE, get_connection


def _create_indexes(conn):
    if DB_TYPE == 'mysql':
        index_statements = [
            'CREATE INDEX IF NOT EXISTS idx_products_name ON products (name)',
            'CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id)',
            'CREATE INDEX IF NOT EXISTS idx_categories_name ON categories (name)',
            'CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug)',
            'CREATE INDEX IF NOT EXISTS idx_offers_code ON offers (code)',
            'CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email)',
            'CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id)',
            'CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id)',
            'CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id)',
            'CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages (slug)',
            'CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_login_key ON admin_login_attempts (login_key)',
        ]
    else:
        index_statements = [
            'CREATE INDEX IF NOT EXISTS idx_products_name ON products (name)',
            'CREATE INDEX IF NOT EXISTS idx_products_category_id ON products (category_id)',
            'CREATE INDEX IF NOT EXISTS idx_categories_name ON categories (name)',
            'CREATE INDEX IF NOT EXISTS idx_categories_slug ON categories (slug)',
            'CREATE INDEX IF NOT EXISTS idx_offers_code ON offers (code)',
            'CREATE INDEX IF NOT EXISTS idx_customers_email ON customers (email)',
            'CREATE INDEX IF NOT EXISTS idx_orders_customer_id ON orders (customer_id)',
            'CREATE INDEX IF NOT EXISTS idx_order_items_order_id ON order_items (order_id)',
            'CREATE INDEX IF NOT EXISTS idx_order_items_product_id ON order_items (product_id)',
            'CREATE INDEX IF NOT EXISTS idx_pages_slug ON pages (slug)',
            'CREATE INDEX IF NOT EXISTS idx_admin_login_attempts_login_key ON admin_login_attempts (login_key)',
        ]

    for statement in index_statements:
        try:
            conn.execute(statement)
        except Exception:
            continue


def _migrate_legacy_order_statuses(conn):
    if DB_TYPE == 'mysql':
        return

    tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}

    if 'orders_legacy' in tables:
        if 'orders' not in tables:
            conn.execute(
                '''
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'on_the_way', 'delivered')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    coupon_code TEXT NOT NULL DEFAULT '',
                    discount_text TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                '''
            )
        else:
            order_columns = {row[1] for row in conn.execute('PRAGMA table_info(orders)').fetchall()}
            if 'coupon_code' not in order_columns:
                conn.execute('ALTER TABLE orders ADD COLUMN coupon_code TEXT NOT NULL DEFAULT ""')
            if 'discount_text' not in order_columns:
                conn.execute('ALTER TABLE orders ADD COLUMN discount_text TEXT NOT NULL DEFAULT ""')

        legacy_columns = [row[1] for row in conn.execute('PRAGMA table_info(orders_legacy)').fetchall()]
        selected_columns = []
        for column in ['id', 'customer_id', 'total', 'status', 'created_at', 'coupon_code', 'discount_text']:
            if column in legacy_columns:
                selected_columns.append(column)
            elif column == 'coupon_code':
                selected_columns.append("'' AS coupon_code")
            elif column == 'discount_text':
                selected_columns.append("'' AS discount_text")

        select_sql = ', '.join(selected_columns)
        conn.execute(
            f'''INSERT OR IGNORE INTO orders (id, customer_id, total, status, created_at, coupon_code, discount_text)
                SELECT {select_sql} FROM orders_legacy'''
        )
        conn.execute('DROP TABLE IF EXISTS orders_legacy')
        conn.commit()
        return

    legacy_sql = conn.execute(
        "SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'"
    ).fetchone()
    if legacy_sql is None:
        return

    table_sql = (legacy_sql['sql'] or '').strip()
    if "on_the_way" in table_sql:
        return

    if "CHECK(status IN ('pending', 'delivered'))" not in table_sql and "CHECK(status IN (\'pending\', \'delivered\'))" not in table_sql:
        return

    conn.execute('ALTER TABLE orders RENAME TO orders_legacy')
    conn.execute(
        '''
        CREATE TABLE orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_id INTEGER NOT NULL,
            total TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'on_the_way', 'delivered')),
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            coupon_code TEXT NOT NULL DEFAULT '',
            discount_text TEXT NOT NULL DEFAULT '',
            FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
        )
        '''
    )

    legacy_columns = [row[1] for row in conn.execute('PRAGMA table_info(orders_legacy)').fetchall()]
    selected_columns = []
    for column in ['id', 'customer_id', 'total', 'status', 'created_at', 'coupon_code', 'discount_text']:
        if column in legacy_columns:
            selected_columns.append(column)
        elif column == 'coupon_code':
            selected_columns.append("'' AS coupon_code")
        elif column == 'discount_text':
            selected_columns.append("'' AS discount_text")

    select_sql = ', '.join(selected_columns)
    conn.execute(
        f'''INSERT INTO orders (id, customer_id, total, status, created_at, coupon_code, discount_text)
            SELECT {select_sql} FROM orders_legacy'''
    )
    conn.execute('DROP TABLE orders_legacy')
    conn.commit()


def init_admin_db():
    with closing(get_connection()) as conn:
        if DB_TYPE == 'mysql':
            existing_tables = {
                row['TABLE_NAME']
                for row in conn.execute(
                    "SELECT TABLE_NAME FROM information_schema.tables WHERE table_schema = DATABASE()"
                ).fetchall()
            }
            schema_sql = [
                """
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    username VARCHAR(255) UNIQUE NOT NULL,
                    password VARCHAR(255) NOT NULL
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS pages (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    slug VARCHAR(255) UNIQUE NOT NULL,
                    content TEXT NOT NULL
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS categories (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) UNIQUE NOT NULL,
                    slug VARCHAR(255) UNIQUE NOT NULL
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS homepage_hero (
                    id INT PRIMARY KEY,
                    eyebrow TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    description TEXT NOT NULL,
                    image TEXT NOT NULL
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS homepage_hero_slides (
                    id INT PRIMARY KEY,
                    sort_order INT NOT NULL DEFAULT 0,
                    eyebrow VARCHAR(255) NOT NULL DEFAULT '',
                    headline VARCHAR(255) NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    image TEXT NOT NULL DEFAULT '',
                    category VARCHAR(255) NOT NULL DEFAULT ''
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS homepage_trust_badges (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL DEFAULT '',
                    description TEXT NOT NULL,
                    icon VARCHAR(50) NOT NULL DEFAULT ''
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS products (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    price VARCHAR(50) NOT NULL,
                    currency VARCHAR(20) NOT NULL,
                    image TEXT NOT NULL,
                    category_id INT,
                    description TEXT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS offers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    title VARCHAR(255) NOT NULL,
                    description TEXT NOT NULL,
                    discount VARCHAR(50) NOT NULL,
                    code VARCHAR(100) UNIQUE NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS customers (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    full_name VARCHAR(255) NOT NULL,
                    email VARCHAR(255) UNIQUE NOT NULL,
                    phone VARCHAR(50) NOT NULL,
                    address TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS orders (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    customer_id INT NOT NULL,
                    total VARCHAR(50) NOT NULL,
                    status VARCHAR(50) NOT NULL DEFAULT 'pending',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    coupon_code VARCHAR(255) NOT NULL DEFAULT '',
                    discount_text VARCHAR(255) NOT NULL DEFAULT '',
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS order_items (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    order_id INT NOT NULL,
                    product_id INT NOT NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    unit_price VARCHAR(50) NOT NULL,
                    item_total VARCHAR(50) NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                ) ENGINE=InnoDB
                """,
                """
                CREATE TABLE IF NOT EXISTS reviews (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    reviewer_name VARCHAR(255) NOT NULL DEFAULT '',
                    rating INT NOT NULL,
                    comment TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                """,
            ]
            for statement in schema_sql:
                conn.execute(statement)
        else:
            existing_tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()}
            _migrate_legacy_order_statuses(conn)
            conn.executescript(
                '''
                CREATE TABLE IF NOT EXISTS admin_users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS pages (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    slug TEXT UNIQUE NOT NULL,
                    content TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS categories (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE NOT NULL,
                    slug TEXT UNIQUE NOT NULL
                );

                CREATE TABLE IF NOT EXISTS homepage_hero (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    eyebrow TEXT NOT NULL,
                    headline TEXT NOT NULL,
                    description TEXT NOT NULL,
                    image TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS homepage_hero_slides (
                    id INTEGER PRIMARY KEY,
                    sort_order INTEGER NOT NULL DEFAULT 0,
                    eyebrow TEXT NOT NULL DEFAULT '',
                    headline TEXT NOT NULL DEFAULT '',
                    description TEXT NOT NULL DEFAULT '',
                    image TEXT NOT NULL DEFAULT '',
                    category TEXT NOT NULL DEFAULT ''
                );

                CREATE TABLE IF NOT EXISTS homepage_trust_badges (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    icon TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS homepage_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS products (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    price TEXT NOT NULL,
                    currency TEXT NOT NULL,
                    image TEXT NOT NULL,
                    category_id INTEGER,
                    description TEXT NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    sale_percent INTEGER NOT NULL DEFAULT 0,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (category_id) REFERENCES categories(id) ON DELETE SET NULL
                );

                CREATE TABLE IF NOT EXISTS offers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    discount TEXT NOT NULL,
                    code TEXT UNIQUE NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS customers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    full_name TEXT NOT NULL,
                    email TEXT UNIQUE NOT NULL,
                    phone TEXT NOT NULL,
                    address TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
                );

                CREATE TABLE IF NOT EXISTS orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'on_the_way', 'delivered')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                );

                CREATE TABLE IF NOT EXISTS homepage_filters (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filter_type TEXT NOT NULL,
                    label TEXT NOT NULL,
                    value TEXT NOT NULL,
                    sort_order INTEGER NOT NULL DEFAULT 0
                );

                CREATE TABLE IF NOT EXISTS order_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    order_id INTEGER NOT NULL,
                    product_id INTEGER NOT NULL,
                    quantity INTEGER NOT NULL DEFAULT 1,
                    unit_price TEXT NOT NULL,
                    item_total TEXT NOT NULL,
                    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE RESTRICT
                );

                CREATE TABLE IF NOT EXISTS reviews (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    product_id INTEGER NOT NULL,
                    reviewer_name TEXT NOT NULL,
                    rating INTEGER NOT NULL CHECK (rating BETWEEN 1 AND 5),
                    comment TEXT NOT NULL,
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                );
                '''
            )

        _create_indexes(conn)
        conn.execute('INSERT OR IGNORE INTO pages (slug, content) VALUES (?, ?)', ('about', ''))
        conn.execute('INSERT OR IGNORE INTO pages (slug, content) VALUES (?, ?)', ('contact', ''))
        conn.execute(
            '''
            CREATE TABLE IF NOT EXISTS admin_login_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                login_key TEXT UNIQUE NOT NULL,
                failures INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            '''
        )
        if DB_TYPE == 'mysql':
            conn.execute('''
                CREATE TABLE IF NOT EXISTS admin_login_attempts (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    login_key VARCHAR(255) UNIQUE NOT NULL,
                    failures INT NOT NULL DEFAULT 0,
                    locked_until VARCHAR(255),
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                ) ENGINE=InnoDB
            ''')
        admin_password = ADMIN_PASSWORD
        if not admin_password:
            raise RuntimeError('ADMIN_PASSWORD must be set in the environment (.env) before starting the app.')

        conn.execute(
            'INSERT OR IGNORE INTO admin_users (username, password) VALUES (?, ?)',
            ('admin', generate_password_hash(admin_password))
        )
        conn.execute(
            '''
            INSERT OR IGNORE INTO homepage_hero (
                id, eyebrow, headline, description, image
            ) VALUES (?, ?, ?, ?, ?)
            ''',
            (1, '', '', '', '')
        )
        conn.execute(
            'INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)',
            ('delivery_charge', '250')
        )

        conn.execute(
            'INSERT OR IGNORE INTO homepage_trust_badges (id, title, description, icon) VALUES (?, ?, ?, ?)',
            (1, 'Free Shipping', 'On all orders over PKR 99000', 'ðŸšš')
        )
        conn.execute('DELETE FROM homepage_filters')
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('category', 'Phones', 'Phones', 1)
        )
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('category', 'Laptops', 'Laptops', 2)
        )
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('category', 'Accessories', 'Accessories', 3)
        )
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('price', 'Under PKR 1,000', 'under-1000', 1)
        )
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('price', 'PKR 1,000 - 5,000', '1000-5000', 2)
        )
        conn.execute(
            'INSERT INTO homepage_filters (filter_type, label, value, sort_order) VALUES (?, ?, ?, ?)',
            ('price', 'Above PKR 5,000', 'above-5000', 3)
        )
        conn.execute(
            'INSERT OR IGNORE INTO homepage_trust_badges (id, title, description, icon) VALUES (?, ?, ?, ?)',
            (2, '24/7 Support', 'We are here to help', 'ðŸ› ï¸')
        )
        conn.execute(
            'INSERT OR IGNORE INTO homepage_trust_badges (id, title, description, icon) VALUES (?, ?, ?, ?)',
            (3, 'Secure Payment', '100% protected', 'ðŸ”’')
        )
        conn.execute(
            'INSERT OR IGNORE INTO homepage_trust_badges (id, title, description, icon) VALUES (?, ?, ?, ?)',
            (4, 'Easy Returns', '30-day policy', 'â†©ï¸')
        )

        if not {'admin_users', 'categories', 'products', 'offers', 'customers', 'orders', 'order_items', 'homepage_hero'}.issubset(existing_tables):
            conn.execute('INSERT OR IGNORE INTO categories (name, slug) VALUES (?, ?)', ('General', 'general'))

        if DB_TYPE == 'mysql':
            order_columns = {row['Field'] for row in conn.execute('SHOW COLUMNS FROM orders').fetchall()}
        else:
            order_columns = {row[1] for row in conn.execute("PRAGMA table_info(orders)").fetchall()}
        if 'coupon_code' not in order_columns:
            conn.execute('ALTER TABLE orders ADD COLUMN coupon_code VARCHAR(255) NOT NULL DEFAULT ""')
        if 'discount_text' not in order_columns:
            conn.execute('ALTER TABLE orders ADD COLUMN discount_text VARCHAR(255) NOT NULL DEFAULT ""')

        if DB_TYPE == 'mysql':
            product_columns = {row['Field'] for row in conn.execute('SHOW COLUMNS FROM products').fetchall()}
        else:
            product_columns = {row[1] for row in conn.execute('PRAGMA table_info(products)').fetchall()}
        if 'quantity' not in product_columns:
            conn.execute('ALTER TABLE products ADD COLUMN quantity INTEGER NOT NULL DEFAULT 1')
        if 'sale_percent' not in product_columns:
            conn.execute('ALTER TABLE products ADD COLUMN sale_percent INTEGER NOT NULL DEFAULT 0')

        _create_indexes(conn)
        conn.commit()


def verify_admin_login(username, password):
    with closing(get_connection()) as conn:
        row = conn.execute(
            'SELECT password FROM admin_users WHERE username = ?',
            (username,)
        ).fetchone()
    if row is None:
        return False
    return check_password_hash(row['password'], password)


def get_login_attempt_state(login_key):
    with closing(get_connection()) as conn:
        row = conn.execute(
            'SELECT failures, locked_until FROM admin_login_attempts WHERE login_key = ?',
            (login_key,)
        ).fetchone()
    if row is None:
        return {'failures': 0, 'locked_until': None}
    return {'failures': int(row['failures']), 'locked_until': row['locked_until']}


def save_login_attempt_state(login_key, failures, locked_until):
    with closing(get_connection()) as conn:
        if locked_until is None:
            conn.execute(
                'INSERT INTO admin_login_attempts (login_key, failures, locked_until, updated_at) VALUES (?, ?, ?, ?) '
                'ON CONFLICT(login_key) DO UPDATE SET failures=excluded.failures, locked_until=excluded.locked_until, updated_at=excluded.updated_at',
                (login_key, failures, None, datetime.now(timezone.utc).isoformat())
            )
        else:
            conn.execute(
                'INSERT INTO admin_login_attempts (login_key, failures, locked_until, updated_at) VALUES (?, ?, ?, ?) '
                'ON CONFLICT(login_key) DO UPDATE SET failures=excluded.failures, locked_until=excluded.locked_until, updated_at=excluded.updated_at',
                (login_key, failures, locked_until, datetime.now(timezone.utc).isoformat())
            )
        conn.commit()


def clear_login_attempt_state(login_key):
    with closing(get_connection()) as conn:
        conn.execute('DELETE FROM admin_login_attempts WHERE login_key = ?', (login_key,))
        conn.commit()


__all__ = [
    'init_admin_db',
    'verify_admin_login',
    'get_login_attempt_state',
    'save_login_attempt_state',
    'clear_login_attempt_state',
]

