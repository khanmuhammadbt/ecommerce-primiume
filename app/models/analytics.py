from __future__ import annotations

from contextlib import closing

from app.models.shared import DB_TYPE, get_connection


def _ensure_table_columns(conn, table_name, required_columns):
    if DB_TYPE == 'mysql':
        columns = {
            row['COLUMN_NAME']
            for row in conn.execute(
                "SELECT COLUMN_NAME FROM information_schema.columns WHERE table_schema = DATABASE() AND table_name = %s",
                (table_name,),
            ).fetchall()
        }
    else:
        columns = {row['name'] for row in conn.execute(f'PRAGMA table_info({table_name})').fetchall()}

    if table_name == 'product_views' and 'timestamp' in columns and 'viewed_at' not in columns:
        conn.execute('ALTER TABLE product_views RENAME COLUMN timestamp TO viewed_at')
        columns.discard('timestamp')
        columns.add('viewed_at')

    for column_name, definition in required_columns.items():
        if column_name not in columns:
            conn.execute(f'ALTER TABLE {table_name} ADD COLUMN {column_name} {definition}')


def init_product_analytics_tables():
    with closing(get_connection()) as conn:
        if DB_TYPE == 'mysql':
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS product_views (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    user_session_id VARCHAR(255) NULL,
                    user_ip VARCHAR(255) NULL,
                    user_agent TEXT NULL,
                    viewed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_page VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                '''
            )
            conn.execute(
                '''
                CREATE TABLE IF NOT EXISTS product_cart_events (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    product_id INT NOT NULL,
                    user_session_id VARCHAR(255) NULL,
                    user_ip VARCHAR(255) NULL,
                    quantity INT NOT NULL DEFAULT 1,
                    added_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_page VARCHAR(255) NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
                ) ENGINE=InnoDB
                '''
            )
            for statement in (
                'CREATE INDEX idx_product_views_identity_product ON product_views (user_session_id, user_ip, product_id)',
                'CREATE INDEX idx_product_cart_events_identity_product ON product_cart_events (user_session_id, user_ip, product_id)',
                'CREATE INDEX idx_product_views_viewed_at ON product_views (viewed_at)',
                'CREATE INDEX idx_product_cart_events_added_at ON product_cart_events (added_at)',
            ):
                try:
                    conn.execute(statement)
                except Exception:
                    continue
            conn.commit()
            return

        conn.executescript(
            '''
            CREATE TABLE IF NOT EXISTS product_views (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_session_id TEXT NULL,
                user_ip TEXT NULL,
                user_agent TEXT NULL,
                viewed_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_page TEXT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS product_cart_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                product_id INTEGER NOT NULL,
                user_session_id TEXT NULL,
                user_ip TEXT NULL,
                quantity INTEGER NOT NULL DEFAULT 1,
                added_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                source_page TEXT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (product_id) REFERENCES products(id) ON DELETE CASCADE
            );
            '''
        )

        _ensure_table_columns(
            conn,
            'product_views',
            {
                'user_session_id': 'TEXT NULL',
                'user_ip': 'TEXT NULL',
                'user_agent': 'TEXT NULL',
                'viewed_at': 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
                'source_page': 'TEXT NULL',
                'created_at': 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
            },
        )
        _ensure_table_columns(
            conn,
            'product_cart_events',
            {
                'user_session_id': 'TEXT NULL',
                'user_ip': 'TEXT NULL',
                'quantity': 'INTEGER NOT NULL DEFAULT 1',
                'added_at': 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
                'source_page': 'TEXT NULL',
                'created_at': 'TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP',
            },
        )
        for statement in (
            'CREATE INDEX IF NOT EXISTS idx_product_views_identity_product ON product_views (user_session_id, user_ip, product_id)',
            'CREATE INDEX IF NOT EXISTS idx_product_cart_events_identity_product ON product_cart_events (user_session_id, user_ip, product_id)',
            'CREATE INDEX IF NOT EXISTS idx_product_views_viewed_at ON product_views (viewed_at)',
            'CREATE INDEX IF NOT EXISTS idx_product_cart_events_added_at ON product_cart_events (added_at)',
        ):
            try:
                conn.execute(statement)
            except Exception:
                continue
        conn.commit()


def record_product_view(product_id, user_session_id=None, user_ip=None, user_agent=None, source_page=None, viewed_at=None):
    init_product_analytics_tables()
    with closing(get_connection()) as conn:
        conn.execute(
            'INSERT INTO product_views (product_id, user_session_id, user_ip, user_agent, viewed_at, source_page, created_at) VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, CURRENT_TIMESTAMP)',
            (product_id, user_session_id, user_ip, user_agent, viewed_at, source_page),
        )
        conn.commit()


def record_product_cart_event(product_id, user_session_id=None, user_ip=None, quantity=1, source_page=None, added_at=None):
    init_product_analytics_tables()
    with closing(get_connection()) as conn:
        conn.execute(
            'INSERT INTO product_cart_events (product_id, user_session_id, user_ip, quantity, added_at, source_page, created_at) VALUES (?, ?, ?, ?, COALESCE(?, CURRENT_TIMESTAMP), ?, CURRENT_TIMESTAMP)',
            (product_id, user_session_id, user_ip, int(quantity or 1), added_at, source_page),
        )
        conn.commit()


def get_product_analytics_summary():
    init_product_analytics_tables()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT p.id AS product_id,
                   p.name AS product_name,
                   COALESCE(c.name, 'Uncategorized') AS category,
                   COALESCE(v.total_views, 0) AS total_views,
                   COALESCE(e.total_add_to_cart, 0) AS total_add_to_cart,
                   COALESCE(r.average_rating, 0) AS average_rating,
                   COALESCE(r.review_count, 0) AS rating_count
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS total_views
                FROM product_views
                GROUP BY product_id
            ) v ON v.product_id = p.id
            LEFT JOIN (
                SELECT product_id, SUM(quantity) AS total_add_to_cart
                FROM product_cart_events
                GROUP BY product_id
            ) e ON e.product_id = p.id
            LEFT JOIN (
                SELECT product_id, AVG(rating) AS average_rating, COUNT(*) AS review_count
                FROM reviews
                GROUP BY product_id
            ) r ON r.product_id = p.id
            ORDER BY COALESCE(v.total_views, 0) DESC, p.name ASC
            '''
        ).fetchall()

    return [
        {
            'product_id': row['product_id'],
            'product_name': row['product_name'],
            'category': row['category'],
            'total_views': int(row['total_views'] or 0),
            'total_add_to_cart': int(row['total_add_to_cart'] or 0),
            'average_rating': float(row['average_rating'] or 0),
            'rating_count': int(row['rating_count'] or 0),
        }
        for row in rows
    ]


