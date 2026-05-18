import json
from datetime import datetime, timezone
from app.extensions import db

EVENT_KINDS = ('phase_advance', 'score_change', 'casualty', 'note', 'match_start', 'match_finish')


class MatchEvent(db.Model):
    __tablename__ = 'match_events'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, index=True)
    round = db.Column(db.Integer, nullable=False, default=0)
    phase = db.Column(db.String(16), nullable=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    kind = db.Column(db.String(24), nullable=False)
    payload_json = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    match = db.relationship('Match', backref=db.backref('events', order_by='MatchEvent.created_at'))
    actor = db.relationship('User')

    def get_payload(self):
        return json.loads(self.payload_json) if self.payload_json else {}
