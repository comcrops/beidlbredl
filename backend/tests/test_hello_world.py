import pytest
from app import create_app
from extensions import socketio
from apps.hello_world.routes import _state


@pytest.fixture(autouse=True)
def reset_hello_world_state():
    _state['message'] = 'Servus Welt!'
    yield
    _state['message'] = 'Servus Welt!'


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')


def test_update_message_broadcasts(socket_client):
    socket_client.emit('hello_world:update_message', {'message': 'Oida!'}, namespace='/apps')
    received = socket_client.get_received('/apps')
    assert any(e['name'] == 'hello_world:message_updated' for e in received)
    event = next(e for e in received if e['name'] == 'hello_world:message_updated')
    assert event['args'][0]['message'] == 'Oida!'


def test_update_message_persists_in_state(socket_client):
    socket_client.emit('hello_world:update_message', {'message': 'Hawedere!'}, namespace='/apps')
    assert _state['message'] == 'Hawedere!'


def test_empty_message_ignored(socket_client):
    socket_client.emit('hello_world:update_message', {'message': '   '}, namespace='/apps')
    assert _state['message'] == 'Servus Welt!'
