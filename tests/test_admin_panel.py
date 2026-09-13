import gc
import importlib
import io
import os
import sqlite3
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.config import ADMIN_PASSWORD, Config
from app.models import admin_models, catalog_models, order_models, shared_models

routes_module = shared_models
TEST_ADMIN_PASSWORD = ADMIN_PASSWORD or os.environ.get('ADMIN_PASSWORD')
if not TEST_ADMIN_PASSWORD:
    raise RuntimeError('ADMIN_PASSWORD must be set in the environment before running tests.')


class AdminPanelTests(unittest.TestCase):
    def setUp(self):
        self.db_tempdir = tempfile.TemporaryDirectory()
        self.temp_db_path = str(Path(self.db_tempdir.name) / 'shop.db')
        routes_module.DB_PATH = self.temp_db_path
        shared_models.DB_PATH = self.temp_db_path

        if os.path.exists(routes_module.DB_PATH):
            os.remove(routes_module.DB_PATH)

        self.app = create_app()
        self.app.config['TESTING'] = True
        self.client = self.app.test_client()

    def tearDown(self):
        self.client = None
        self.app = None
        try:
            self.db_tempdir.cleanup()
        except Exception:
            pass

    def test_security_settings_are_loaded_from_environment(self):
        self.assertTrue(Config.SECRET_KEY)
        self.assertTrue(Config.ADMIN_PASSWORD)
        self.assertNotEqual(Config.SECRET_KEY, 'change-this-secret-key')

    def test_csrf_protection_is_enabled_and_visible_to_forms(self):
        self.assertTrue(self.app.config.get('WTF_CSRF_ENABLED'))
        login_page = self.client.get('/admin/login')
        self.assertEqual(login_page.status_code, 200)
        self.assertIn('meta name="csrf-token"', login_page.get_data(as_text=True))
        self.assertIn('name="csrf_token"', login_page.get_data(as_text=True))

    def test_app_starts_without_dummy_seed_data(self):
        self.assertEqual(catalog_models.get_all_products(), [])
        self.assertEqual(order_models.get_all_offers(), [])
        hero = admin_models.get_homepage_hero()
        self.assertEqual(hero['headline'], '')
        self.assertEqual(hero['description'], '')

    def test_homepage_renders_hero_slider_with_three_slides(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)
        self.assertIn('hero-slider', html)
        self.assertEqual(html.count('<article class="hero-slide'), 3)

    def test_admin_can_add_new_hero_slide(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        response = self.client.post('/admin/hero/add', data={
            'eyebrow': 'New Arrival',
            'headline': 'Fresh picks for your everyday setup',
            'description': 'Explore new essentials built for comfort and convenience.',
            'primary_button_text': 'Shop Now',
            'secondary_button_text': 'Learn More',
            'image': 'https://example.com/new-slide.jpg',
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Hero slide created successfully.', response.get_data(as_text=True))

        slides = admin_models.get_homepage_hero_slides()
        self.assertGreaterEqual(len(slides), 4)
        self.assertTrue(any(slide['headline'] == 'Fresh picks for your everyday setup' for slide in slides))

    def test_admin_can_assign_category_to_homepage_slide_and_homepage_links_to_it(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        response = self.client.post('/admin/hero/add', data={
            'eyebrow': 'Trend Picks',
            'headline': 'Explore electronics curated for daily life',
            'description': 'From accessories to smart home upgrades, find what fits your setup.',
            'category': 'Electronics',
            'image': 'https://example.com/electronics-slide.jpg',
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        slides = admin_models.get_homepage_hero_slides()
        new_slide = next((item for item in slides if item['headline'] == 'Explore electronics curated for daily life'), None)
        self.assertIsNotNone(new_slide)
        self.assertEqual(new_slide['category'], 'Electronics')

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        html = home_response.get_data(as_text=True)
        self.assertIn('category=Electronics', html)
        self.assertIn('View Electronics products', html)

    def test_admin_hero_slides_are_rendered_as_collapsible_details(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        response = self.client.get('/admin/dashboard')
        self.assertEqual(response.status_code, 200)
        html = response.get_data(as_text=True)

        self.assertIn('<details class="hero-slide-details"', html)
        self.assertIn('<summary class="hero-slide-summary"', html)
        self.assertIn('hero-slide-arrow', html)

    def test_admin_product_create_redirects_back_to_add_product_section(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        response = self.client.post('/admin/products', data={
            'name': 'Test Product',
            'price': '1500',
            'currency': 'PKR',
            'category': 'Electronics',
            'quantity': '5',
            'sale_percent': '10',
            'description': 'A test product to verify redirect behavior.',
        }, follow_redirects=False)

        self.assertEqual(response.status_code, 302)
        self.assertIn('/admin/dashboard', response.location)
        self.assertTrue(response.location.endswith('#add-product-section'))

    def test_admin_can_delete_hero_slide(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        response = self.client.post('/admin/hero/add', data={
            'eyebrow': 'Limited Offer',
            'headline': 'Delete me later',
            'description': 'This slide should be removed.',
            'image': 'https://example.com/delete-slide.jpg',
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        slides = admin_models.get_homepage_hero_slides()
        slide = next((item for item in slides if item['headline'] == 'Delete me later'), None)
        self.assertIsNotNone(slide)

        delete_response = self.client.post(f"/admin/hero/{slide['id']}/delete", follow_redirects=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn('Hero slide deleted successfully.', delete_response.get_data(as_text=True))

        remaining_slides = admin_models.get_homepage_hero_slides()
        self.assertNotIn('Delete me later', [item['headline'] for item in remaining_slides])

    def test_admin_pages_render_sidebar_navigation(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        dashboard_response = self.client.get('/admin/dashboard')
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn('/admin/dashboard', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/dashboard#add-product-section', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/dashboard#all-products-section', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/dashboard#offers-section', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/dashboard#orders-section', dashboard_response.get_data(as_text=True))
        self.assertIn('id="order-search"', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/about', dashboard_response.get_data(as_text=True))
        self.assertIn('/admin/contact', dashboard_response.get_data(as_text=True))

    def test_admin_can_set_order_status_to_on_the_way(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        with sqlite3.connect(self.temp_db_path) as conn:
            customer_id = conn.execute(
                'INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)',
                ('Test Buyer', 'buyer@example.com', '03001234567', 'Somewhere in Lahore')
            ).lastrowid
            conn.execute(
                'INSERT INTO orders (customer_id, total, status, created_at, coupon_code, discount_text) VALUES (?, ?, ?, ?, ?, ?)',
                (customer_id, '2500', 'pending', '2026-08-08 12:00:00', '', '')
            )
            conn.commit()

        dashboard_response = self.client.get('/admin/dashboard')
        self.assertEqual(dashboard_response.status_code, 200)
        self.assertIn('On the Way', dashboard_response.get_data(as_text=True))

        update_response = self.client.post('/admin/orders/1/status', data={'status': 'on_the_way'}, follow_redirects=True)
        self.assertEqual(update_response.status_code, 200)
        self.assertIn('Order marked as on the way', update_response.get_data(as_text=True))

        with sqlite3.connect(self.temp_db_path) as conn:
            order_status = conn.execute('SELECT status FROM orders WHERE id = 1').fetchone()[0]
        self.assertEqual(order_status, 'on_the_way')

    def test_admin_can_search_orders_by_id_name_or_email(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        with sqlite3.connect(self.temp_db_path) as conn:
            customer_id = conn.execute(
                'INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)',
                ('Search Buyer', 'search@example.com', '03001234567', 'Somewhere in Lahore')
            ).lastrowid
            conn.execute(
                'INSERT INTO orders (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)',
                (customer_id, '2500', 'pending', '2026-08-08 12:00:00')
            )
            conn.commit()

        for search_query in ('1', 'Search Buyer', 'search@example.com'):
            response = self.client.get('/admin/api/orders', query_string={'search': search_query})
            self.assertEqual(response.status_code, 200)
            self.assertEqual(len(response.get_json()['orders']), 1)

        empty_response = self.client.get('/admin/api/orders', query_string={'search': 'missing'})
        self.assertEqual(empty_response.status_code, 200)
        self.assertEqual(empty_response.get_json()['orders'], [])

    def test_existing_orders_table_is_migrated_to_support_on_the_way(self):
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute('DROP TABLE IF EXISTS orders')
            conn.execute('DROP TABLE IF EXISTS customers')
            conn.execute(
                '''
                CREATE TABLE orders (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'delivered')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    coupon_code TEXT NOT NULL DEFAULT '',
                    discount_text TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                '''
            )
            conn.execute('CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            conn.execute('INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)', ('Legacy Buyer', 'legacy@example.com', '03000000000', 'Old Address'))
            conn.execute('INSERT INTO orders (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)', (1, '1500', 'pending', '2026-08-08 12:00:00'))
            conn.commit()

        init_admin_db = admin_models.init_admin_db
        init_admin_db()

        with sqlite3.connect(self.temp_db_path) as conn:
            table_sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()[0]
            self.assertIn("'on_the_way'", table_sql)
            order_status = conn.execute('SELECT status FROM orders WHERE id = 1').fetchone()[0]
            self.assertEqual(order_status, 'pending')

    def test_partial_legacy_migration_is_recovered_without_crashing(self):
        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute('DROP TABLE IF EXISTS orders')
            conn.execute('DROP TABLE IF EXISTS orders_legacy')
            conn.execute('DROP TABLE IF EXISTS customers')
            conn.execute(
                '''
                CREATE TABLE orders_legacy (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    customer_id INTEGER NOT NULL,
                    total TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending' CHECK(status IN ('pending', 'delivered')),
                    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    coupon_code TEXT NOT NULL DEFAULT '',
                    discount_text TEXT NOT NULL DEFAULT '',
                    FOREIGN KEY (customer_id) REFERENCES customers(id) ON DELETE CASCADE
                )
                '''
            )
            conn.execute('CREATE TABLE customers (id INTEGER PRIMARY KEY AUTOINCREMENT, full_name TEXT NOT NULL, email TEXT UNIQUE NOT NULL, phone TEXT NOT NULL, address TEXT NOT NULL, created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)')
            conn.execute('INSERT INTO customers (full_name, email, phone, address) VALUES (?, ?, ?, ?)', ('Legacy Buyer', 'legacy@example.com', '03000000000', 'Old Address'))
            conn.execute('INSERT INTO orders_legacy (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)', (1, '1500', 'pending', '2026-08-08 12:00:00'))
            conn.commit()

        init_admin_db = admin_models.init_admin_db
        init_admin_db()

        with sqlite3.connect(self.temp_db_path) as conn:
            table_sql = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='orders'").fetchone()[0]
            self.assertIn("'on_the_way'", table_sql)
            order_status = conn.execute('SELECT status FROM orders WHERE id = 1').fetchone()[0]
            self.assertEqual(order_status, 'pending')

    def test_admin_login_is_protected_against_brute_force_attempts(self):
        self.app.config['LOGIN_RATE_LIMIT'] = '100 per minute'

        for _ in range(4):
            response = self.client.post('/admin/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)
            self.assertEqual(response.status_code, 200)
            self.assertIn('Invalid username or password.', response.get_data(as_text=True))

        locked_response = self.client.post('/admin/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)
        self.assertEqual(locked_response.status_code, 200)
        self.assertIn('Too many failed attempts', locked_response.get_data(as_text=True))
        self.assertIn('try again in', locked_response.get_data(as_text=True))

    def test_admin_login_lockout_blocks_correct_password_while_locked(self):
        self.app.config['LOGIN_MAX_ATTEMPTS'] = '4'
        self.app.config['LOGIN_LOCKOUT_MINUTES'] = '15'

        for _ in range(4):
            self.client.post('/admin/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)

        locked_response = self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)

        self.assertEqual(locked_response.status_code, 200)
        self.assertIn('Too many failed attempts', locked_response.get_data(as_text=True))
        self.assertNotIn('Admin Dashboard', locked_response.get_data(as_text=True))

    def test_admin_login_lockout_persists_across_app_instances(self):
        self.app.config['LOGIN_MAX_ATTEMPTS'] = '4'
        self.app.config['LOGIN_LOCKOUT_MINUTES'] = '15'

        for _ in range(4):
            self.client.post('/admin/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)

        restarted_app = create_app()
        restarted_app.config['TESTING'] = True
        restarted_client = restarted_app.test_client()
        locked_response = restarted_client.post('/admin/login', data={'username': 'admin', 'password': 'wrong-password'}, follow_redirects=True)

        self.assertEqual(locked_response.status_code, 200)
        self.assertIn('Too many failed attempts', locked_response.get_data(as_text=True))

    def test_admin_can_create_product_and_offer(self):
        login_response = self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)
        self.assertEqual(login_response.status_code, 200)
        self.assertIn('Admin Dashboard', login_response.get_data(as_text=True))

        product_response = self.client.post('/admin/products', data={
            'name': 'Gaming Mouse',
            'price': '89',
            'currency': 'PKR',
            'category': 'Accessories',
            'image': '',
            'description': 'A fast gaming mouse.'
        }, follow_redirects=True)
        self.assertEqual(product_response.status_code, 200)
        self.assertIn('Gaming Mouse', product_response.get_data(as_text=True))

        offer_response = self.client.post('/admin/offers', data={
            'title': 'Weekend Flash Sale',
            'description': 'Up to 30% off on select devices.',
            'discount': '30',
            'code': 'FLASH30'
        }, follow_redirects=True)
        self.assertEqual(offer_response.status_code, 200)
        self.assertIn('Weekend Flash Sale', offer_response.get_data(as_text=True))

        home_response = self.client.get('/')
        self.assertIn('Weekend Flash Sale', home_response.get_data(as_text=True))

    def test_admin_can_create_product_with_zero_quantity_and_show_out_of_stock(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Stocked Product',
            'price': '150',
            'currency': 'PKR',
            'category': 'Accessories',
            'description': 'A product with no stock left.',
            'quantity': '0'
        }, follow_redirects=True)

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        self.assertIn('Stocked Product', home_response.get_data(as_text=True))
        self.assertIn('Out of stock', home_response.get_data(as_text=True))

        product = next((product for product in catalog_models.get_all_products() if product['name'] == 'Stocked Product'), None)
        self.assertIsNotNone(product)
        admin_response = self.client.get('/admin/dashboard')
        self.assertEqual(admin_response.status_code, 200)
        self.assertIn('Out of stock products:', admin_response.get_data(as_text=True))
        self.assertIn(f'#{product["id"]}', admin_response.get_data(as_text=True))

    def test_home_page_filters_products_by_category_and_price(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Budget Phone',
            'price': '500',
            'currency': 'PKR',
            'category': 'Phones',
            'description': 'A budget device.'
        }, follow_redirects=True)
        self.client.post('/admin/products', data={
            'name': 'Premium Laptop',
            'price': '6000',
            'currency': 'PKR',
            'category': 'Laptops',
            'description': 'A premium device.'
        }, follow_redirects=True)

        filtered_response = self.client.get('/?category=Phones&price=under-1000')
        self.assertEqual(filtered_response.status_code, 200)
        self.assertIn('Budget Phone', filtered_response.get_data(as_text=True))
        self.assertNotIn('Premium Laptop', filtered_response.get_data(as_text=True))
        self.assertIn('name="category"', filtered_response.get_data(as_text=True))
        self.assertIn('name="price"', filtered_response.get_data(as_text=True))

    def test_home_page_shows_all_saved_categories_in_filter(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Wireless Charger',
            'price': '2500',
            'currency': 'PKR',
            'category': 'Accessories',
            'description': 'Fast charging pad.'
        }, follow_redirects=True)
        self.client.post('/admin/products', data={
            'name': 'Smart Watch',
            'price': '1200',
            'currency': 'PKR',
            'category': 'Wearables',
            'description': 'Fitness tracker watch.'
        }, follow_redirects=True)

        home_response = self.client.get('/')
        html = home_response.get_data(as_text=True)
        self.assertEqual(home_response.status_code, 200)
        self.assertIn('Accessories', html)
        self.assertIn('Wearables', html)

    def test_admin_can_update_home_page_filter_options(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})

        response = self.client.post('/admin/filters', data={
            'categories': 'Phones\nLaptops',
            'price_ranges': 'under-1000:Under PKR 1,000\nabove-5000:Above PKR 5,000'
        }, follow_redirects=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Homepage filters updated successfully.', response.get_data(as_text=True))

        home_response = self.client.get('/')
        self.assertIn('Under PKR 1,000', home_response.get_data(as_text=True))
        self.assertIn('Phones', home_response.get_data(as_text=True))

    def test_admin_dashboard_homepage_filter_editor_shows_saved_categories(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Desk Lamp',
            'price': '1800',
            'currency': 'PKR',
            'category': 'Lighting',
            'description': 'A bright desk lamp.'
        }, follow_redirects=True)

        response = self.client.get('/admin/dashboard')
        html = response.get_data(as_text=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn('Lighting', html)

    def test_admin_dashboard_stats_api_returns_expected_keys(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)
        response = self.client.get('/admin/api/dashboard-stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertIsInstance(data, dict)
        self.assertIn('total_orders', data)
        self.assertIn('total_revenue', data)
        self.assertIn('pending_orders_count', data)
        self.assertIn('order_status_breakdown', data)
        self.assertIn('top_selling_products', data)
        self.assertIn('category_wise_sales', data)
        self.assertIn('recent_orders', data)

    def test_recent_orders_dashboard_excludes_delivered_orders(self):
        conn = sqlite3.connect(self.temp_db_path)
        conn.execute('INSERT INTO customers (full_name, email, phone, address, created_at) VALUES (?, ?, ?, ?, ?)',
                     ('Ali', 'ali@example.com', '03001234567', 'Main Street', '2026-08-08 12:00:00'))
        conn.execute('INSERT INTO customers (full_name, email, phone, address, created_at) VALUES (?, ?, ?, ?, ?)',
                     ('Sara', 'sara@example.com', '03007654321', 'Market Road', '2026-08-09 10:00:00'))
        conn.execute('INSERT INTO orders (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)',
                     (1, '1500', 'pending', '2026-08-08 12:00:00'))
        conn.execute('INSERT INTO orders (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)',
                     (2, '2200', 'on_the_way', '2026-08-09 11:00:00'))
        conn.execute('INSERT INTO orders (customer_id, total, status, created_at) VALUES (?, ?, ?, ?)',
                     (1, '5000', 'delivered', '2026-08-10 09:00:00'))
        conn.commit()
        conn.close()

        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD}, follow_redirects=True)
        response = self.client.get('/admin/api/dashboard-stats')
        self.assertEqual(response.status_code, 200)
        recent_orders = response.get_json()['recent_orders']
        self.assertEqual([item['status'] for item in recent_orders], ['on_the_way', 'pending'])
        self.assertNotIn('delivered', [item['status'] for item in recent_orders])

    def test_new_category_is_added_to_homepage_filters(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Smart Watch',
            'price': '1200',
            'currency': 'PKR',
            'category': '__new__',
            'new_category': 'Smart Watches',
            'description': 'A trendy device.'
        }, follow_redirects=True)

        home_response = self.client.get('/')
        self.assertEqual(home_response.status_code, 200)
        self.assertIn('Smart Watches', home_response.get_data(as_text=True))

    def test_uploaded_product_persists_after_restart(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Portable Speaker',
            'price': '129',
            'currency': 'USD',
            'category': 'Audio',
            'description': 'Great sound.'
        }, follow_redirects=True)

        importlib.reload(catalog_models)
        importlib.reload(order_models)
        importlib.reload(admin_models)
        restarted_app = create_app()
        restarted_client = restarted_app.test_client()

        with sqlite3.connect(routes_module.DB_PATH) as conn:
            row = conn.execute('SELECT id FROM products WHERE name = ?', ('Portable Speaker',)).fetchone()

        self.assertIsNotNone(row)
        detail_response = restarted_client.get(f"/product/{row[0]}")
        self.assertEqual(detail_response.status_code, 200)
        self.assertIn('Portable Speaker', detail_response.get_data(as_text=True))

    def test_unified_database_contains_relational_tables_with_foreign_keys(self):
        conn = sqlite3.connect(routes_module.DB_PATH)
        tables = {row[0] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        self.assertTrue({'admin_users', 'categories', 'products', 'offers', 'customers', 'orders', 'order_items'}.issubset(tables))

        foreign_keys = conn.execute("PRAGMA foreign_key_list(orders)").fetchall()
        self.assertTrue(any(fk[2] == 'customers' for fk in foreign_keys))
        conn.close()

    def test_checkout_creates_order_and_shows_it_in_admin_dashboard(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Starter Laptop',
            'price': '499',
            'currency': 'PKR',
            'category': 'Laptops',
            'description': 'A clean starter laptop.'
        }, follow_redirects=True)

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Starter Laptop')
        self.client.post('/add_to_cart', data={'product_id': product['id']}, follow_redirects=True)

        checkout_page = self.client.get('/checkout')
        self.assertEqual(checkout_page.status_code, 200)
        self.assertIn('Delivery charges', checkout_page.get_data(as_text=True))
        self.assertIn('PKR 250', checkout_page.get_data(as_text=True))

        checkout_response = self.client.post('/checkout', data={
            'name': 'Alice Johnson',
            'email': 'alice@example.com',
            'phone': '03001234567',
            'address': '123 Main Street'
        }, follow_redirects=True)

        self.assertEqual(checkout_response.status_code, 200)
        self.assertIn('Order placed successfully', checkout_response.get_data(as_text=True))

        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        admin_response = self.client.get('/admin/dashboard')
        self.assertIn('Alice Johnson', admin_response.get_data(as_text=True))
        self.assertIn('alice@example.com', admin_response.get_data(as_text=True))
        self.assertIn('PKR 749', admin_response.get_data(as_text=True))
        self.assertIn('1 pending order', admin_response.get_data(as_text=True))

    def test_checkout_persists_coupon_data_on_the_saved_order(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Promo Laptop',
            'price': '500',
            'currency': 'PKR',
            'category': 'Laptops',
            'description': 'A laptop for coupon testing.'
        }, follow_redirects=True)

        with sqlite3.connect(self.temp_db_path) as conn:
            conn.execute(
                'INSERT INTO offers (title, description, discount, code) VALUES (?, ?, ?, ?)',
                ('Spring Sale', '10% off', '10%', 'SPRING10')
            )
            conn.commit()

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Promo Laptop')
        self.client.post('/add_to_cart', data={'product_id': product['id']}, follow_redirects=True)

        checkout_response = self.client.post('/checkout', data={
            'name': 'Coupon Buyer',
            'email': 'coupon@example.com',
            'phone': '03001234567',
            'address': '77 Promo Street',
            'coupon_code': 'SPRING10'
        }, follow_redirects=True)

        self.assertEqual(checkout_response.status_code, 200)
        self.assertIn('Order placed successfully', checkout_response.get_data(as_text=True))

        with sqlite3.connect(self.temp_db_path) as conn:
            row = conn.execute(
                'SELECT coupon_code, discount_text FROM orders WHERE customer_id = (SELECT id FROM customers WHERE email = ?)',
                ('coupon@example.com',)
            ).fetchone()

        self.assertIsNotNone(row)
        self.assertEqual(row[0], 'SPRING10')
        self.assertIn('SPRING10', row[1])
        self.assertIn('10', row[1])

    def test_admin_cannot_delete_product_that_has_been_ordered(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Ordered Product',
            'price': '199',
            'currency': 'PKR',
            'category': 'Gadgets',
            'description': 'A product already ordered.'
        }, follow_redirects=True)

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Ordered Product')
        self.client.post('/add_to_cart', data={'product_id': product['id']}, follow_redirects=True)
        self.client.post('/checkout', data={
            'name': 'Charlie Buyer',
            'email': 'charlie@example.com',
            'phone': '03001234567',
            'address': '789 Shopper Lane'
        }, follow_redirects=True)

        delete_response = self.client.post(f'/admin/products/{product["id"]}/delete', follow_redirects=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn('Product cannot be deleted because it is referenced by existing orders.', delete_response.get_data(as_text=True))
        self.assertIsNotNone(catalog_models.get_product(product['id']))

    def test_admin_can_update_existing_product(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Wireless Mouse',
            'price': '59',
            'currency': 'PKR',
            'category': 'Accessories',
            'description': 'A simple mouse.'
        }, follow_redirects=True)

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Wireless Mouse')
        update_response = self.client.post(f'/admin/products/{product["id"]}/update', data={
            'name': 'Wireless Mouse Pro',
            'price': '89',
            'currency': 'PKR',
            'category': 'Accessories',
            'image': '',
            'description': 'An upgraded mouse.'
        }, follow_redirects=True)

        self.assertEqual(update_response.status_code, 200)
        self.assertIn('Wireless Mouse Pro', update_response.get_data(as_text=True))

        updated_product = catalog_models.get_product(product['id'])
        self.assertEqual(updated_product['name'], 'Wireless Mouse Pro')
        self.assertEqual(updated_product['description'], 'An upgraded mouse.')

    def test_admin_update_product_accepts_ajax_requests(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Keyboard',
            'price': '79',
            'currency': 'PKR',
            'category': 'Accessories',
            'description': 'A simple keyboard.'
        }, follow_redirects=True)

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Keyboard')
        update_response = self.client.post(
            f'/admin/products/{product["id"]}/update',
            data={
                'name': 'Mechanical Keyboard',
                'price': '129',
                'currency': 'PKR',
                'category': 'Accessories',
                'image': '',
                'description': 'An upgraded keyboard.'
            },
            headers={'X-Requested-With': 'XMLHttpRequest'}
        )

        self.assertEqual(update_response.status_code, 200)
        self.assertTrue(update_response.get_json()['success'])
        updated_product = catalog_models.get_product(product['id'])
        self.assertEqual(updated_product['name'], 'Mechanical Keyboard')
        self.assertEqual(updated_product['description'], 'An upgraded keyboard.')

    def test_uploaded_image_file_uses_product_id_and_deletes_when_product_removed(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        image_bytes = io.BytesIO(b'Test image content')
        image_bytes.name = 'product-photo.jpg'

        response = self.client.post(
            '/admin/products',
            data={
                'name': 'Image Test Product',
                'price': '199',
                'currency': 'PKR',
                'category': 'Gadgets',
                'description': 'Product with image upload.',
                'image_file': (image_bytes, image_bytes.name)
            },
            content_type='multipart/form-data',
            follow_redirects=True
        )
        self.assertEqual(response.status_code, 200)
        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Image Test Product')
        self.assertIsNotNone(product)
        self.assertRegex(product['image'], r'/static/images/uploads/\d+\.jpg')

        filename = product['image'].split('/static/', 1)[1].replace('/', os.sep)
        filepath = os.path.join(self.app.static_folder, filename)
        self.assertTrue(os.path.exists(filepath))

        delete_response = self.client.post(f'/admin/products/{product["id"]}/delete', follow_redirects=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertFalse(os.path.exists(filepath))
        self.assertIsNone(catalog_models.get_product(product['id']))

    def test_product_supports_multiple_uploaded_images(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})

        first_image = io.BytesIO(b'First image content')
        first_image.name = 'front.jpg'
        second_image = io.BytesIO(b'Second image content')
        second_image.name = 'side.png'

        response = self.client.post(
            '/admin/products',
            data={
                'name': 'Multi Image Product',
                'price': '450',
                'currency': 'PKR',
                'category': 'Gadgets',
                'description': 'Product with multiple gallery images.',
                'image_file': [
                    (first_image, first_image.name),
                    (second_image, second_image.name),
                ]
            },
            content_type='multipart/form-data',
            follow_redirects=True,
        )

        self.assertEqual(response.status_code, 200)
        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Multi Image Product')
        self.assertGreaterEqual(len(product['images']), 2)
        self.assertTrue(all(url.startswith('/static/images/uploads/') for url in product['images']))
        self.assertEqual(product['image'], product['images'][0])

    def test_admin_can_mark_order_delivered_and_delete_it(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        self.client.post('/admin/products', data={
            'name': 'Desk Monitor',
            'price': '299',
            'currency': 'PKR',
            'category': 'Accessories',
            'description': 'A clean desk monitor.'
        }, follow_redirects=True)

        product = next(product for product in catalog_models.get_all_products() if product['name'] == 'Desk Monitor')
        self.client.post('/add_to_cart', data={'product_id': product['id']}, follow_redirects=True)
        self.client.post('/checkout', data={
            'name': 'Bob Smith',
            'email': 'bob@example.com',
            'phone': '03123456789',
            'address': '456 Market Road'
        }, follow_redirects=True)

        order = order_models.get_all_orders()[0]
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        status_response = self.client.post(f'/admin/orders/{order["id"]}/status', data={'status': 'delivered'}, follow_redirects=True)
        self.assertEqual(status_response.status_code, 200)
        self.assertIn('Order marked as delivered', status_response.get_data(as_text=True))

        delete_response = self.client.post(f'/admin/orders/{order["id"]}/delete', follow_redirects=True)
        self.assertEqual(delete_response.status_code, 200)
        self.assertIn('Order deleted successfully', delete_response.get_data(as_text=True))

    def test_paginated_product_loading_and_indexes_are_available(self):
        self.client.post('/admin/login', data={'username': 'admin', 'password': TEST_ADMIN_PASSWORD})
        for name in ['Alpha Product', 'Beta Product', 'Gamma Product']:
            self.client.post('/admin/products', data={
                'name': name,
                'price': '100',
                'currency': 'PKR',
                'category': 'Accessories',
                'description': f'{name} description.'
            }, follow_redirects=True)

        page_one = catalog_models.get_all_products(page=1, per_page=2)
        self.assertEqual(len(page_one), 2)
        page_two = catalog_models.get_all_products(page=2, per_page=2)
        self.assertEqual(len(page_two), 1)

        with sqlite3.connect(routes_module.DB_PATH) as conn:
            index_names = {row[1] for row in conn.execute("PRAGMA index_list(products)")}

        self.assertIn('idx_products_name', index_names)
        self.assertIn('idx_products_category_id', index_names)

    def test_feature_model_modules_are_available(self):
        admin_module = importlib.import_module('app.models.admin_models')
        catalog_module = importlib.import_module('app.models.catalog_models')
        order_module = importlib.import_module('app.models.order_models')

        self.assertTrue(hasattr(admin_module, 'init_admin_db'))
        self.assertTrue(hasattr(catalog_module, 'get_all_products'))
        self.assertTrue(hasattr(order_module, 'save_order'))


if __name__ == '__main__':
    unittest.main()
