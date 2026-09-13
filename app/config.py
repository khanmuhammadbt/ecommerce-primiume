import hashlib
import os
from datetime import timedelta
from pathlib import Path

try:
    from dotenv import load_dotenv
except ImportError:  # pragma: no cover - optional dependency, fallback for local env files
    def load_dotenv():
        env_path = Path(__file__).resolve().parent.parent / '.env'
        if not env_path.exists():
            return False

        for raw_line in env_path.read_text(encoding='utf-8').splitlines():
            line = raw_line.strip()
            if not line or line.startswith('#') or '=' not in line:
                continue
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))
        return True


load_dotenv()

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PACKAGE_ROOT = Path(__file__).resolve().parent


class Config:
    fallback_secret = os.environ.get("SECRET_KEY") or os.environ.get("FLASK_SECRET_KEY")
    if not fallback_secret:
        fallback_secret = hashlib.sha256(str(PROJECT_ROOT).encode("utf-8")).hexdigest()
    SECRET_KEY = fallback_secret
    ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")

    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600
    LOGIN_MAX_ATTEMPTS = int(os.environ.get("LOGIN_MAX_ATTEMPTS") or "5")
    LOGIN_LOCKOUT_MINUTES = int(os.environ.get("LOGIN_LOCKOUT_MINUTES") or "15")

    DB_TYPE = (os.environ.get("DB_TYPE") or "SQLite").lower()
    DATABASE_PATH = os.environ.get("DATABASE_PATH") or str(PROJECT_ROOT / "shop.db")

    MYSQL_HOST = os.environ.get("MYSQL_HOST") or "localhost"
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT") or "3306")
    MYSQL_USER = os.environ.get("MYSQL_USER") or "root"
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD")
    MYSQL_DB = os.environ.get("MYSQL_DB") or "ecommerce_db"
    MYSQL_CHARSET = os.environ.get("MYSQL_CHARSET") or "utf8mb4"

    UPLOAD_FOLDER = os.environ.get("UPLOAD_FOLDER") or str(PACKAGE_ROOT / "static" / "images" / "uploads")
    PERMANENT_SESSION_LIFETIME = timedelta(days=int(os.environ.get("SESSION_LIFETIME_DAYS") or 10))
    SESSION_REFRESH_EACH_REQUEST = True


DATABASE_PATH = Config.DATABASE_PATH
SECRET_KEY = Config.SECRET_KEY
UPLOAD_FOLDER = Config.UPLOAD_FOLDER
DB_TYPE = Config.DB_TYPE
MYSQL_HOST = Config.MYSQL_HOST
MYSQL_PORT = Config.MYSQL_PORT
MYSQL_USER = Config.MYSQL_USER
MYSQL_PASSWORD = Config.MYSQL_PASSWORD
MYSQL_DB = Config.MYSQL_DB
MYSQL_CHARSET = Config.MYSQL_CHARSET
ADMIN_PASSWORD = Config.ADMIN_PASSWORD

