from flask import Blueprint
from extensions import socketio
import requests
import os
import time

bp = Blueprint('hello_world', __name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
PB_COLLECTION = 'hello_world_messages'

_collection_ready = False


def _admin_token() -> str | None:
    email = os.environ.get('PB_ADMIN_EMAIL', '')
    password = os.environ.get('PB_ADMIN_PASSWORD', '')
    if not email or not password:
        return None

    # Try authenticating with existing account
    resp = requests.post(
        f'{PB_URL}/api/admins/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        return resp.json().get('token')

    # No admin yet — bootstrap first admin account (only works when zero admins exist)
    requests.post(
        f'{PB_URL}/api/admins',
        json={'email': email, 'password': password, 'passwordConfirm': password},
        timeout=5,
    )
    resp = requests.post(
        f'{PB_URL}/api/admins/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    return resp.json().get('token') if resp.ok else None


def _ensure_collection():
    global _collection_ready
    if _collection_ready:
        return
    for attempt in range(6):
        try:
            token = _admin_token()
            if not token:
                _collection_ready = True
                return
            headers = {'Authorization': token}
            check = requests.get(
                f'{PB_URL}/api/collections/{PB_COLLECTION}',
                headers=headers,
                timeout=5,
            )
            if check.status_code == 404:
                requests.post(
                    f'{PB_URL}/api/collections',
                    headers=headers,
                    timeout=5,
                    json={
                        'name': PB_COLLECTION,
                        'type': 'base',
                        'schema': [{'name': 'text', 'type': 'text', 'required': True, 'options': {}}],
                        'listRule': '',
                        'viewRule': '',
                        'createRule': '',
                        'updateRule': None,
                        'deleteRule': None,
                    },
                )
            _collection_ready = True
            return
        except Exception:
            if attempt < 5:
                time.sleep(3)
    _collection_ready = True  # give up, try record ops anyway


def _recent_messages(limit: int = 20) -> list[str]:
    _ensure_collection()
    try:
        resp = requests.get(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            params={'sort': '-created', 'perPage': limit, 'fields': 'text'},
            timeout=5,
        )
        if resp.ok:
            return [item['text'] for item in resp.json().get('items', [])]
    except Exception:
        pass
    return []


def _save_message(text: str):
    _ensure_collection()
    try:
        requests.post(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            json={'text': text},
            timeout=5,
        )
    except Exception:
        pass


@socketio.on('hello_world:update_message', namespace='/apps')
def handle_update_message(data):
    message = data.get('message', '').strip()
    if not message:
        return
    _save_message(message)
    socketio.emit(
        'hello_world:messages_updated',
        {'messages': _recent_messages()},
        namespace='/apps',
    )


@socketio.on('hello_world:request_messages', namespace='/apps')
def handle_request_messages():
    socketio.emit(
        'hello_world:messages_updated',
        {'messages': _recent_messages()},
        namespace='/apps',
    )
