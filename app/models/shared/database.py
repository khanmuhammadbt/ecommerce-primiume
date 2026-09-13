import os
import re
import sqlite3
import sys
from contextlib import closing

from app.config import (
    DATABASE_PATH,
    DB_TYPE,
    MYSQL_CHARSET,
    MYSQL_DB,
    MYSQL_HOST,
    MYSQL_PASSWORD,
    MYSQL_PORT,
    MYSQL_USER,
)

try:
    import mysql.connector
    from mysql.connector.pooling import MySQLConnectionPool
except ImportError:  # pragma: no cover - optional dependency
    mysql = None
    MySQLConnectionPool = None

DB_PATH = DATABASE_PATH
PRODUCT_DB_PATH = DB_PATH
ORDERS_DB_PATH = DB_PATH
DB_TYPE = DB_TYPE

MYSQL_POOL = None
MYSQL_POOL_SIZE = int(os.environ.get('MYSQL_POOL_SIZE') or '10')
MYSQL_POOL_NAME = os.environ.get('MYSQL_POOL_NAME') or 'banta_bazar_pool'


class CompatConnection:
    def __init__(self, raw_conn, db_type):
        self._raw_conn = raw_conn
        self._db_type = db_type

    def execute(self, operation, params=()):
        if self._db_type == 'mysql':
            normalized = operation.strip().replace('INSERT OR IGNORE', 'INSERT IGNORE')
            normalized = normalized.replace('?', '%s')
            cursor = self._raw_conn.cursor(dictionary=True)
            cursor.execute(normalized, params)
            return cursor

        return self._raw_conn.execute(operation, params)

    def executemany(self, operation, seq_of_params):
        if self._db_type == 'mysql':
            normalized = operation.strip().replace('?', '%s')
            cursor = self._raw_conn.cursor(dictionary=True)
            cursor.executemany(normalized, seq_of_params)
            return cursor

        return self._raw_conn.executemany(operation, seq_of_params)

    def executescript(self, script):
        if self._db_type == 'mysql':
            statements = [statement.strip() for statement in script.split(';') if statement.strip()]
            for statement in statements:
                self.execute(statement)
            return None

        return self._raw_conn.executescript(script)

    def commit(self):
        self._raw_conn.commit()

    def rollback(self):
        self._raw_conn.rollback()

    def close(self):
        self._raw_conn.close()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        self.close()


def _resolve_runtime_db_path():
    shared_module = sys.modules.get('app.models.shared')
    if shared_module is not None:
        candidate = getattr(shared_module, 'DB_PATH', None)
        if candidate:
            return str(candidate)
    return DB_PATH


def _open_connection():
    if DB_TYPE == 'mysql':
        if mysql is None or MySQLConnectionPool is None:
            raise RuntimeError('Install mysql-connector-python to use MySQL.')

        global MYSQL_POOL
        if MYSQL_POOL is None:
            MYSQL_POOL = MySQLConnectionPool(
                pool_name=MYSQL_POOL_NAME,
                pool_size=MYSQL_POOL_SIZE,
                host=MYSQL_HOST,
                port=MYSQL_PORT,
                user=MYSQL_USER,
                password=MYSQL_PASSWORD,
                database=MYSQL_DB,
                charset=MYSQL_CHARSET,
                autocommit=False,
            )

        raw_conn = MYSQL_POOL.get_connection()
        return CompatConnection(raw_conn, 'mysql')

    db_path = _resolve_runtime_db_path()
    conn = sqlite3.connect(db_path, timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute('PRAGMA foreign_keys = ON')
    return conn


def get_connection():
    return _open_connection()


def _slugify(value):
    return re.sub(r'[^a-z0-9]+', '-', value.lower()).strip('-') or 'general'


__all__ = [
    'DB_PATH',
    'PRODUCT_DB_PATH',
    'ORDERS_DB_PATH',
    'CompatConnection',
    'get_connection',
    '_slugify',
]

