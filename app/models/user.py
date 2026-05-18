from flask_login import UserMixin
import bcrypt
from app.extensions import db
from app.models._base import TimestampMixin


class User(UserMixin, TimestampMixin, db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(32), unique=True, nullable=False, index=True)
    email = db.Column(db.String(255), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(255), nullable=False)
    display_name = db.Column(db.String(64), nullable=True)
    is_admin = db.Column(db.Boolean, nullable=False, default=False)

    def set_password(self, raw: str) -> None:
        self.password_hash = bcrypt.hashpw(raw.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

    def check_password(self, raw: str) -> bool:
        return bcrypt.checkpw(raw.encode('utf-8'), self.password_hash.encode('utf-8'))

    @property
    def name(self) -> str:
        return self.display_name or self.username

    def __repr__(self) -> str:
        return f'<User {self.username}>'
