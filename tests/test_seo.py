import gc
import os
import tempfile
import unittest
from pathlib import Path

from app import create_app
from app.models import catalog_models, shared_models


class SeoTests(unittest.TestCase):
    def setUp(self):
        self.db_tempdir = tempfile.TemporaryDirectory()
        self.temp_db_path = str(Path(self.db_tempdir.name) / 'shop.db')
        shared_models.DB_PATH = self.temp_db_path
        catalog_models.DB_PATH = self.temp_db_path

        if os.path.exists(shared_models.DB_PATH):
            os.remove(shared_models.DB_PATH)
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

    def test_homepage_includes_seo_meta_tags_and_json_ld(self):
        response = self.client.get('/')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('<title>', html)
        self.assertIn('meta name="description"', html)
        self.assertIn('meta property="og:title"', html)
        self.assertIn('meta property="og:description"', html)
        self.assertIn('rel="canonical"', html)
        self.assertIn('application/ld+json', html)

    def test_about_page_uses_clear_geo_content_and_author_metadata(self):
        response = self.client.get('/about')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('About Banta Bazar', html)
        self.assertIn('Frequently asked questions', html)
        self.assertIn('meta name="author"', html)
        self.assertIn('Banta Bazar Team', html)

    def test_robots_and_sitemap_endpoints_are_available(self):
        robots_response = self.client.get('/robots.txt')
        self.assertEqual(robots_response.status_code, 200)
        self.assertIn('Sitemap:', robots_response.get_data(as_text=True))

        sitemap_response = self.client.get('/sitemap.xml')
        self.assertEqual(sitemap_response.status_code, 200)
        self.assertIn('<urlset', sitemap_response.get_data(as_text=True))

    def test_product_page_supports_slug_urls_and_product_schema(self):
        product_id = catalog_models.save_product(
            'Wireless Mouse',
            '89',
            'PKR',
            '',
            'Accessories',
            'A fast wireless mouse for everyday work.'
        )

        response = self.client.get(f'/product/{product_id}/wireless-mouse')
        html = response.get_data(as_text=True)

        self.assertEqual(response.status_code, 200)
        self.assertIn('Wireless Mouse', html)
        self.assertIn('application/ld+json', html)
        self.assertIn('"@type": "Product"', html)

    def test_llms_and_custom_404_pages_are_available(self):
        llms_response = self.client.get('/llms.txt')
        self.assertEqual(llms_response.status_code, 200)
        self.assertIn('Banta Bazar', llms_response.get_data(as_text=True))

        missing_response = self.client.get('/definitely-missing-page')
        self.assertEqual(missing_response.status_code, 404)
        self.assertIn('Page not found', missing_response.get_data(as_text=True))