def get_customer_behavior_analytics():
    init_product_analytics_tables()
    identity_sql = "COALESCE(NULLIF(user_session_id, ''), NULLIF(user_ip, ''))"
    with closing(get_connection()) as conn:
        cart_rows = conn.execute(
            f'''
            SELECT {identity_sql} AS visitor_id, p.name AS product_name,
                   COUNT(*) AS add_to_cart_count, MAX(e.added_at) AS last_added_at
            FROM product_cart_events e
            JOIN products p ON p.id = e.product_id
            WHERE {identity_sql} IS NOT NULL
            GROUP BY {identity_sql}, e.product_id, p.name
            HAVING COUNT(*) >= 12
            ORDER BY add_to_cart_count DESC, last_added_at DESC
            LIMIT 25
            '''
        ).fetchall()
        view_rows = conn.execute(
            f'''
            SELECT {identity_sql} AS visitor_id, p.name AS product_name,
                   COUNT(*) AS view_count, MAX(v.viewed_at) AS last_viewed_at
            FROM product_views v
            JOIN products p ON p.id = v.product_id
            WHERE {identity_sql} IS NOT NULL
            GROUP BY {identity_sql}, v.product_id, p.name
            HAVING COUNT(*) >= 2
            ORDER BY view_count DESC, last_viewed_at DESC
            LIMIT 25
            '''
        ).fetchall()
        visitor_row = conn.execute(
            f'''
            SELECT COUNT(*) AS total_visitors,
                   SUM(CASE WHEN interaction_count = 1 THEN 1 ELSE 0 END) AS new_visitors,
                   SUM(CASE WHEN interaction_count > 1 THEN 1 ELSE 0 END) AS returning_visitors
            FROM (
                SELECT visitor_id, COUNT(*) AS interaction_count
                FROM (
                    SELECT {identity_sql} AS visitor_id FROM product_views
                    UNION ALL
                    SELECT {identity_sql} AS visitor_id FROM product_cart_events
                ) tracked_events
                WHERE visitor_id IS NOT NULL
                GROUP BY visitor_id
            ) visitor_counts
            '''
        ).fetchone()
        order_row = conn.execute(
            '''
            SELECT
                COALESCE(SUM(CASE WHEN order_count = 1 THEN order_count ELSE 0 END), 0) AS new_customer_orders,
                COALESCE(SUM(CASE WHEN order_count > 1 THEN order_count ELSE 0 END), 0) AS returning_customer_orders,
                COALESCE(SUM(CASE WHEN order_count = 1 THEN 1 ELSE 0 END), 0) AS new_customers,
                COALESCE(SUM(CASE WHEN order_count > 1 THEN 1 ELSE 0 END), 0) AS returning_customers
            FROM (
                SELECT customer_id, COUNT(*) AS order_count
                FROM orders
                GROUP BY customer_id
            ) customer_orders
            '''
        ).fetchone()

    def serialize(row, count_key, date_key):
        return {
            'visitor_id': row['visitor_id'],
            'product_name': row['product_name'],
            count_key: int(row[count_key] or 0),
            'last_activity': row[date_key],
        }

    return {
        'repeat_cart_customers': [serialize(row, 'add_to_cart_count', 'last_added_at') for row in cart_rows],
        'repeat_view_customers': [serialize(row, 'view_count', 'last_viewed_at') for row in view_rows],
        'visitor_overview': {
            'total_visitors': int(visitor_row['total_visitors'] or 0),
            'new_visitors': int(visitor_row['new_visitors'] or 0),
            'returning_visitors': int(visitor_row['returning_visitors'] or 0),
        },
        'orders_customer_breakdown': {
            'new_customer_orders': int(order_row['new_customer_orders'] or 0),
            'returning_customer_orders': int(order_row['returning_customer_orders'] or 0),
            'new_customers': int(order_row['new_customers'] or 0),
            'returning_customers': int(order_row['returning_customers'] or 0),
        },
    }


