import secrets
from app.extensions import db
from app.models._base import TimestampMixin


BATTLEPACKS = {
    'vanguard':   {'label': 'Vanguard',   'pts': 1000, 'regiments': (1, 2), 'auxiliary': (0, 1)},
    'battlehost': {'label': 'Battlehost', 'pts': 2000, 'regiments': (2, 4), 'auxiliary': (0, 2)},
}


class Army(TimestampMixin, db.Model):
    __tablename__ = 'armies'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False, index=True)
    faction_id = db.Column(db.Integer, db.ForeignKey('factions.id'), nullable=False, index=True)
    name = db.Column(db.String(96), nullable=False)
    battlepack = db.Column(db.String(16), nullable=False, default='vanguard')
    points_limit = db.Column(db.Integer, nullable=False, default=1000)
    notes = db.Column(db.Text, nullable=True)
    public_token = db.Column(db.String(32), unique=True, nullable=True, index=True)

    user = db.relationship('User', backref='armies')
    faction = db.relationship('Faction')
    regiments = db.relationship('Regiment', backref='army', cascade='all, delete-orphan',
                                order_by='Regiment.position')
    army_units = db.relationship('ArmyUnit', backref='army', cascade='all, delete-orphan')

    def ensure_public_token(self):
        if not self.public_token:
            self.public_token = secrets.token_urlsafe(16)
        return self.public_token


class Regiment(TimestampMixin, db.Model):
    __tablename__ = 'regiments'
    id = db.Column(db.Integer, primary_key=True)
    army_id = db.Column(db.Integer, db.ForeignKey('armies.id'), nullable=False, index=True)
    position = db.Column(db.Integer, nullable=False)

    army_units = db.relationship('ArmyUnit', backref='regiment',
                                  primaryjoin='Regiment.id == ArmyUnit.regiment_id')

    @property
    def leader(self):
        for au in self.army_units:
            if au.is_leader:
                return au
        return None


class ArmyUnit(TimestampMixin, db.Model):
    __tablename__ = 'army_units'
    id = db.Column(db.Integer, primary_key=True)
    army_id = db.Column(db.Integer, db.ForeignKey('armies.id'), nullable=False, index=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False, index=True)
    regiment_id = db.Column(db.Integer, db.ForeignKey('regiments.id'), nullable=True, index=True)
    is_reinforced = db.Column(db.Boolean, nullable=False, default=False)
    is_leader = db.Column(db.Boolean, nullable=False, default=False)
    is_general = db.Column(db.Boolean, nullable=False, default=False)
    sort_order = db.Column(db.Integer, nullable=False, default=0)

    unit = db.relationship('Unit')

    @property
    def slot_kind(self):
        if self.regiment_id is None:
            return 'auxiliary'
        return 'leader' if self.is_leader else 'companion'

    @property
    def points(self):
        base = self.unit.points_cost
        return base * 2 if self.is_reinforced else base
