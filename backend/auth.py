import os
import logging
from functools import wraps

import jwt
from jwt import PyJWKClient
from flask import request, g, jsonify

log = logging.getLogger(__name__)

_jwks_client: PyJWKClient | None = None


def _get_jwks_client() -> PyJWKClient:
    global _jwks_client
    if _jwks_client is None:
        url = os.environ.get('AUTHENTIK_URL', '')
        slug = os.environ.get('AUTHENTIK_APP_SLUG', '')
        _jwks_client = PyJWKClient(f'{url}/application/o/{slug}/jwks/')
    return _jwks_client


def decode_token(token: str) -> dict:
    """Validate JWT against Authentik JWKS. Raises jwt.InvalidTokenError on failure."""
    client = _get_jwks_client()
    try:
        signing_key = client.get_signing_key_from_jwt(token)
    except jwt.exceptions.PyJWKClientConnectionError as e:
        log.error('JWKS fetch failed: %s', e)
        raise jwt.InvalidTokenError('JWKS unavailable') from e

    return jwt.decode(
        token,
        signing_key.key,
        algorithms=['RS256', 'ES256'],
        audience=os.environ.get('AUTHENTIK_CLIENT_ID', ''),
    )


def require_auth(f):
    """Decorator for Flask routes: validates Bearer token, injects g.user_sub."""
    @wraps(f)
    def decorated(*args, **kwargs):
        header = request.headers.get('Authorization', '')
        if not header.startswith('Bearer '):
            return jsonify({'error': 'Missing token'}), 401
        try:
            g.user_claims = decode_token(header[7:])
            g.user_sub = g.user_claims['sub']
        except Exception as e:
            log.warning('Auth rejected: %s', e)
            return jsonify({'error': 'Invalid token'}), 401
        return f(*args, **kwargs)
    return decorated
