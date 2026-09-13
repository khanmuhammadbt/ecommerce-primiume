"""Route blueprints for the Flask application."""

from .admin import register_admin_routes  # noqa: F401
from .main import register_main_routes  # noqa: F401
from .products import register_products_routes  # noqa: F401

