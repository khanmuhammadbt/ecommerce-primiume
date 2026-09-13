# Project Features

## 1. Project Overview

- **Project name:** Banta Bazar Ecommerce
- **Purpose:** Electronics and accessories ke liye Flask-based ecommerce storefront. Customers products browse/search kar sakte hain, cart aur checkout use kar sakte hain, reviews submit kar sakte hain; admins catalog, orders, homepage content aur analytics manage kar sakte hain.
- **Tech stack:**
  - Flask 3.1
  - Jinja2 templates
  - SQLite ya MySQL database support
  - Flask-WTF / CSRFProtect
  - Flask-SocketIO aur Socket.IO client
  - Flask-Compress
  - Pillow image processing
  - python-dotenv configuration
  - Chart.js CDN for admin analytics
- **Application entry point:** `run.py` (Socket.IO server `0.0.0.0:3000` par run hota hai)
- **Configuration:** `app/config.py` environment-based secret key, database, upload folder, admin password, session lifetime aur login lockout settings load karta hai.

## 2. Pages and Their Features

### Home Page

- **Route:** `/`
- **Route function:** `home()` in `app/routes/main/home_routes.py`
- **Template:** `app/templates/index.html`
- **Hero slider:** `index.html` mein hero slides, dots, keyboard activation aur automatic rotation.
- **Trust badges:** Homepage trust badges display karta hai; admin dashboard se manage kiye ja sakte hain.
- **Product filters and categories:** Category links aur homepage filters ke through catalog browsing.
- **Initial product listing:** Homepage par initial six products render hote hain.
- **Load more products:** Inline JavaScript `/load-more-products` endpoint ko call karke additional product cards load karta hai.
- **Feature slider:** Homepage feature content ka slider.
- **SEO content:** Homepage metadata aur structured content shared layout ke through provide hota hai.

### Product Listing / Shop Page

- **Route:** `/shop`
- **Route function:** `shop()` in `app/routes/products/shop_routes.py`
- **Template:** `app/templates/shop.html`
- **Catalog listing:** Available products ka full catalog display karta hai.
- **Product cards:** Shared product-card partial `app/templates/partials/product_cards.html` use hota hai.
- **Product information:** Cards product image, pricing, sale pricing, stock-related information aur product link show karte hain.

### Search Page

- **Route:** `/search?q=...`
- **Route function:** `search()` in `app/routes/main/search_routes.py`
- **Template:** `app/templates/search.html`
- **Product search:** Query parameter ke basis par products search karke results render karta hai.

### Product Detail Page

- **Routes:** `/product/<product_id>` aur `/product/<product_id>/<product_slug>`
- **Route function:** `product_details()` in `app/routes/products/product_detail_routes.py`
- **Template:** `app/templates/product_details.html`
- **Product gallery:** Main image aur thumbnails ke beech client-side switching.
- **Pricing and stock:** Regular/sale pricing aur current stock status display.
- **Reviews:** Existing reviews display karta hai aur `POST /product/<id>/review` se validated rating/comment submit hote hain.
- **Structured product data:** Product SEO ke liye Product JSON-LD structured data.
- **Live viewer count:** Product-specific Socket.IO room ke through current viewer count.
- **Add to cart:** Product quantity ko cart endpoint ke through cart mein add karta hai.

### Cart Page

- **Route:** `/cart`
- **Route function:** `cart()` in `app/routes/main/cart_routes.py`
- **Template:** `app/templates/cart.html`
- **Cart snapshot:** Session cart ke items, quantities, prices aur totals show karta hai.
- **Quantity updates:** `POST /update_cart_quantity` stock validation ke saath quantity increase/decrease karta hai.
- **Remove items:** `POST /remove_from_cart` se cart item remove hota hai.
- **Cart AJAX:** `app/static/js/cart-ajax.js` fetch requests ke through cart actions aur UI updates handle karta hai.
- **Coupon and totals:** Cart/checkout flow coupon discounts aur calculated totals support karta hai.

### Checkout Page

