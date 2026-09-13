# Project Rules — General Purpose Flask Structure

This document explains the folder structure of this Flask project and the rules to follow when adding new features. Follow these rules so the project stays clean and easy to manage as it grows.

---

## 1. Folder Structure Overview

```
myapp/
│
├── app/
│   ├── __init__.py
│   ├── config.py
│   │
│   ├── models/
│   │   ├── __init__.py
│   │   ├── home_models.py
│   │   ├── auth_models.py
│   │   └── ... (one file per page/feature)
│   │
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── home_routes.py
│   │   ├── auth_routes.py
│   │   └── ... (one file per page/feature)
│   │
│   ├── templates/
│   │   ├── base.html
│   │   ├── home/
│   │   ├── auth/
│   │   └── ... (one folder per page/feature)
│   │
│   ├── static/
│   │   ├── css/
│   │   ├── js/
│   │   └── images/
│   │
│   ├── forms/
│   │   ├── __init__.py
│   │   └── ... (one file per feature that needs a form)
│   │
│   └── utils/
│       ├── __init__.py
│       └── helpers.py
│
├── tests/
│   ├── __init__.py
│   └── ... (one file per page/feature)
│
├── migrations/
│
├── .env
├── .gitignore
├── requirements.txt
├── run.py
└── README.md
```

---

## 2. Core Rule: One Feature = One Set of Files

Every page or feature (example: home, cart, product, auth, blog, contact, dashboard) must have:

- **One model file** in `app/models/` named `featurename_models.py`
- **One route file** in `app/routes/` named `featurename_routes.py`
- **One template folder** in `app/templates/` named `featurename/`
- **One test file** in `tests/` named `test_featurename.py`

Do not mix models or routes of different pages in the same file. Keep them separate so it is easy to find and edit code later.

---

## 3. Naming Rules

- File names: always lowercase, use underscore `_` between words. Example: `product_routes.py`, not `ProductRoutes.py`
- Class names (models): PascalCase. Example: `class Product`, `class CartItem`
- Function names: lowercase with underscore. Example: `def get_all_products():`
- Blueprint variable names: `featurename_bp`. Example: `home_bp`, `auth_bp`
- Template folder names: same as feature name, lowercase. Example: `templates/product/`

---

## 4. Models Rules

- Each model file should only contain models related to that one feature.
- Always import `db` from the app package: `from app import db`
- Every model must have a primary key `id`.
- Use clear column names, not short forms. Example: `email`, not `em`.
- Add relationships (ForeignKey) only when needed, and keep them documented with a comment.

---

## 5. Routes Rules

- Each route file must define its own Blueprint.
- Use `url_prefix` for grouping routes under a feature. Example: `url_prefix='/cart'`
- Import only the models needed for that route file, nothing extra.
- Keep business logic short inside routes. If logic is long, move it to `app/utils/helpers.py` or a separate service file.
- Every new route file must be registered inside `app/__init__.py` using `app.register_blueprint()`.

---

## 6. Templates Rules

- Every feature gets its own subfolder inside `templates/`.
- All pages must extend the shared `base.html` file for consistent layout.
- Keep HTML clean, use Jinja2 blocks properly (`{% block content %}`).
- Do not put inline CSS or JS inside templates; use files inside `static/`.

---

## 7. Forms Rules

- If a feature needs user input (login form, contact form, search form), create a form file inside `app/forms/`.
- Use Flask-WTF for form handling.
- Name the form file after the feature: `contact_forms.py`, `auth_forms.py`.

---

## 8. Config and Environment Rules

- Never hardcode secret keys, passwords, or database URLs in code.
- All sensitive values go in `.env` file.
- `.env` file must always be listed in `.gitignore` so it is never uploaded to GitHub.
- Use `app/config.py` to load these values using `os.environ.get()`.

---

## 9. Database Rules

- Use Flask-Migrate for any database changes. Never edit the database directly.
- Run `flask db migrate` and `flask db upgrade` after changing any model.
- Keep model changes small and one at a time, so migrations stay easy to track.

---

## 10. Testing Rules

- Every feature must have at least one test file.
- Test files go in the `tests/` folder, named `test_featurename.py`.
- Test both success cases and failure cases (example: valid login and invalid login).

---

## 11. General Coding Rules

