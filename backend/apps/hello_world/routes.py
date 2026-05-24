from flask import Blueprint
from extensions import socketio
import requests
import os
import logging

import pocketbase
import users as users_module

log = logging.getLogger(__name__)

bp = Blueprint('hello_world', __name__)

PB_URL = os.environ.get('POCKETBASE_URL', 'http://pocketbase:8090')
PB_COLLECTION = 'hello_world_messages'
_FIELDS = [
    {'name': 'text', 'type': 'text', 'required': True},
    {'name': 'sender', 'type': 'text', 'required': False},
    {'name': 'avatar_url', 'type': 'text', 'required': False},
    {'name': 'created', 'type': 'autodate', 'onCreate': True, 'onUpdate': False},
]


def _ensure():
    pocketbase.ensure_collection(PB_COLLECTION, _FIELDS)


def _recent_messages(limit: int = 20) -> list[dict]:
    _ensure()
    try:
        resp = requests.get(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            params={'sort': '-created', 'perPage': limit, 'skipTotal': 1},
            timeout=5,
        )
        if resp.ok:
            return [
                {
                    'text': item['text'],
                    'sender': item.get('sender', ''),
                    'avatar_url': item.get('avatar_url') or None,
                }
                for item in resp.json().get('items', [])
            ]
        log.warning('_recent_messages failed: %s %s', resp.status_code, resp.text)
    except Exception as e:
        log.error('_recent_messages exception: %s', e)
    return []


def _save_message(text: str, sender: str = '', user_sub: str = ''):
    _ensure()
    av_url = None
    if user_sub:
        user = users_module.get_user(user_sub)
        av_url = users_module.avatar_url(user) if user else None
    try:
        r = requests.post(
            f'{PB_URL}/api/collections/{PB_COLLECTION}/records',
            json={'text': text, 'sender': sender, 'avatar_url': av_url or ''},
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
    from flask import request
    from sockets.middleware import get_session
    session = get_session(request.sid)
    sender = session.get('username', '') if session else ''
    user_sub = session.get('user_sub', '') if session else ''
    _save_message(message, sender, user_sub)
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