- **Route:** `/checkout` (GET/POST)
- **Route function:** `checkout()` in `app/routes/main/checkout_routes.py`
- **Template:** `app/templates/checkout.html`
- **Customer details:** Checkout form customer/order information collect karta hai.
- **Stock validation:** Order create karne se pehle product stock validate hota hai.
- **Delivery fee:** Configured delivery charge totals mein add hota hai.
- **Coupons:** Valid coupon/offer apply karke order total calculate hota hai.
- **Order creation:** Order aur order items database mein save hote hain.
- **Inventory decrement:** Successful order par product inventory reduce hoti hai.
- **Payment integration:** Codebase mein external payment gateway/API implemented nahi mila.

### Admin Login Page

- **Routes:** `/admin/login` (GET/POST), `/admin/logout`
- **Route functions:** `admin_login()` aur `admin_logout()` in `app/routes/admin/login_routes.py`
- **Template:** `app/templates/admin_login.html`
- **Admin authentication:** Admin credentials verify karke `session['is_admin']` session flag set hota hai.
- **Password hashing:** Werkzeug password hashing/verification use hoti hai.
- **Login lockout:** Failed attempts username/IP ke saath track hote hain aur temporary expiry-based lockout apply hota hai.
- **Customer signup:** Public customer login/signup page ya customer authentication system codebase mein nahi mila.

### Admin Dashboard

- **Route:** `/admin/dashboard`
- **Route function:** `admin_dashboard()` in `app/routes/admin/dashboard_routes.py`
- **Template:** `app/templates/admin_dashboard.html`
- **Product management:** `admin_create_product()`, `admin_update_product()`, `admin_delete_product()` se product CRUD.
- **Order management:** `admin_update_order_status()` aur `admin_delete_order()` se orders manage hote hain.
- **Offer management:** `admin_create_offer()`, `admin_update_offer()`, `admin_delete_offer()` se offers/coupons manage hote hain.
- **Homepage management:** `admin_update_hero()`, `admin_add_hero_slide()`, `admin_update_hero_slide()`, `admin_delete_hero_slide()` se hero content manage hota hai.
- **Homepage settings:** `admin_update_homepage_filters()`, `admin_update_delivery_charge()`, `admin_update_trust_badge()` filters, delivery aur badges update karte hain.
- **Admin password:** `admin_change_password()` admin password change karta hai.
- **Analytics:** Dashboard analytics view aur API se sales/product metrics available hain.

### Admin Analytics Page

- **Route:** `/admin/dashboard/analytics`
- **Route function:** `admin_dashboard_analytics()` in `app/routes/admin/dashboard_routes.py`
- **Template:** `app/templates/admin/analytics.html`
- **Analytics charts:** Product views, cart events, ratings, category summaries aur percentages ko Chart.js ke saath display karta hai.
- **Analytics data:** Admin-protected `/admin/api/dashboard-stats` endpoint se dashboard statistics milti hain.

### Admin About Page

- **Route:** `/admin/about` (GET/POST)
- **Route function:** `admin_edit_about()` in `app/routes/admin/about_routes.py`
- **Template:** `app/templates/admin_about.html`
- **About content management:** Admin about-page content edit aur save kar sakta hai.

### Admin Contact Page

- **Route:** `/admin/contact` (GET/POST)
- **Route function:** `admin_edit_contact()` in `app/routes/admin/contact_routes.py`
- **Template:** `app/templates/admin_contact.html`
- **Contact content management:** Admin contact-page content edit aur save kar sakta hai.

### Public About Page

- **Route:** `/about`
- **Route function:** `about()` in `app/routes/main/about_routes.py`
- **Template:** `app/templates/about.html`
- **About information:** Store/site ka about content render karta hai.

### Public Contact Page

- **Route:** `/contact`
- **Route function:** `contact()` in `app/routes/main/contact_routes.py`
- **Template:** `app/templates/contact.html`
- **Contact information:** Site ka contact content render karta hai.

### Error and SEO Pages

