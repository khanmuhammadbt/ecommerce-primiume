from urllib.parse import urlsplit

from flask import jsonify, request, session, url_for


def is_admin():
    return session.get('is_admin', False)


def is_ajax_request():
    return request.headers.get('X-Requested-With') == 'XMLHttpRequest' or 'application/json' in request.headers.get('Accept', '')


def build_admin_redirect(section=None):
    referrer = request.referrer or ''
    if section:
        return url_for('admin_dashboard_bp.admin_dashboard', _anchor=section)

    if referrer:
        parsed_referrer = urlsplit(referrer)
        if parsed_referrer.path.startswith('/admin'):
            if parsed_referrer.fragment:
                return referrer
            return url_for('admin_dashboard_bp.admin_dashboard')

    return url_for('admin_dashboard_bp.admin_dashboard')


def send_admin_success(message, section=None):
    target_url = build_admin_redirect(section)
    if is_ajax_request():
        return jsonify(success=True, message=message, redirect=target_url)

    from flask import flash, redirect
    flash(message, 'success')
    return redirect(target_url)


__all__ = [
    'is_admin',
    'is_ajax_request',
    'build_admin_redirect',
    'send_admin_success',
]

