import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
import jwt
from unittest.mock import patch, MagicMock
from flask import Flask, g
import auth


@pytest.fixture
def app():
    a = Flask(__name__)
    a.config['TESTING'] = True
    return a


def _make_signing_key():
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.hazmat.backends import default_backend
    private_key = rsa.generate_private_key(
        public_exponent=65537, key_size=2048, backend=default_backend()
    )
    return private_key


def _make_token(private_key, sub='user-123', audience='test-client', expired=False):
    import datetime
    now = datetime.datetime.utcnow()
    exp = now - datetime.timedelta(hours=1) if expired else now + datetime.timedelta(hours=1)
    return jwt.encode(
        {'sub': sub, 'aud': audience, 'iat': now, 'exp': exp},
        private_key,
        algorithm='RS256',
    )


def test_decode_token_valid():
    private_key = _make_signing_key()
    token = _make_token(private_key, audience='my-client')
    mock_key = MagicMock()
    mock_key.key = private_key.public_key()
    with patch.dict(os.environ, {'AUTHENTIK_CLIENT_ID': 'my-client'}), \
         patch('auth._get_jwks_client') as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        auth._jwks_client = None
        claims = auth.decode_token(token)
    assert claims['sub'] == 'user-123'


def test_decode_token_expired():
    private_key = _make_signing_key()
    token = _make_token(private_key, expired=True, audience='my-client')
    mock_key = MagicMock()
    mock_key.key = private_key.public_key()
    with patch.dict(os.environ, {'AUTHENTIK_CLIENT_ID': 'my-client'}), \
         patch('auth._get_jwks_client') as mock_client_fn:
        mock_client = MagicMock()
        mock_client.get_signing_key_from_jwt.return_value = mock_key
        mock_client_fn.return_value = mock_client
        auth._jwks_client = None
        with pytest.raises(jwt.ExpiredSignatureError):
            auth.decode_token(token)


def test_require_auth_missing_header(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return 'ok'
    with app.test_client() as c:
        resp = c.get('/test')
    assert resp.status_code == 401


def test_require_auth_invalid_token(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return 'ok'
    with patch('auth.decode_token', side_effect=jwt.InvalidTokenError('bad')):
        with app.test_client() as c:
            resp = c.get('/test', headers={'Authorization': 'Bearer badtoken'})
    assert resp.status_code == 401


def test_require_auth_valid_token(app):
    @app.route('/test')
    @auth.require_auth
    def view():
        return g.user_sub
    with patch('auth.decode_token', return_value={'sub': 'user-abc'}):
        with app.test_client() as c:
            resp = c.get('/test', headers={'Authorization': 'Bearer validtoken'})
    assert resp.status_code == 200
    assert resp.data == b'user-abc'
