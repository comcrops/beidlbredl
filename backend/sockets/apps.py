from flask_socketio import Namespace
from flask import request
from sockets.middleware import authenticate_socket, clear_session


class AppsNamespace(Namespace):
    def on_connect(self, auth=None):
        session = authenticate_socket(auth or {}, request.sid)
        if session is None:
            return False

    def on_disconnect(self):
        clear_session(request.sid)
