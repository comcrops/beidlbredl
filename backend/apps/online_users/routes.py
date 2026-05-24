from flask import Blueprint
from extensions import socketio
import users as users_module

bp = Blueprint('online_users', __name__)

# username -> {count, user_sub}
_online: dict[str, dict] = {}


def user_connected(username: str, user_sub: str = '') -> None:
    if username in _online:
        _online[username]['count'] += 1
    else:
        _online[username] = {'count': 1, 'user_sub': user_sub}
    _broadcast()


def user_disconnected(username: str) -> None:
    if username not in _online:
        return
    _online[username]['count'] -= 1
    if _online[username]['count'] <= 0:
        del _online[username]
    _broadcast()


def _user_list() -> list[dict]:
    result = []
    for username, info in sorted(_online.items()):
        sub = info.get('user_sub', '')
        av_url = None
        if sub:
            user = users_module.get_user(sub)
            av_url = users_module.avatar_url(user) if user else None
        result.append({'username': username, 'avatar_url': av_url})
    return result


def emit_current(sid: str) -> None:
    socketio.emit('online_users:updated', {'users': _user_list()}, namespace='/apps', to=sid)


def _broadcast() -> None:
    socketio.emit('online_users:updated', {'users': _user_list()}, namespace='/apps')
