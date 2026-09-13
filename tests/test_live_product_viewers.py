from app import create_app


def test_socketio_uses_threading_backend():
    app = create_app()
    socketio = app.extensions.get('socketio')
    assert socketio is not None
    assert socketio.server.async_mode == 'threading'


def test_product_viewer_count_tracks_join_leave_disconnect():
    app = create_app()
    app.config['TESTING'] = True

    socketio = app.extensions.get('socketio')
    assert socketio is not None

    client = socketio.test_client(app, flask_test_client=app.test_client())

    client.emit('join_product', {'product_id': 42})
    received = client.get_received()
    viewer_events = [message for message in received if message.get('name') == 'viewer_count']
    assert viewer_events and viewer_events[-1]['args'][0]['count'] == 1

    client.emit('leave_product', {'product_id': 42})
    received = client.get_received()
    viewer_events = [message for message in received if message.get('name') == 'viewer_count']
    assert viewer_events and viewer_events[-1]['args'][0]['count'] == 0

    client.emit('join_product', {'product_id': 99})
    received = client.get_received()
    viewer_events = [message for message in received if message.get('name') == 'viewer_count']
    assert viewer_events and viewer_events[-1]['args'][0]['product_id'] == '99'

    client.disconnect()
    received = client.get_received()
    assert not [message for message in received if message.get('name') == 'viewer_count' and message['args'][0]['count'] > 0]
