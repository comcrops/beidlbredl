import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch
from app import create_app


@pytest.fixture
def flask_app():
    return create_app({'TESTING': True, 'SECRET_KEY': 'test', 'SOCKETIO_ASYNC_MODE': 'threading'})


@pytest.fixture
def client(flask_app):
    return flask_app.test_client()


def _auth_header():
    return {'Authorization': 'Bearer validtoken'}


def test_get_me_returns_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value={'username': 'TestUser'}):
        resp = client.get('/api/users/me', headers=_auth_header())
    assert resp.status_code == 200
    assert resp.get_json() == {'username': 'TestUser', 'avatar_url': None}


def test_get_me_returns_404_for_new_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-new'}), \
         patch('users.get_user', return_value=None):
        resp = client.get('/api/users/me', headers=_auth_header())
    assert resp.status_code == 404


def test_get_me_requires_auth(client):
    resp = client.get('/api/users/me')
    assert resp.status_code == 401


def test_post_me_creates_user(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value=None), \
         patch('users.create_user', return_value={'username': 'Oida'}) as mock_create:
        resp = client.post('/api/users/me', json={'username': 'Oida'}, headers=_auth_header())
    assert resp.status_code == 201
    mock_create.assert_called_once_with('sub-123', 'Oida')


def test_post_me_rejects_short_username(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}):
        resp = client.post('/api/users/me', json={'username': 'ab'}, headers=_auth_header())
    assert resp.status_code == 400


def test_post_me_rejects_long_username(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}):
        resp = client.post('/api/users/me', json={'username': 'a' * 21}, headers=_auth_header())
    assert resp.status_code == 400


def test_post_me_conflict_if_already_exists(client):
    with patch('auth.decode_token', return_value={'sub': 'sub-123'}), \
         patch('users.get_user', return_value={'username': 'existing'}):
        resp = client.post('/api/users/me', json={'username': 'NewName'}, headers=_auth_header())
    assert resp.status_code == 409
