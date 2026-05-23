import pytest
from unittest.mock import patch, MagicMock
from extensions import socketio
import apps.hello_world.routes as hw_routes


def _pb_list(messages):
    m = MagicMock()
    m.ok = True
    m.json.return_value = {'items': [{'text': t, 'sender': ''} for t in messages]}
    return m


def _pb_ok():
    m = MagicMock()
    m.ok = True
    m.status_code = 200
    return m


@pytest.fixture(autouse=True)
def skip_pb_setup():
    with patch('pocketbase.ensure_collection'):
        yield


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps', auth={'kiosk_secret': 'test-kiosk-secret'})


def test_update_message_broadcasts_messages_list(socket_client):
    with patch('apps.hello_world.routes.requests.post', return_value=_pb_ok()), \
         patch('apps.hello_world.routes.requests.get', return_value=_pb_list(['Oida!'])):
        socket_client.emit('hello_world:update_message', {'message': 'Oida!'}, namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next((e for e in received if e['name'] == 'hello_world:messages_updated'), None)
    assert event is not None
    assert any(m['text'] == 'Oida!' for m in event['args'][0]['messages'])


def test_empty_message_ignored(socket_client):
    with patch('apps.hello_world.routes.requests.post'), \
         patch('apps.hello_world.routes.requests.get'):
        socket_client.emit('hello_world:update_message', {'message': '   '}, namespace='/apps')
        received = socket_client.get_received('/apps')
    assert not any(e['name'] == 'hello_world:messages_updated' for e in received)


def test_request_messages_returns_list(socket_client):
    with patch('apps.hello_world.routes.requests.get', return_value=_pb_list(['Hawedere!', 'Servas!'])):
        socket_client.emit('hello_world:request_messages', namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hello_world:messages_updated')
    texts = [m['text'] for m in event['args'][0]['messages']]
    assert texts == ['Hawedere!', 'Servas!']


def test_newest_message_first_in_response(socket_client):
    messages = ['Neu', 'Alt']
    with patch('apps.hello_world.routes.requests.post', return_value=_pb_ok()), \
         patch('apps.hello_world.routes.requests.get', return_value=_pb_list(messages)):
        socket_client.emit('hello_world:update_message', {'message': 'Neu'}, namespace='/apps')
        received = socket_client.get_received('/apps')
    event = next(e for e in received if e['name'] == 'hello_world:messages_updated')
    assert event['args'][0]['messages'][0]['text'] == 'Neu'
