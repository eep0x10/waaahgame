from app.extensions import db
from app.models._base import TimestampMixin


class ArmyTemplate(TimestampMixin, db.Model):
    __tablename__ = 'army_templates'
    id = db.Column(db.Integer, primary_key=True)
    system_id = db.Column(db.Integer, db.ForeignKey('game_systems.id'), nullable=False, index=True)
    faction_id = db.Column(db.Integer, db.ForeignKey('factions.id'), nullable=False, index=True)
    slug = db.Column(db.String(96), unique=True, nullable=False, index=True)
    name = db.Column(db.String(96), nullable=False)
    format = db.Column(db.String(32), nullable=False)
    points_target = db.Column(db.Integer, nullable=False)
    units_json = db.Column(db.JSON, nullable=False, default=list)
    regiments_layout_json = db.Column(db.JSON, nullable=False, default=list)
    summary = db.Column(db.Text, nullable=True)

    system = db.relationship('GameSystem')
    faction = db.relationship('Faction')

    def __repr__(self):
        return f'<ArmyTemplate {self.slug}>'