- **404 page:** `handle_not_found()` in `app/__init__.py`, template `app/templates/404.html`.
- **Robots:** `/robots.txt` via `robots_txt()`.
- **Sitemap:** `/sitemap.xml` via `sitemap_xml()`.
- **LLMs metadata:** `/llms.txt` via `llms_txt()`.
- **Shared layout:** `app/templates/base.html` common navigation, metadata, CSRF meta tag, stylesheets aur Socket.IO client include karta hai.

## 3. Backend Features

### Authentication and Authorization

- **Admin-only access:** `is_admin()` in `app/models/order/admin.py` session ke `is_admin` flag se protected routes guard karta hai.
- **Credential verification:** `verify_admin_login()` in `app/models/admin/user.py` hashed admin passwords verify karta hai.
- **Session-based auth:** Successful admin login ke baad admin session create hota hai; `/admin/logout` session end karta hai.
- **Brute-force lockout:** `admin_login_attempts` table mein username/IP, failure count aur expiry store hote hain.
- **Not implemented:** Customer authentication, signup, password reset, API-token auth, CAPTCHA aur Flask-Limiter initialization codebase mein nahi mila.

### Cart Logic

- **Cart initialization:** `initialize_cart()` in `app/models/order/cart.py` session cart initialize karta hai.
- **Cart snapshot:** `get_cart_snapshot()` session items aur totals ka current snapshot banata hai.
- **Add item:** `add_to_cart()` in `app/routes/main/cart_routes.py`, `POST /add_to_cart`, form ya JSON input accept karta hai, product/stock validate karta hai, cart update karta hai aur analytics record karta hai.
- **Remove item:** `remove_from_cart()`, `POST /remove_from_cart`.
- **Update quantity:** `update_cart_quantity()`, `POST /update_cart_quantity`, stock validation ke saath quantity update karta hai.

### AJAX and API Endpoints

- **`POST /add_to_cart`:** JSON request par JSON response ke saath cart update.
- **`POST /remove_from_cart`:** Cart item removal.
- **`POST /update_cart_quantity`:** AJAX-compatible quantity update.
- **`GET /load-more-products`:** Rendered product-card HTML aur `has_more` flag return karta hai; `load_more_products()`.
- **`POST /product/<id>/review`:** Validated review/rating save karta hai; `product_review()`.
- **`GET /admin/api/dashboard-stats`:** Admin-protected analytics JSON; `admin_dashboard_stats_api()`.
- **Admin mutations:** AJAX request advertise hone par admin success responses JSON return kar sakte hain via `is_ajax_request()` aur `send_admin_success()`.
- **General APIs not found:** Public product JSON API, checkout/payment API, webhook API ya formal REST API schema codebase mein nahi mila.

### Admin Analytics

- **Model/query layer:** `app/models/analytics.py` product views, add-to-cart quantity, session/IP/user-agent/source-page data, ratings, category summaries aur percentages record/query karta hai.
- **Dashboard API:** `admin_dashboard_stats_api()` analytics payload provide karta hai.
- **Tests:** `tests/test_product_analytics.py` aggregation behavior aur `tests/test_admin_panel.py` dashboard API behavior cover karte hain.

### Database Models

- **Database abstraction:** `app/models/shared/database.py` SQLite/MySQL connection/support provide karta hai.
- **Catalog:** `app/models/catalog/product.py` categories, products, pagination, search, sale prices, reviews, image URLs, uploads aur deletion handle karta hai.
- **Orders and cart:** `app/models/order/cart.py` customers, orders, order items, coupons, cart state aur totals handle karta hai.
- **Admin/site content:** `app/models/admin/user.py`, `app/models/admin/homepage.py`, `app/models/admin/page.py`, `app/models/admin/site.py`.
- **Analytics:** `app/models/analytics.py`.
- **Tables:** `admin_users`, `pages`, `categories`, `products`, `offers`, `customers`, `orders`, `order_items`, homepage configuration tables, `admin_login_attempts`, `product_views` aur `product_cart_events`.

### CSRF Protection

- **Global protection:** `CSRFProtect` in `app/__init__.py` globally enabled hai.
- **Template token:** `base.html` CSRF token ko meta tag aur POST forms mein expose karta hai.
- **AJAX token:** `app/static/js/cart-ajax.js` `X-CSRFToken` header send karta hai.
- **Coverage:** Admin panel tests CSRF visibility/behavior verify karte hain in `tests/test_admin_panel.py`.

