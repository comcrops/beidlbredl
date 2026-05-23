from flask_socketio import Namespace


class AppsNamespace(Namespace):
    def on_connect(self):
        pass
