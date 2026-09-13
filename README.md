# ecommerce premium

Banta Bazar is a Flask-based ecommerce storefront for electronics and accessories. Customers can browse and search the catalog, manage a session-based cart, apply offers, submit reviews, and place orders. A protected admin area provides catalog, order, homepage-content, and analytics management.

## Features

- Responsive storefront with home, shop, search, product details, about, contact, cart, and checkout pages
- Product categories, sale pricing, stock validation, image uploads, galleries, and customer reviews
- Session-based cart with AJAX quantity updates, item removal, coupons, delivery charges, and order creation
- Admin login with hashed passwords and temporary lockout after repeated failed attempts
- Admin CRUD for products, offers, orders, hero slides, homepage filters, trust badges, and site content
- Product-view and cart-event analytics with a Chart.js admin dashboard
- Live product viewer counts using Flask-SocketIO
- CSRF protection, response compression, SEO metadata, JSON-LD, sitemap, robots.txt, and `llms.txt`

## Tech Stack

- Python 3.10+ and Flask 3.1
- Jinja2 templates and vanilla JavaScript
- SQLite by default, with optional MySQL support
- Flask-WTF, Flask-SocketIO, Flask-Compress, Pillow, and python-dotenv
- Optional React/Vite frontend in `frontend/`

## Quick Start

### 1. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS/Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install Python dependencies

```bash
python -m pip install -r requirements.txt
```

### 3. Configure the application

Create a `.env` file in the project root. At minimum, set a secret key and admin password:

```env
SECRET_KEY=replace-with-a-long-random-value
ADMIN_PASSWORD=replace-with-a-strong-admin-password
```

SQLite is used by default and the database is created at `shop.db`. The upload directory is created automatically at `app/static/images/uploads`.

### 4. Start the server

```bash
python run.py
```

Open [http://localhost:5000](http://localhost:5000). The admin area is available at `/admin/login`.

## Configuration

The following environment variables are supported:

| Variable | Default | Purpose |
| --- | --- | --- |
| `SECRET_KEY` or `FLASK_SECRET_KEY` | Development fallback | Flask session and CSRF signing key |
| `ADMIN_PASSWORD` | None | Admin login password configuration |
| `DB_TYPE` | `sqlite` | Use `sqlite` or `mysql` |
| `DATABASE_PATH` | `./shop.db` | SQLite database path |
| `MYSQL_HOST` | `localhost` | MySQL host |
| `MYSQL_PORT` | `3306` | MySQL port |
| `MYSQL_USER` | `root` | MySQL user |
| `MYSQL_PASSWORD` | None | MySQL password |
| `MYSQL_DB` | `ecommerce_db` | MySQL database name |
| `UPLOAD_FOLDER` | `app/static/images/uploads` | Uploaded image directory |
| `SESSION_LIFETIME_DAYS` | `10` | Permanent session lifetime |
| `LOGIN_MAX_ATTEMPTS` | `5` | Failed login attempts before lockout |
| `LOGIN_LOCKOUT_MINUTES` | `15` | Admin login lockout duration |

Never commit `.env`, passwords, or production secrets.

## Optional Frontend Build

The `frontend/` directory contains a separate Vite/React package:

```bash
cd frontend
npm install
npm run build
```

The generated `frontend/dist` assets can be served by the Flask application. The main storefront currently uses the Jinja templates and files under `app/templates` and `app/static`.

## Testing

Install the dependencies, activate the virtual environment, and run:

```bash
python -m pytest
```

The test suite covers admin behavior, product analytics, live viewer tracking, and SEO responses.

## Project Layout

```text
app/
	models/       Database and domain logic
	routes/       Flask route blueprints
	templates/    Jinja2 pages and partials
	static/       CSS, JavaScript, and uploaded images
tests/          Automated tests
frontend/       Optional React/Vite frontend
run.py          Application entry point
FEATURES.md     Detailed feature inventory
project_rules.md
								Project organization and security rules
```

## Notes

- Checkout creates orders and decrements inventory, but no external payment gateway is currently integrated.
- Customer accounts and public customer authentication are not currently implemented.
- For production, use HTTPS, a strong explicit `SECRET_KEY`, a production database, restricted CORS origins, and a production-ready Socket.IO deployment configuration.

