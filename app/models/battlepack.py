import json
from app.extensions import db
from app.models._base import TimestampMixin


class Battlepack(TimestampMixin, db.Model):
    __tablename__ = 'battlepacks_db'
    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('game_systems.id'), nullable=False, index=True)
    slug = db.Column(db.String(64), unique=True, nullable=False, index=True)
    name = db.Column(db.String(96), nullable=False)
    format = db.Column(db.String(32), nullable=False)
    summary = db.Column(db.Text, nullable=True)
    primary_objective = db.Column(db.Text, nullable=True)
    secondary_objectives_json = db.Column(db.JSON, nullable=False, default=list)
    deployment_text = db.Column(db.Text, nullable=True)
    special_rules_text = db.Column(db.Text, nullable=True)

    system = db.relationship('GameSystem')
    matches = db.relationship('Match', backref='battlepack', lazy='dynamic')

    def __repr__(self):
        return f'<Battlepack {self.slug}>'