- Keep functions short. If a function is doing too many things, split it.
- Add comments only where the code is not self explanatory.
- Do not repeat the same code in multiple files. If code repeats, move it to `app/utils/helpers.py`.
- Always use Blueprints. Never write routes directly in `app/__init__.py`.
- Follow PEP8 style for Python code (proper spacing, indentation, naming).

---

## 12. Adding a New Feature — Step by Step

When adding a new feature (example: "blog"), follow these steps in order:

1. Create `app/models/blog_models.py` and define the model(s).
2. Create `app/routes/blog_routes.py` and define the Blueprint and routes.
3. Create `app/templates/blog/` folder and add the needed HTML files.
4. If the feature needs a form, create `app/forms/blog_forms.py`.
5. Register the new Blueprint inside `app/__init__.py`.
6. Create `tests/test_blog.py` and write basic tests.
7. Run migrations if new database tables were added.

---

## 13. Security Rules (General)

- Always hash passwords before saving to database (use `werkzeug.security` or `bcrypt`). Never store plain text passwords.
- Validate all form inputs before saving to database, both on frontend and backend.
- Never trust data coming from the user without checking it.
- Sanitize any user input that will be shown back on a page, to avoid XSS (cross site scripting).
- Use SQLAlchemy ORM query methods instead of raw SQL, to avoid SQL injection.
- Never put secret keys, API keys, or passwords directly in code. Always use `.env`.
- Set proper file upload limits and only allow specific file types if the project accepts uploads.

---

## 14. CSRF Protection Rules

CSRF (Cross Site Request Forgery) protection stops other websites from submitting forms to your app without permission.

- Use `Flask-WTF` for all forms, it adds CSRF protection automatically.
- Every form template must include `{{ form.hidden_tag() }}` or `{{ form.csrf_token }}` inside the `<form>` tag.
- For AJAX/JSON requests (fetch, axios), send the CSRF token in request headers. Get the token from a meta tag in `base.html`:
  ```html
  <meta name="csrf-token" content="{{ csrf_token() }}">
  ```
- Set `WTF_CSRF_ENABLED = True` in `config.py` for all environments (never disable it in production).
- Set a CSRF token expiry time using `WTF_CSRF_TIME_LIMIT` in `config.py`.
- Never disable CSRF checks on a route unless it is a public API endpoint that uses a different protection method (like API tokens).

---

## 15. CORS Rules

CORS (Cross Origin Resource Sharing) controls which outside domains are allowed to call your app's API.

- Use `Flask-CORS` package to manage CORS, do not write manual CORS headers.
- Never use `CORS(app, resources={r"/*": {"origins": "*"}})` in production. This allows any website to call your API.
- Always list the exact allowed domains in production. Example:
  ```python
  CORS(app, resources={r"/api/*": {"origins": ["https://yourdomain.com"]}})
  ```
- Keep allowed origins in `.env` so they can be changed per environment (development, staging, production) without changing code.
- Only enable CORS on routes that actually need it (usually `/api/` routes), not the whole app.
- Do not allow credentials (`supports_credentials=True`) together with wildcard `*` origins, this is a security risk.

---

## 16. Brute Force Protection Rules

Brute force protection stops attackers from guessing passwords or spamming forms by trying many times quickly.

- Use `Flask-Limiter` to add rate limiting on sensitive routes (login, signup, password reset, OTP, contact form).
- Example limits to apply as a starting point:
  - Login route: max 5 attempts per minute per IP address.
  - Signup route: max 5 attempts per hour per IP address.
  - Password reset route: max 3 attempts per hour per IP address.
  - Contact form / OTP routes: max 5 attempts per hour per IP address.
- After repeated failed login attempts, lock the account temporarily (example: lock for 15 minutes after 5 wrong tries) and show a clear message to the user.
- Always show a generic error message on login failure, example: "Invalid email or password". Never say which one was wrong, this stops attackers from knowing if an email exists in the system.
- Log failed login attempts (email/IP/timestamp) so suspicious activity can be reviewed later.
- Add a CAPTCHA (example: Google reCAPTCHA) on login, signup, and contact forms if the project is public facing.
- Use strong password rules: minimum length, mix of letters and numbers, no common passwords.

---

## 17. Session and Cookie Security Rules

