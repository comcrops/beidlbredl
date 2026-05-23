from flask import Blueprint
from extensions import socketio
import requests
import os
import time
import logging

log = logging.getLogger(__name__)
bp = Blueprint('hello_world', __name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
PB_COLLECTION = 'hello_world_messages'

_collection_ready = False


def _admin_token() -> str | None:
    email = os.environ.get('PB_ADMIN_EMAIL', '')
    password = os.environ.get('PB_ADMIN_PASSWORD', '')
    if not email or not password:
        return None

    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        log.warning('PocketBase superuser auth OK')
        return resp.json().get('token')

    log.warning('PocketBase superuser auth failed (%s), trying bootstrap', resp.status_code)
    # No superuser yet — bootstrap first superuser (only works when zero superusers exist)
    requests.post(
        f'{PB_URL}/api/collections/_superusers/records',
        json={'email': email, 'password': password, 'passwordConfirm': password},
        timeout=5,
    )
    resp = requests.post(
        f'{PB_URL}/api/collections/_superusers/auth-with-password',
        json={'identity': email, 'password': password},
        timeout=5,
    )
    if resp.ok:
        log.warning('PocketBase bootstrap + auth OK')
        return resp.json().get('token')
    log.error('PocketBase superuser auth failed after bootstrap: %s %s', resp.status_code, resp.text)
    return None


def _ensure_collection():
    global _collection_ready
    if _collection_ready:
        return
    for attempt in range(6):
        try:
            token = _admin_token()
            if not token:
                log.error('No PocketBase admin token — skipping collection setup')
                return
            headers = {'Authorization': f'Bearer {token}'}
            check = requests.get(
                f'{PB_URL}/api/collections/{PB_COLLECTION}',
                headers=headers,
                timeout=5,
            )
            if check.status_code == 404:
                log.warning('Collection %s not found, creating...', PB_COLLECTION)
                r = requests.post(
                    f'{PB_URL}/api/collections',
                    headers=headers,
                    timeout=5,
                    json={
                        'name': PB_COLLECTION,
                        'type': 'base',
                        'fields': [
                            {'name': 'text', 'type': 'text', 'required': True},
                            {'name': 'created', 'type': 'autodate', 'onCreate': True, 'onUpdate': False},
                        ],
                        'listRule': '',
                        'viewRule': '',
                        'createRule': '',
                        'updateRule': None,
                        'deleteRule': None,
                    },
                )
                log.warning('Collection create response: %s %s', r.status_code, r.text)
            else:
                log.warning('Collection %s check: %s', PB_COLLECTION, check.status_code)
            _collection_ready = True
            return
        except Exception as e:
            log.warning('_ensure_collection attempt %d failed: %s', attempt, e)
            if attempt < 5:
                time.sleep(3)
    log.error('_ensure_collection gave up after 6 attempts')
    _collection_ready = True


def _recent_messages(limit: int = 20) -> list[str]:
    _ensure_collection()
    try:
        resp = requests.get(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            params={'sort': '-created', 'perPage': limit, 'skipTotal': 1},
            timeout=5,
        )
        if resp.ok:
            return [item['text'] for item in resp.json().get('items', [])]
        log.warning('_recent_messages failed: %s %s', resp.status_code, resp.text)
    except Exception as e:
        log.error('_recent_messages exception: %s', e)
    return []


def _save_message(text: str):
    _ensure_collection()
    try:
        r = requests.post(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            json={'text': text},
            timeout=5,
        )
        if not r.ok:
            log.warning('_save_message failed: %s %s', r.status_code, r.text)
    except Exception as e:
        log.error('_save_message exception: %s', e)


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
