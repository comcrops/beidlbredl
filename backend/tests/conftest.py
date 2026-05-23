import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from app import create_app
from config import TestConfig


@pytest.fixture
def flask_app():
    app = create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SOCKETIO_ASYNC_MODE': 'threading'})
    yield app


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()
