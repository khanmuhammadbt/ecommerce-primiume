import logging
from datetime import datetime, timedelta, timezone
from math import ceil

from flask import Blueprint, current_app, flash, redirect, render_template, request, session, url_for

from app.models.admin import (
    clear_login_attempt_state,
    get_login_attempt_state,
    save_login_attempt_state,
    verify_admin_login,
)

admin_login_bp = Blueprint('admin_login_bp', __name__)
SECURITY_LOGGER = logging.getLogger('banta_bazar.security')


def _get_login_key(username):
    forwarded_for = (request.headers.get('X-Forwarded-For') or '').split(',')[0].strip()
    client_ip = forwarded_for or request.remote_addr or 'unknown'
    return f'{username}:{client_ip}'


def _get_remaining_lockout_minutes(lock_until):
    if not lock_until:
        return 0
    remaining_seconds = max(0, int((lock_until - datetime.now(timezone.utc)).total_seconds()))
    return max(1, ceil(remaining_seconds / 60))


@admin_login_bp.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = (request.form.get('username') or '').strip()
        password = (request.form.get('password') or '').strip()
        login_key = _get_login_key(username)
        max_attempts = int(current_app.config.get('LOGIN_MAX_ATTEMPTS', 5))
        lockout_minutes = int(current_app.config.get('LOGIN_LOCKOUT_MINUTES', 15))

        attempt_state = get_login_attempt_state(login_key)
        locked_until = attempt_state.get('locked_until')
        if locked_until and datetime.now(timezone.utc) < datetime.fromisoformat(locked_until):
            remaining_minutes = _get_remaining_lockout_minutes(datetime.fromisoformat(locked_until))
            flash(f'Too many failed attempts. Please try again in {remaining_minutes} minute{"s" if remaining_minutes != 1 else ""}.', 'error')
            SECURITY_LOGGER.warning('Blocked admin login attempt for %s from %s due to lockout.', username, login_key)
            return render_template('admin_login.html', title='Admin Login')

        if verify_admin_login(username, password):
            clear_login_attempt_state(login_key)
            session['is_admin'] = True
            return redirect(url_for('admin_dashboard_bp.admin_dashboard'))

        next_failures = int(attempt_state.get('failures', 0)) + 1
        if next_failures >= max_attempts:
            lockout_expiry = datetime.now(timezone.utc) + timedelta(minutes=lockout_minutes)
            remaining_minutes = _get_remaining_lockout_minutes(lockout_expiry)
            save_login_attempt_state(login_key, next_failures, lockout_expiry.isoformat())
            flash(f'Too many failed attempts. Please try again in {remaining_minutes} minute{"s" if remaining_minutes != 1 else ""}.', 'error')
        else:
            save_login_attempt_state(login_key, next_failures, None)
            flash('Invalid username or password.', 'error')

        SECURITY_LOGGER.warning('Failed admin login attempt for %s from %s (attempt %s).', username, login_key, next_failures)
        return render_template('admin_login.html', title='Admin Login')
    return render_template('admin_login.html', title='Admin Login')


@admin_login_bp.route('/admin/logout')
def admin_logout():
    session.pop('is_admin', None)
    flash('You have been logged out.', 'success')
    return redirect(url_for('admin_login_bp.admin_login'))

