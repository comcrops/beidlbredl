from flask import Blueprint
from extensions import socketio

bp = Blueprint('online_users', __name__)

# username -> connection count (handles multiple tabs per user)
_online: dict[str, int] = {}


def user_connected(username: str) -> None:
    _online[username] = _online.get(username, 0) + 1
    _broadcast()


def user_disconnected(username: str) -> None:
    count = _online.get(username, 0) - 1
    if count <= 0:
        _online.pop(username, None)
    else:
        _online[username] = count
    _broadcast()


def _broadcast() -> None:
    socketio.emit(
        'online_users:updated',
        {'users': sorted(_online.keys())},
        namespace='/apps',
    )
