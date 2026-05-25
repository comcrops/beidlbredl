import pytest
from extensions import socketio
from apps.hagenberg_mittag.routes import _state


@pytest.fixture(autouse=True)
def reset():
    _state.clear()
    yield
    _state.clear()


@pytest.fixture
def socket_client(flask_app):
    return socketio.test_client(flask_app, namespace='/apps')


def test_app_registered(flask_app):
    from apps import APP_REGISTRY
    app_ids = [a['id'] for a in APP_REGISTRY]
    assert 'hagenberg-mittag' in app_ids
