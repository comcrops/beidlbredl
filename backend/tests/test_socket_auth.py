import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from unittest.mock import patch
from sockets.middleware import authenticate_socket, get_session, clear_session, _sessions


@pytest.fixture(autouse=True)
def clear_sessions():
    _sessions.clear()
    yield
    _sessions.clear()


def test_kiosk_secret_accepted():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'secret123'}):
        session = authenticate_socket({'kiosk_secret': 'secret123'}, 'sid-1')
    assert session is not None
    assert session['is_kiosk'] is True


def test_kiosk_wrong_secret_rejected():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'secret123'}):
        session = authenticate_socket({'kiosk_secret': 'wrong'}, 'sid-1')
    assert session is None


def test_valid_token_accepted():
    with patch('sockets.middleware.decode_token', return_value={'sub': 'u1'}), \
         patch('sockets.middleware.users.get_user', return_value={'username': 'Max'}):
        session = authenticate_socket({'token': 'validtoken'}, 'sid-2')
    assert session is not None
    assert session['username'] == 'Max'
    assert session['is_kiosk'] is False


def test_invalid_token_rejected():
    import jwt
    with patch('sockets.middleware.decode_token', side_effect=jwt.InvalidTokenError('bad')):
        session = authenticate_socket({'token': 'badtoken'}, 'sid-3')
    assert session is None


def test_unknown_user_rejected():
    with patch('sockets.middleware.decode_token', return_value={'sub': 'ghost'}), \
         patch('sockets.middleware.users.get_user', return_value=None):
        session = authenticate_socket({'token': 'tok'}, 'sid-4')
    assert session is None


def test_no_auth_rejected():
    session = authenticate_socket({}, 'sid-5')
    assert session is None


def test_session_stored_on_auth():
    with patch.dict(os.environ, {'KIOSK_SECRET': 'sec'}):
        authenticate_socket({'kiosk_secret': 'sec'}, 'sid-6')
    assert get_session('sid-6') is not None


def test_session_cleared():
    _sessions['sid-7'] = {'is_kiosk': True}
    clear_session('sid-7')
    assert get_session('sid-7') is None
