from __future__ import annotations

import time
from typing import Any

from flask import request
from flask_socketio import emit, join_room, leave_room

product_viewers: dict[str, set[str]] = {}
socket_to_product: dict[str, str] = {}
product_broadcast_queue: dict[str, float] = {}


def _normalize_product_id(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, dict):
        value = value.get('product_id')
    if value is None:
        return None
    value = str(value).strip()
    if not value:
        return None
    return value


def _room_name(product_id: str) -> str:
    return f'product_{product_id}'


def _broadcast_viewer_count(socketio, product_id: str) -> None:
    now = time.monotonic()
    last = product_broadcast_queue.get(product_id)
    if last is not None and (now - last) < 1:
        return

    product_broadcast_queue[product_id] = now
    count = len(product_viewers.get(product_id, set()))
    emit(
        'viewer_count',
        {'product_id': str(product_id), 'count': count},
        room=_room_name(product_id),
        include_self=True,
    )


def _leave_product(socketio, product_id: str, sid: str) -> None:
    product_id = _normalize_product_id(product_id)
    if not product_id:
        return

    viewers = product_viewers.get(product_id, set())
    if sid in viewers:
        viewers.discard(sid)

    if not viewers:
        product_viewers.pop(product_id, None)
    else:
        product_viewers[product_id] = viewers

    socket_to_product.pop(sid, None)
    leave_room(_room_name(product_id), sid)
    _broadcast_viewer_count(socketio, product_id)


def _cleanup_stale_socket_mappings(socketio) -> None:
    while True:
        socketio.sleep(60)

        valid_sids = set()
        for namespace_map in socketio.server.manager.rooms.values():
            for room_sids in namespace_map.values():
                valid_sids.update(room_sids)

        for sid in list(socket_to_product.keys()):
            if sid not in valid_sids:
                product_id = socket_to_product.pop(sid)
                viewers = product_viewers.get(product_id, set())
                viewers.discard(sid)
                if not viewers:
                    product_viewers.pop(product_id, None)
                else:
                    product_viewers[product_id] = viewers

                if product_id in product_viewers:
                    _broadcast_viewer_count(socketio, product_id)


def register_live_product_viewers(socketio) -> None:
    @socketio.on('join_product')
    def handle_join_product(data=None):
        product_id = _normalize_product_id(data)
        if product_id is None:
            return

        sid = request.sid
        previous_product_id = socket_to_product.get(sid)
        if previous_product_id and previous_product_id != product_id:
            _leave_product(socketio, previous_product_id, sid)

        room_name = _room_name(product_id)
        join_room(room_name)
        product_viewers.setdefault(product_id, set()).add(sid)
        socket_to_product[sid] = product_id
        _broadcast_viewer_count(socketio, product_id)

    @socketio.on('leave_product')
    def handle_leave_product(data=None):
        sid = request.sid
        product_id = _normalize_product_id(data)
        if product_id is None:
            product_id = socket_to_product.get(sid)
        if product_id is None:
            return

        _leave_product(socketio, product_id, sid)

    @socketio.on('disconnect')
    def handle_disconnect():
        sid = request.sid
        product_id = socket_to_product.get(sid)
        if product_id is None:
            return

        _leave_product(socketio, product_id, sid)

    socketio.start_background_task(_cleanup_stale_socket_mappings, socketio)
