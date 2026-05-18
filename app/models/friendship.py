from sqlalchemy import CheckConstraint, UniqueConstraint
from app.extensions import db
from app.models._base import TimestampMixin

FRIENDSHIP_STATUSES = ('pending', 'accepted', 'blocked')


class Friendship(TimestampMixin, db.Model):
    __tablename__ = 'friendships'
    __table_args__ = (
        UniqueConstraint('requester_id', 'addressee_id', name='uq_friendship_pair'),
        CheckConstraint('requester_id != addressee_id', name='ck_friendship_self'),
    )
    id = db.Column(db.Integer, primary_key=True)
    requester_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    addressee_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    status = db.Column(db.String(16), nullable=False, default='pending')

    requester = db.relationship('User', foreign_keys=[requester_id], backref='sent_friend_requests')
    addressee = db.relationship('User', foreign_keys=[addressee_id], backref='received_friend_requests')
