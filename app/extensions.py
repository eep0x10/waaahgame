from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_socketio import SocketIO
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

db = SQLAlchemy()
migrate = Migrate()
socketio = SocketIO(async_mode='threading', cors_allowed_origins='*')
login_manager = LoginManager()
csrf = CSRFProtect()