- Set `SESSION_COOKIE_SECURE = True` in production, so cookies only travel over HTTPS.
- Set `SESSION_COOKIE_HTTPONLY = True`, so JavaScript cannot read the session cookie (helps against XSS).
- Set `SESSION_COOKIE_SAMESITE = 'Lax'` or `'Strict'`, this helps prevent CSRF through cookies.
- Set a reasonable session expiry time (`PERMANENT_SESSION_LIFETIME`), do not keep sessions alive forever.
- Regenerate the session ID after login, to prevent session fixation attacks.

---

## 18. HTTP Security Headers Rules

- Use `Flask-Talisman` package to easily add standard security headers.
- Force HTTPS in production (`force_https=True` in Talisman, or handle at the server/proxy level).
- Set `Content-Security-Policy` header to control which scripts and resources can load on the page.
- Set `X-Frame-Options: DENY` or `SAMEORIGIN` to stop the site from being loaded inside an iframe (clickjacking protection).
- Set `X-Content-Type-Options: nosniff` to stop browsers from guessing file types.
- Set `Strict-Transport-Security` (HSTS) header so browsers always use HTTPS for the domain.

---

## 19. Production Environment Rules

- Turn off `debug=True` before deploying to production. Debug mode must never run in production, it can leak code and secrets.
- Use a proper production server like `Gunicorn` or `uWSGI`, never use Flask's built in development server in production.
- Use a reverse proxy like `Nginx` in front of the app server for handling HTTPS, static files, and load balancing.
- Keep `requirements.txt` updated with exact package versions (use `pip freeze > requirements.txt`).
- Use different `.env` files for development, staging, and production. Never mix their values.
- Set `FLASK_ENV=production` and `FLASK_DEBUG=0` in production environment variables.
- Never commit `.env`, database files, or any secret files to GitHub. Confirm `.gitignore` covers them.
- Set up proper logging (`logging` module) in production to track errors, do not rely on `print()` statements.
- Set up error pages for common errors (404, 500) instead of showing default Flask error pages.
- Keep database backups on a regular schedule in production.
- Use a Web Application Firewall (WAF) if the hosting provider offers one, for extra protection against common attacks.
- Monitor the app in production using a tool like Sentry, to catch errors as they happen.
- Regularly update all packages in `requirements.txt` to patch known security issues.

---

## 20. SEO Rules (Search Engine Optimization)

These rules help the website rank better on Google and other search engines.

- Every page must have a unique `<title>` tag, clear and under 60 characters.
- Every page must have a unique `meta description`, under 160 characters, written naturally (not stuffed with keywords).
- Use only one `<h1>` tag per page. Use `<h2>`, `<h3>` for subheadings in proper order.
- Use clean and readable URLs. Example: `/product/red-shoes`, not `/product?id=123`.
- Add `alt` text to every image, describing what the image shows.
- Add a `sitemap.xml` file and keep it updated when new pages are added.
- Add a `robots.txt` file to control which pages search engines can crawl.
- Use canonical tags (`<link rel="canonical">`) on pages that have duplicate or similar content.
- Make sure the website loads fast. Compress images, minify CSS/JS, use caching.
- Make sure the website is mobile friendly (responsive design), Google ranks mobile friendly sites higher.
- Use HTTPS everywhere, Google ranks secure sites higher.
- Add Open Graph tags (`og:title`, `og:description`, `og:image`) so links look good when shared on social media.
- Use internal linking between related pages (example: product page linking to related products).
- Keep page load errors (404s) to a minimum, and set up a proper custom 404 page.
- Add structured data (Schema.org / JSON-LD) for things like products, articles, reviews, FAQs, so Google can show rich results.

---

## 21. GEO Rules (Generative Engine Optimization)

GEO means optimizing content so AI tools like ChatGPT, Google AI Overview, Perplexity, and Claude can understand, quote, and recommend the website correctly.

- Write content in clear, direct language. Answer the main question in the first two or three sentences of a page or section.
- Use a question and answer format where possible (example: FAQ sections), AI engines pick up Q&A content easily.
- Break content into clear sections with descriptive headings, so AI tools can find the exact part that answers a question.
- Keep facts, numbers, and claims accurate and up to date. AI engines prefer content they can trust and quote directly.
- Add an About page and Author information, AI engines give more trust to content with clear source and authorship.
- Use structured data (Schema.org / JSON-LD) heavily, this is one of the main ways AI engines understand page content.
- Avoid keyword stuffing. AI engines read for meaning, not repeated keywords like old SEO tricks.
- Keep important information in plain HTML text, not only inside images or JavaScript heavy components, so AI crawlers can read it.
- Add a clear summary or key takeaway box at the top of long articles or guides.
- Make sure the site has a clean `llms.txt` file (if supported) describing what the site is about, similar purpose to `robots.txt` but for AI tools.
- List sources and references where relevant, AI engines are more likely to cite pages that show credible references.
- Keep content fresh, update old pages regularly, AI engines and search engines both prefer recently updated content.

