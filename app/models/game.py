from app.extensions import db
from app.models._base import TimestampMixin


class GameSystem(TimestampMixin, db.Model):
    __tablename__ = 'game_systems'
    id = db.Column(db.Integer, primary_key=True)
    code = db.Column(db.String(16), unique=True, nullable=False)      # 'aos4', 'w40k10'
    name = db.Column(db.String(64), nullable=False)                   # 'Age of Sigmar'
    edition = db.Column(db.String(32), nullable=False)                # '4th Edition (2024)'
    ruleset_label = db.Column(db.String(64), nullable=False)          # 'GHB 2025-26 + April 2026 Battlescroll'

    factions = db.relationship('Faction', backref='game_system', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<GameSystem {self.code}>'


class Faction(TimestampMixin, db.Model):
    __tablename__ = 'factions'
    id = db.Column(db.Integer, primary_key=True)
    game_system_id = db.Column(db.Integer, db.ForeignKey('game_systems.id'), nullable=False, index=True)
    code = db.Column(db.String(32), unique=True, nullable=False)      # 'skaven', 'seraphon'
    slug = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(64), nullable=False)
    grand_alliance = db.Column(db.String(16), nullable=True)          # 'Order', 'Chaos', 'Death', 'Destruction'
    blurb = db.Column(db.Text, nullable=True)                         # 1-2 paragraph faction summary

    units = db.relationship('Unit', backref='faction', cascade='all, delete-orphan')

    def __repr__(self):
        return f'<Faction {self.code}>'


class Unit(TimestampMixin, db.Model):
    __tablename__ = 'units'
    id = db.Column(db.Integer, primary_key=True)
    faction_id = db.Column(db.Integer, db.ForeignKey('factions.id'), nullable=False, index=True)
    slug = db.Column(db.String(96), unique=True, nullable=False, index=True)
    name = db.Column(db.String(96), nullable=False)
    points_cost = db.Column(db.Integer, nullable=False)
    base_size_mm = db.Column(db.String(16), nullable=True)
    model_count = db.Column(db.Integer, nullable=False, default=1)
    unit_role = db.Column(db.String(32), nullable=True)               # 'Hero', 'Battleline', 'Behemoth', etc.
    can_be_general = db.Column(db.Boolean, default=False)
    can_be_reinforced = db.Column(db.Boolean, default=False)

    stats_json = db.Column(db.JSON, nullable=False, default=dict)     # move/save/control/health
    weapons_json = db.Column(db.JSON, nullable=False, default=list)   # melee + ranged
    abilities_json = db.Column(db.JSON, nullable=False, default=list) # named abilities
    keywords_json = db.Column(db.JSON, nullable=False, default=list)  # ['CHAOS','SKAVENTIDE','VERMINUS','HERO']
    companions_json = db.Column(db.JSON, nullable=False, default=list)# eligible companions (Heroes only)

    image_path = db.Column(db.String(255), nullable=True)             # 'units/skaven/stormvermin.jpg'
    image_source_url = db.Column(db.String(512), nullable=True)
    wahapedia_url = db.Column(db.String(512), nullable=True)

    def __repr__(self):
        return f'<Unit {self.slug}>'
