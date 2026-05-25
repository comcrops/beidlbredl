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
    {
        'id': 'online-users',
        'name': 'Wer is da?',
        'icon': '👥',
        'has_mobile_controls': False,
    },
    {
        'id': 'hagenberg-mittag',
        'name': 'Hagenberger Mittagessen',
        'icon': '🍽️',
        'has_mobile_controls': True,
    },
]


def register_apps(flask_app: Flask) -> None:
    from apps.hello_world.routes import bp as hello_world_bp
    flask_app.register_blueprint(hello_world_bp, url_prefix='/api/apps/hello-world')

    from apps.rot_app.routes import bp as rot_app_bp
    flask_app.register_blueprint(rot_app_bp, url_prefix='/api/apps/rot-app')

    from apps.blau_app.routes import bp as blau_app_bp
    flask_app.register_blueprint(blau_app_bp, url_prefix='/api/apps/blau-app')

    from apps.online_users.routes import bp as online_users_bp
    flask_app.register_blueprint(online_users_bp, url_prefix='/api/apps/online-users')

    from apps.hagenberg_mittag.routes import bp as hagenberg_mittag_bp
    flask_app.register_blueprint(hagenberg_mittag_bp, url_prefix='/api/apps/hagenberg-mittag')
