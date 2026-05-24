import pytest
from extensions import socketio
from apps.online_users.routes import _online, user_connected, user_disconnected


@pytest.fixture(autouse=True)
def reset():
    _online.clear()
    yield
    _online.clear()


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(
        flask_app, namespace='/apps',
        auth={'kiosk_secret': 'test-kiosk-secret'},
    )


def test_user_connected_adds_to_online(flask_app):
    with flask_app.app_context():
        user_connected('alice')
    assert 'alice' in _online


def test_user_disconnected_removes_from_online(flask_app):
    with flask_app.app_context():
        user_connected('alice')
        user_disconnected('alice')
    assert 'alice' not in _online


def test_multiple_connections_counted(flask_app):
    with flask_app.app_context():
        user_connected('alice')
        user_connected('alice')
        user_disconnected('alice')
    assert 'alice' in _online
    with flask_app.app_context():
        user_disconnected('alice')
    assert 'alice' not in _online


def test_broadcast_on_connect(socket_client):
    user_connected('bob')
    received = socket_client.get_received('/apps')
    updates = [e for e in received if e['name'] == 'online_users:updated']
    assert updates
    assert 'bob' in updates[-1]['args'][0]['users']


def test_broadcast_on_disconnect(socket_client):
    user_connected('bob')
    socket_client.get_received('/apps')  # clear
    user_disconnected('bob')
    received = socket_client.get_received('/apps')
    updates = [e for e in received if e['name'] == 'online_users:updated']
    assert updates
    assert 'bob' not in updates[-1]['args'][0]['users']
