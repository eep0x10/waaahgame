from app.extensions import db
from sqlalchemy import UniqueConstraint


class MatchCasualty(db.Model):
    __tablename__ = 'match_casualties'
    __table_args__ = (
        UniqueConstraint('match_id', 'army_unit_id', name='uq_casualty_match_unit'),
    )
    id = db.Column(db.Integer, primary_key=True)
    match_id = db.Column(db.Integer, db.ForeignKey('matches.id'), nullable=False, index=True)
    army_unit_id = db.Column(db.Integer, db.ForeignKey('army_units.id'), nullable=False, index=True)
    round = db.Column(db.Integer, nullable=False, default=0)
    removed = db.Column(db.Boolean, nullable=False, default=False)

    match = db.relationship('Match', backref='casualties')
    army_unit = db.relationship('ArmyUnit')
