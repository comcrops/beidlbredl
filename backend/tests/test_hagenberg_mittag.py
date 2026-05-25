import pytest
from extensions import socketio


@pytest.fixture
def client_a(flask_app):
    client = socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})
    yield client
    client.disconnect('/apps')


@pytest.fixture
def client_b(flask_app):
    client = socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})
    yield client
    client.disconnect('/apps')


def test_focus_is_broadcast_to_all_clients(client_a, client_b):
    client_a.emit('hagenberg_mittag:focus', {'id': 'caravento'}, namespace='/apps')
    received = client_b.get_received('/apps')
    focus_events = [e for e in received if e['name'] == 'hagenberg_mittag:focus']
    assert len(focus_events) == 1
    assert focus_events[0]['args'][0]['id'] == 'caravento'


def test_set_week_mode_is_broadcast_to_all_clients(client_a, client_b):
    client_a.emit('hagenberg_mittag:set_week_mode', {'week': True}, namespace='/apps')
    received = client_b.get_received('/apps')
    events = [e for e in received if e['name'] == 'hagenberg_mittag:set_week_mode']
    assert len(events) == 1
    assert events[0]['args'][0]['week'] is True


def test_focus_payload_preserved(client_a, client_b):
    client_a.emit('hagenberg_mittag:focus', {'id': 'schlossrestaurant'}, namespace='/apps')
    received = client_b.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hagenberg_mittag:focus')
    assert event['args'][0]['id'] == 'schlossrestaurant'
