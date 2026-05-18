import secrets
import json
from datetime import datetime, timezone
from app.extensions import db
from app.models._base import TimestampMixin

MATCH_STATUSES = ('pending', 'army_select', 'active', 'finished', 'cancelled')
MATCH_FORMATS = ('vanguard', 'battlehost', 'spearhead')
FORMAT_POINTS = {'vanguard': 1000, 'battlehost': 2000, 'spearhead': 750}
PHASES = ('hero', 'move', 'shoot', 'charge', 'combat', 'end')


class Match(TimestampMixin, db.Model):
    __tablename__ = 'matches'
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    opponent_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True, index=True)
    system_id = db.Column(db.Integer, db.ForeignKey('game_systems.id'), nullable=False)
    format = db.Column(db.String(16), nullable=False, default='vanguard')
    points_limit = db.Column(db.Integer, nullable=False, default=1000)
    army_host_id = db.Column(db.Integer, db.ForeignKey('armies.id'), nullable=True)
    army_opponent_id = db.Column(db.Integer, db.ForeignKey('armies.id'), nullable=True)
    status = db.Column(db.String(16), nullable=False, default='pending')
    current_round = db.Column(db.Integer, nullable=False, default=0)
    current_phase = db.Column(db.String(16), nullable=False, default='pre_game')
    active_player_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    scores_json = db.Column(db.Text, nullable=True)
    public_token = db.Column(db.String(24), unique=True, nullable=False, index=True,
                             default=lambda: secrets.token_urlsafe(12))
    started_at = db.Column(db.DateTime, nullable=True)
    finished_at = db.Column(db.DateTime, nullable=True)

    host = db.relationship('User', foreign_keys=[host_id], backref='hosted_matches')
    opponent = db.relationship('User', foreign_keys=[opponent_id], backref='opponent_matches')
    active_player = db.relationship('User', foreign_keys=[active_player_id])
    system = db.relationship('GameSystem')
    army_host = db.relationship('Army', foreign_keys=[army_host_id])
    army_opponent = db.relationship('Army', foreign_keys=[army_opponent_id])

    def is_participant(self, user):
        return user.id in (self.host_id, self.opponent_id)

    def other_player(self, user):
        if user.id == self.host_id:
            return self.opponent
        return self.host

    def army_of(self, user):
        if user.id == self.host_id:
            return self.army_host
        if user.id == self.opponent_id:
            return self.army_opponent
        return None

    def score_of(self, user):
        scores = json.loads(self.scores_json) if self.scores_json else _default_scores()
        key = 'host' if user.id == self.host_id else 'opponent'
        return scores.get(key, {'vp': 0, 'cp': 1, 'turns': []})

    def set_score(self, user, **kwargs):
        scores = json.loads(self.scores_json) if self.scores_json else _default_scores()
        key = 'host' if user.id == self.host_id else 'opponent'
        for k, v in kwargs.items():
            scores[key][k] = v
        self.scores_json = json.dumps(scores)

    def get_scores(self):
        return json.loads(self.scores_json) if self.scores_json else _default_scores()


def _default_scores():
    return {
        'host': {'vp': 0, 'cp': 1, 'turns': []},
        'opponent': {'vp': 0, 'cp': 1, 'turns': []},
    }