## 4. Frontend Features

### Responsive Design

- **Global styles:** `app/static/css/reset.css`, `app/static/css/layout.css`, `app/static/css/home.css`.
- **Feature styles:** `app/static/css/cart.css`, `app/static/css/checkout.css`, `app/static/css/admin.css`, `app/static/css/admin-dashboard.css`.
- **Breakpoints:** Layout, home, cart, checkout, admin aur dashboard stylesheets mein 980px, 900px, 768px, 720px, 560px, 490px, 420px aur 375px responsive behavior.
- **Mobile navigation:** `base.html` mein navigation/search toggles, `aria-expanded` updates aur Escape-key handling.
- **Admin mobile layout:** Admin sidebar overlay behavior responsive styles/scripts ke through.
- **Verified responsive sizes:** 320px, 375px, 480px, 768px aur 1440px par overflow-free behavior documented hai.

### JavaScript Functionality

- **Cart AJAX:** `app/static/js/cart-ajax.js` add/remove/update cart fetch requests, CSRF header, response handling aur cart UI updates manage karta hai.
- **Admin dashboard:** `app/static/js/admin-dashboard.js` `/admin/api/dashboard-stats` fetch karke analytics dashboard update karta hai.
- **Home interactions:** `app/templates/index.html` mein hero slider, keyboard controls, auto-rotation, dots, category links, feature slider aur load-more interaction.
- **Product gallery:** `app/templates/product_details.html` mein thumbnail-based image switching.
- **Navigation/search:** `app/templates/base.html` mein mobile menu aur search toggle.

### WebSocket Live Viewer Count

- **Server:** `app/live_viewers.py` mein `handle_join_product()`, `handle_leave_product()` aur `handle_disconnect()`.
- **Events:** `join_product`, `leave_product`, `disconnect` aur emitted `viewer_count`.
- **Rooms:** Product-specific Socket.IO rooms `product_<id>`.
- **Reliability behavior:** In-memory viewer maps, one-second broadcast throttling aur 60-second stale-socket cleanup.
- **Client:** Socket.IO CDN client `base.html` mein included hai; product detail client logic `product_details.html` mein inline hai.

## 5. Performance Features

- **Image lazy loading:** `app/templates/partials/product_cards.html` product-card images par fixed `width`/`height` aur `loading="lazy"` use karta hai.
- **Hero image priority:** `app/templates/index.html` ka first hero image `fetchpriority="high"` use karta hai.
- **Image optimization:** `save_optimized_image()` in `app/utils/__init__.py` aur `utils/images.py` Pillow ke through uploaded product/hero images ko JPEG, maximum `800x800`, quality `80` mein convert karta hai.
- **Non-blocking CSS:** `base.html` cart, admin aur dashboard stylesheets ko `media="print"` aur `onload` switching ke saath load karta hai.
- **Response compression:** `Flask-Compress` `app/__init__.py` mein enabled hai.
- **Lighthouse-specific work:** Dedicated Lighthouse config, report, CI job ya explicit Lighthouse score files codebase mein nahi mile. Upar listed image, CSS loading aur response compression optimizations existing performance work hain.
- **Not found:** `srcset`, responsive image sizes, `IntersectionObserver`, custom lazy-loading code, CSS/JS bundling or minification, service worker, caching headers, resource preloading ya Lighthouse configuration/report files.

## 6. Existing Tests

- `tests/test_admin_panel.py`: Admin authentication, CSRF, hero/product/offer/order behavior, migrations, lockout aur dashboard API.
- `tests/test_live_product_viewers.py`: Socket.IO viewer join/leave/disconnect behavior.
- `tests/test_product_analytics.py`: Product aur category analytics aggregation.
- `tests/test_seo.py`: SEO metadata, JSON-LD, robots, sitemap, llms, slug URLs aur 404 page.
- Dedicated frontend/browser responsiveness tests, Lighthouse CI, payment tests, customer authentication tests ya API contract tests codebase mein nahi mile.
