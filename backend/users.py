import os
import logging
import requests as http

import pocketbase

log = logging.getLogger(__name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
_COLLECTION = 'users'
_FIELDS = [
    {'name': 'authentik_sub', 'type': 'text', 'required': True},
    {'name': 'username', 'type': 'text', 'required': True},
]


def _ensure():
    pocketbase.ensure_collection(_COLLECTION, _FIELDS)


def get_user(sub: str) -> dict | None:
    _ensure()
    try:
        resp = http.get(
            f'{PB_URL}/api/collections/{_COLLECTION}/records',
            params={'filter': f'authentik_sub="{sub}"', 'perPage': 1, 'skipTotal': 1},
            timeout=5,
        )
        if resp.ok:
            items = resp.json().get('items', [])
            return items[0] if items else None
        log.warning('get_user failed: %s %s', resp.status_code, resp.text)
    except Exception as e:
        log.error('get_user exception: %s', e)
    return None


def create_user(sub: str, username: str) -> dict:
    _ensure()
    resp = http.post(
        f'{PB_URL}/api/collections/{_COLLECTION}/records',
        json={'authentik_sub': sub, 'username': username},
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
