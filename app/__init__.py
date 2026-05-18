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

    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Sign in to enter the war-host.'

    from .models.user import User

    @login_manager.user_loader
    def load_user(user_id):
        return db.session.get(User, int(user_id))

    # Register blueprints
    from .routes.main import main_bp
    app.register_blueprint(main_bp)

    from .routes.auth import auth_bp
    app.register_blueprint(auth_bp)

    from .routes.friends import friends_bp
    app.register_blueprint(friends_bp)

    # Register sockets
    from .sockets import register_sockets
    register_sockets(socketio)

    # Import models so Alembic sees them
    from . import models  # noqa: F401

    return app
