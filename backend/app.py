from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import socketio


def create_app(config=None) -> Flask:
    app = Flask(__name__)
    app.config.from_object(Config)
    if config:
        app.config.update(config)

    CORS(app)
    async_mode = app.config.get('SOCKETIO_ASYNC_MODE', 'gevent')
    socketio.init_app(app, cors_allowed_origins='*', async_mode=async_mode)

    from apps import register_apps
    register_apps(app)

    from sockets.general import GeneralNamespace
    from sockets.apps import AppsNamespace
    socketio.on_namespace(GeneralNamespace('/general'))
    socketio.on_namespace(AppsNamespace('/apps'))

    @app.route('/api/health')
    def health():
        return {'status': 'ok'}

    return app
