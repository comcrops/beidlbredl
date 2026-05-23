from flask import Flask

APP_REGISTRY = [
    {
        'id': 'hello-world',
        'name': 'Hallo Welt',
        'icon': '👋',
        'has_mobile_controls': True,
    },
    {
        'id': 'rot-app',
        'name': 'Rote App',
        'icon': '🔴',
        'has_mobile_controls': False,
    },
    {
        'id': 'blau-app',
        'name': 'Blaue App',
        'icon': '🔵',
        'has_mobile_controls': False,
    },
]


def register_apps(flask_app: Flask) -> None:
    from apps.hello_world.routes import bp as hello_world_bp
    flask_app.register_blueprint(hello_world_bp, url_prefix='/api/apps/hello-world')

    from apps.rot_app.routes import bp as rot_app_bp
    flask_app.register_blueprint(rot_app_bp, url_prefix='/api/apps/rot-app')

    from apps.blau_app.routes import bp as blau_app_bp
    flask_app.register_blueprint(blau_app_bp, url_prefix='/api/apps/blau-app')
