from contextlib import closing

from app.models.shared import DB_TYPE, get_connection


def get_site_setting(key, default=None):
    with closing(get_connection()) as conn:
        row = conn.execute('SELECT value FROM settings WHERE key = ?', (key,)).fetchone()
    if row is None or row['value'] is None:
        return default
    return row['value']


def set_site_setting(key, value):
    with closing(get_connection()) as conn:
        if DB_TYPE == 'mysql':
            conn.execute(
                'INSERT INTO settings (`key`, `value`) VALUES (?, ?) ON DUPLICATE KEY UPDATE `value` = VALUES(`value`)',
                (key, str(value))
            )
        else:
            conn.execute(
                'INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value',
                (key, str(value))
            )
        conn.commit()


__all__ = ['get_site_setting', 'set_site_setting']

