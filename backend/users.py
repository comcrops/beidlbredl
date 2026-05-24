import os
import logging
import requests as http

import pocketbase

log = logging.getLogger(__name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
_COLLECTION = 'bb_users'
_FIELDS = [
    {'name': 'authentik_sub', 'type': 'text', 'required': True},
    {'name': 'username', 'type': 'text', 'required': True},
    {'name': 'avatar', 'type': 'file', 'required': False},
]
_AVATAR_FIELD = {'name': 'avatar', 'type': 'file', 'required': False}


def _ensure():
    pocketbase.ensure_collection(_COLLECTION, _FIELDS)
    pocketbase.ensure_field(_COLLECTION, _AVATAR_FIELD)


def avatar_url(user: dict) -> str | None:
    filename = user.get('avatar')
    if not filename:
        return None
    return f"/pb-files/{_COLLECTION}/{user['id']}/{filename}"


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


def update_avatar(sub: str, file_stream, filename: str, content_type: str) -> dict:
    _ensure()
    user = get_user(sub)
    if not user:
        raise ValueError('User not found')
    token = pocketbase.admin_token()
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    resp = http.patch(
        f'{PB_URL}/api/collections/{_COLLECTION}/records/{user["id"]}',
        files={'avatar': (filename, file_stream, content_type)},
        headers=headers,
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()


def update_user(sub: str, username: str) -> dict:
    _ensure()
    user = get_user(sub)
    if not user:
        raise ValueError('User not found')
    token = pocketbase.admin_token()
    headers = {'Authorization': f'Bearer {token}'} if token else {}
    resp = http.patch(
        f'{PB_URL}/api/collections/{_COLLECTION}/records/{user["id"]}',
        json={'username': username},
        headers=headers,
        timeout=5,
    )
    resp.raise_for_status()
    return resp.json()