---

## 22. Error Handling and Logging Rules

- Use `try/except` blocks around code that can fail (database calls, file operations, API calls), do not let the app crash with no message.
- Create centralized error handlers in `app/__init__.py` for common HTTP errors: 400, 401, 403, 404, 500.
- Log every error with enough detail (timestamp, route, error message) using Python's `logging` module, not `print()`.
- Set up log file rotation (`RotatingFileHandler`) so log files do not grow forever and fill up disk space.
- Never show raw error messages or stack traces to the user in production, show a friendly error page instead.
- Separate log levels properly: `DEBUG` for development details, `INFO` for normal events, `WARNING` for unusual events, `ERROR` for failures, `CRITICAL` for major failures.

---

## 23. Database Performance Rules

- Add indexes on columns that are searched or filtered often (example: `email`, `username`, foreign keys).
- Avoid N+1 query problems, use `joinedload` or `selectinload` in SQLAlchemy when loading related data.
- Do not fetch all rows with `Model.query.all()` on large tables, use pagination instead.
- Use database connection pooling in production, do not open a new connection for every request.
- Write only the columns you need in a query, avoid `SELECT *` style queries when only a few fields are needed.
- Run `EXPLAIN` on slow queries during development to check if indexes are being used properly.

---

## 24. API Rate Limiting and Versioning Rules

- Version every API from the start, use a prefix like `/api/v1/`, so future changes do not break old clients.
- Keep API response format consistent across all endpoints, example:
  ```json
  {
    "success": true,
    "data": {},
    "message": ""
  }
  ```
- Apply rate limiting on all public API endpoints, not just login (use `Flask-Limiter`).
- Return proper HTTP status codes: `200` success, `201` created, `400` bad request, `401` unauthorized, `404` not found, `429` too many requests, `500` server error.
- Document breaking changes clearly and keep old API versions running for a while before removing them.

---

## 25. Input Validation Rules

- Validate all incoming data (forms and API requests) using a schema library like `Marshmallow` or `Pydantic`, do not rely only on manual checks.
- Check data type, length, and format before saving to database (example: email format, phone number format).
- Reject unexpected extra fields in API requests instead of silently ignoring them.
- Always validate on the backend even if frontend validation already exists, frontend checks can be bypassed.

---

## 26. File Upload Security Rules

- Always check file extension and MIME type before accepting an upload, do not trust the file name alone.
- Set a maximum file size limit (`MAX_CONTENT_LENGTH` in Flask config) to stop large file abuse.
- Rename uploaded files to a random or unique name, do not keep the original file name (avoids overwriting and path attacks).
- Store uploaded files outside the main app code folder, or use cloud storage (example: S3) for production.
- Never allow uploaded files to run as scripts, keep upload folder permissions read only where possible.
- Scan uploaded files for viruses/malware if the project accepts public uploads at scale.

---

## 27. Environment and Dependency Management Rules

- Always use a virtual environment (`venv`) per project, never install packages globally.
- Keep two requirement files: `requirements.txt` for production packages, `requirements-dev.txt` for development only tools (testing, linting).
- Pin exact package versions in `requirements.txt` (example: `Flask==3.0.0`), do not leave versions unpinned.
- Regularly check for outdated or vulnerable packages using `pip list --outdated` or a tool like `pip-audit`.

---

## 28. Caching Rules

- Use `Flask-Caching` with Redis (or simple in-memory cache for small apps) to cache data that does not change often.
- Cache expensive database queries or API calls, not data that changes every request.
- Set a proper cache expiry time (`timeout`) for every cached item, do not cache forever without a plan to refresh it.
- Clear or update the cache automatically when the related data changes (example: clear product cache when a product is updated).

---

## 29. Background Jobs Rules

