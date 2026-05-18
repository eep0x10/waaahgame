from datetime import datetime, timezone
from app.extensions import db


class MatchMessage(db.Model):
    __tablename__ = 'match_messages'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.String(500), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    match = db.relationship('Match', backref=db.backref('messages', order_by='MatchMessage.created_at'))
    actor = db.relationship('User')
