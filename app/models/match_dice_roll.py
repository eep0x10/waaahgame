import json
from datetime import datetime, timezone
from app.extensions import db


class MatchDiceRoll(db.Model):
    __tablename__ = 'match_dice_rolls'
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, index=True)
    actor_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    round = db.Column(db.Integer, nullable=False, default=0)
    phase = db.Column(db.String(16), nullable=True)
    formula = db.Column(db.String(32), nullable=False)
    results_json = db.Column(db.Text, nullable=False)
    total = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False,
                           default=lambda: datetime.now(timezone.utc))

    match = db.relationship('Match', backref=db.backref('dice_rolls', order_by='MatchDiceRoll.created_at'))
    actor = db.relationship('User')

    def get_results(self):
        return json.loads(self.results_json)