- Use `Celery` or `RQ` (Redis Queue) for tasks that take time: sending emails, sending notifications, processing images, generating reports.
- Never run slow tasks directly inside a route, this blocks the request and makes the app feel slow.
- Set up retry logic for background jobs that fail (example: retry sending an email up to 3 times).
- Monitor background job queues so failed or stuck jobs can be noticed and fixed.

---

## 30. API Documentation Rules

- Document all API endpoints using `Swagger` / `OpenAPI` (example: `Flask-Smorest` or `Flasgger`).
- Keep documentation updated whenever an endpoint changes, outdated docs are worse than no docs.
- Include example requests and responses for every endpoint in the documentation.
- Document required authentication for each endpoint clearly (public, login required, admin only).

---

## 31. Accessibility (A11y) Rules

- Use proper HTML tags (`<button>`, `<nav>`, `<label>`) instead of only `<div>` and `<span>` for everything.
- Add `alt` text to all images (this also helps SEO, see Section 20).
- Make sure all forms have proper `<label>` tags connected to their input fields.
- Make sure the site can be navigated using keyboard only (Tab key), not just mouse.
- Keep good color contrast between text and background, so text is readable for people with low vision.
- Add `aria-label` attributes where an icon or button does not have visible text.

---

## 32. Code Review and Git Workflow Rules

- Use clear branch names: `feature/cart-page`, `fix/login-bug`, `hotfix/payment-error`.
- Write clear commit messages that explain what changed and why, example: `fix: correct total price calculation in cart`.
- Never commit directly to the `main`/`master` branch, always use a separate branch and merge through a Pull Request.
- Review code before merging, check for security issues, unused code, and rule violations from this document.
- Keep commits small and focused on one change, do not mix unrelated changes in one commit.
- Add a `.gitignore` check before every commit to make sure no secrets or unnecessary files are being added.

---

## 33. Monitoring and Health Check Rules

- Add a `/health` route that returns a simple `200 OK` response, used by uptime monitoring tools and load balancers.
- Use an uptime monitoring service (example: UptimeRobot, Better Uptime) to get alerts if the site goes down.
- Use an error tracking tool (example: Sentry) to catch and report errors in real time, not just from logs.
- Track basic app metrics in production: response time, error rate, request count, so problems can be caught early.

---

## 34. Internationalization (i18n) Rules

- Use `Flask-Babel` for supporting multiple languages (example: English and Urdu) instead of hardcoding text in templates.
- Keep all user facing text in translation files, not directly written in HTML or Python code.
- Support right to left (RTL) layout properly if Urdu or Arabic text is shown, check that the design does not break.
- Let the user choose their preferred language, and remember that choice using session or user settings.
- Format dates, numbers, and currency according to the selected language/region, not hardcoded to one format.

---

## 35. Payment Security Rules

- Never store raw credit card numbers, CVV, or full card details in your own database.
- Use a trusted payment gateway (example: Stripe, PayPal, JazzCash, Easypaisa) and let them handle sensitive card data.
- Use the payment gateway's official SDK/API, do not build custom card handling logic.
- Always verify payment status using a server side webhook from the payment gateway, never trust only the frontend confirmation.
- Log all payment events (success, failure, refund) for records, but never log full card numbers or sensitive details.
- Keep payment related code isolated in its own file/module, do not mix it with unrelated business logic.
- Follow basic PCI DSS awareness: use HTTPS everywhere, restrict access to payment logs, and keep payment gateway keys in `.env`.

---

## 36. Recommended Security Packages

Add these to `requirements.txt` when building any production ready Flask app:

```
Flask-WTF        # CSRF protection and forms
Flask-CORS       # CORS control
Flask-Limiter    # Rate limiting / brute force protection
Flask-Talisman   # Security headers, force HTTPS
Flask-Login      # Session and login management
bcrypt           # Password hashing
python-dotenv    # Load .env files
gunicorn         # Production server
Flask-Caching    # Caching support
Flask-Babel      # Internationalization (i18n)
Flask-Migrate    # Database migrations
Marshmallow      # Input validation and serialization
Celery           # Background jobs
redis            # Caching and job queue backend
Flasgger         # API documentation (Swagger/OpenAPI)
sentry-sdk       # Error tracking and monitoring
```

---

*This file should be kept updated whenever the project structure or rules change. Any new developer joining the project should read this file first.*