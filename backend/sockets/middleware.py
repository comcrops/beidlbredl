import os
import logging

import users
from auth import decode_token

log = logging.getLogger(__name__)

_sessions: dict[str, dict] = {}


def authenticate_socket(auth: dict, sid: str) -> dict | None:
    """Returns session dict if auth valid, None to reject the connection."""
    kiosk_secret = os.environ.get('KIOSK_SECRET', '')
    if kiosk_secret and auth.get('kiosk_secret') == kiosk_secret:
        session = {'is_kiosk': True, 'username': 'Kiosk'}
        _sessions[sid] = session
        return session

    token = auth.get('token', '')
    if not token:
        log.warning('Socket rejected: no auth (sid=%s)', sid)
        return None

    try:
        claims = decode_token(token)
    except Exception as e:
        log.warning('Socket rejected: bad token: %s (sid=%s)', e, sid)
        return None

    sub = claims.get('sub')
    user = users.get_user(sub)
    if not user:
        log.warning('Socket rejected: unknown user sub=%s (sid=%s)', sub, sid)
        return None

    session = {'is_kiosk': False, 'user_sub': sub, 'username': user['username']}
    _sessions[sid] = session
    log.info('Socket authenticated: %s (sid=%s)', user['username'], sid)
    return session


def get_session(sid: str) -> dict | None:
    return _sessions.get(sid)


def clear_session(sid: str) -> None:
    _sessions.pop(sid, None)
