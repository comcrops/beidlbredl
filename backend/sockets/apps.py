from flask_socketio import Namespace
from flask import request
from sockets.middleware import authenticate_socket, get_session, clear_session


class AppsNamespace(Namespace):
    def on_connect(self, auth=None):
        session = authenticate_socket(auth or {}, request.sid)
        if session is None:
            return False
        from apps.online_users.routes import user_connected, emit_current
        if not session.get('is_kiosk'):
            user_connected(session['username'])
        else:
            emit_current(request.sid)

    def on_disconnect(self, reason=None):
        session = get_session(request.sid)
        if session and not session.get('is_kiosk'):
            from apps.online_users.routes import user_disconnected
            user_disconnected(session['username'])
        clear_session(request.sid)
