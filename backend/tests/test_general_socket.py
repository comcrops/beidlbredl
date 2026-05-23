import pytest
from app import create_app
from extensions import socketio
from state import kiosk_state


@pytest.fixture(autouse=True)
def reset_state():
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []
    kiosk_state.locked = False
    yield
    kiosk_state.active_app_id = None
    kiosk_state.open_app_ids = []
    kiosk_state.locked = False


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/general')


def test_connect_receives_initial_state(socket_client):
    received = socket_client.get_received('/general')
    assert len(received) == 1
    assert received[0]['name'] == 'state'
    data = received[0]['args'][0]
    assert data['active_app_id'] is None
    assert data['open_app_ids'] == []
    assert data['locked'] is False


def test_open_app_updates_state(socket_client):
    socket_client.get_received('/general')  # clear connect event
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    received = socket_client.get_received('/general')
    assert any(e['name'] == 'state' for e in received)
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'
    assert 'hello-world' in state_event['args'][0]['open_app_ids']


def test_close_app_removes_from_state(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('close_app', {'app_id': 'hello-world'}, namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert 'hello-world' not in state_event['args'][0]['open_app_ids']
    assert state_event['args'][0]['active_app_id'] is None


def test_carousel_next_cycles_active_app(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('carousel_next', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'


def test_carousel_prev_cycles_active_app(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('carousel_prev', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'hello-world'


def test_toggle_lock_sets_locked_true(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['locked'] is True


def test_toggle_lock_flips_back_to_false(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['locked'] is False


def test_focus_request_sets_active_app_and_opens_it(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('focus_request', {'app_id': 'rot-app'}, namespace='/general')
    received = socket_client.get_received('/general')
    state_event = next(e for e in received if e['name'] == 'state')
    assert state_event['args'][0]['active_app_id'] == 'rot-app'
    assert 'rot-app' in state_event['args'][0]['open_app_ids']


def test_focus_request_no_op_when_locked(socket_client):
    socket_client.get_received('/general')
    socket_client.emit('open_app', {'app_id': 'hello-world'}, namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('toggle_lock', namespace='/general')
    socket_client.get_received('/general')
    socket_client.emit('focus_request', {'app_id': 'rot-app'}, namespace='/general')
    received = socket_client.get_received('/general')
    assert not any(e['name'] == 'state' for e in received)
