import pytest
from app import create_app
from extensions import socketio


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})


def test_connect_succeeds(socket_client):
    assert socket_client.is_connected('/apps')
