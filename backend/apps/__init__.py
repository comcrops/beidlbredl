from flask import Flask

APP_REGISTRY = [
    {
        'id': 'hello-world',
        'name': 'Hallo Welt',
        'icon': '👋',
        'has_mobile_controls': True,
    }
]


def register_apps(flask_app: Flask) -> None:
    from apps.hello_world.routes import bp as hello_world_bp
    flask_app.register_blueprint(hello_world_bp, url_prefix='/api/apps/hello-world')