def get_category_analytics_summary():
    init_product_analytics_tables()
    with closing(get_connection()) as conn:
        rows = conn.execute(
            '''
            SELECT COALESCE(c.name, 'Uncategorized') AS category,
                   COALESCE(SUM(v.views_count), 0) AS views_count,
                   COALESCE(SUM(e.cart_count), 0) AS add_to_cart_count,
                   COALESCE(SUM(r.rating_count), 0) AS total_rating_count,
                   COALESCE((SUM(v.views_count) * 100.0) / NULLIF((
                       SELECT COUNT(*)
                       FROM product_views
                   ), 0), 0) AS views_percentage
            FROM products p
            LEFT JOIN categories c ON p.category_id = c.id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS views_count
                FROM product_views
                GROUP BY product_id
            ) v ON v.product_id = p.id
            LEFT JOIN (
                SELECT product_id, SUM(quantity) AS cart_count
                FROM product_cart_events
                GROUP BY product_id
            ) e ON e.product_id = p.id
            LEFT JOIN (
                SELECT product_id, COUNT(*) AS rating_count
                FROM reviews
                GROUP BY product_id
            ) r ON r.product_id = p.id
            GROUP BY COALESCE(c.name, 'Uncategorized')
            ORDER BY COALESCE(SUM(v.views_count), 0) DESC, COALESCE(c.name, 'Uncategorized') ASC
            '''
        ).fetchall()

    return [
        {
            'category': row['category'],
            'views_count': int(row['views_count'] or 0),
            'add_to_cart_count': int(row['add_to_cart_count'] or 0),
            'total_rating_count': int(row['total_rating_count'] or 0),
            'views_percentage': float(row['views_percentage'] or 0),
        }
        for row in rows
    ]
