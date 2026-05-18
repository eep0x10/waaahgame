import os
from flask import Flask
from .config import get_config
from .extensions import db, migrate, socketio, login_manager


def create_app(config_name='dev'):
    app = Flask(__name__, instance_relative_config=True)

    # Ensure instance folder exists
    try:
        os.makedirs(app.instance_path, exist_ok=True)
    except OSError:
        pass

    app.config.from_object(get_config(config_name))

    # Init extensions
    db.init_app(app)
    migrate.init_app(app, db)
    socketio.init_app(app)
    login_manager.init_app(app)

    # Stub user_loader — Phase 1 will replace this with a real User query.
    @login_manager.user_loader
    def _load_user(user_id):  # noqa: F811
        return None

    # Register blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    # Register sockets
    from .sockets import register_sockets
    register_sockets(socketio)

    # Import models so Alembic sees them
    from . import models  # noqa: F401

    return app
