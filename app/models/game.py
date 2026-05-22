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

    # PDF import columns (migration: c1d2e3f4a5b6)
    rules_json = db.Column(db.Text, nullable=True)                    # JSON: {battle_traits, formations, spell_lores,
                                                                      #   prayer_lores, manifestation_lores,
                                                                      #   sub_factions, battle_tactics,
                                                                      #   heroic_traits, artefacts}
    description_pt_md = db.Column(db.Text, nullable=True)            # Faction lore intro in PT-BR markdown
    pdf_source = db.Column(db.String(255), nullable=True)             # PDF filename used for import
    pdf_imported_at = db.Column(db.DateTime, nullable=True)           # When this faction was last imported

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
    image_search_url = db.Column(db.String(512), nullable=True)       # Google Images search URL fallback
    wahapedia_url = db.Column(db.String(512), nullable=True)

    # PDF import column (migration: c1d2e3f4a5b6)
    lore_pt_md = db.Column(db.Text, nullable=True)                    # Unit lore paragraph in PT-BR markdown

    # Category: 'regular' | 'manifestation' | 'legends' | 'incomplete'
    # manifestation = Endless Spells, Manifestations, Invocations, Faction Terrain
    # legends = legacy/retired units
    # incomplete = real unit missing points or warscroll data
    unit_category = db.Column(db.String(20), nullable=False, default='regular', server_default='regular')

    def __repr__(self):
        return f'<Unit {self.slug}>'


class RegimentOfRenown(TimestampMixin, db.Model):
    __tablename__ = 'regiments_of_renown'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(128), nullable=False, unique=True)
    points_cost = db.Column(db.Integer, nullable=True)
    alliance = db.Column(db.String(16), nullable=True)    # 'Order', 'Chaos', 'Death', 'Destruction', 'Mercenary'
    units_json = db.Column(db.Text, nullable=True)        # JSON list of unit strings
    eligible_factions_json = db.Column(db.Text, nullable=True)  # JSON list of faction names
    is_new = db.Column(db.Boolean, nullable=False, default=False)  # ✹ NEW marker in PDF

    def __repr__(self):
        return f'<RegimentOfRenown {self.name}>'


class Ruleset(TimestampMixin, db.Model):
    __tablename__ = 'rulesets'
    id = db.Column(db.Integer, primary_key=True)
    game_system_id = db.Column(db.Integer, db.ForeignKey('game_systems.id'), nullable=False, index=True)
    code = db.Column(db.String(64), unique=True, nullable=False)
    name = db.Column(db.String(96), nullable=False)
    edition = db.Column(db.String(32), nullable=False)
    release_date = db.Column(db.Date, nullable=True)
    is_current = db.Column(db.Boolean, nullable=False, default=False, index=True)
    notes = db.Column(db.Text, nullable=True)
    source_url = db.Column(db.String(512), nullable=True)

    game_system = db.relationship('GameSystem', backref='rulesets')

    def __repr__(self):
        return f'<Ruleset {self.code}>'


class UnitVersion(TimestampMixin, db.Model):
    __tablename__ = 'unit_versions'
    id = db.Column(db.Integer, primary_key=True)
    unit_id = db.Column(db.Integer, db.ForeignKey('units.id'), nullable=False, index=True)
    ruleset_id = db.Column(db.Integer, db.ForeignKey('rulesets.id'), nullable=False, index=True)

    points_cost = db.Column(db.Integer, nullable=True)
    stats_json = db.Column(db.JSON, nullable=True)
    weapons_json = db.Column(db.JSON, nullable=True)
    abilities_json = db.Column(db.JSON, nullable=True)
    keywords_json = db.Column(db.JSON, nullable=True)
    companions_json = db.Column(db.JSON, nullable=True)
    notes_json = db.Column(db.JSON, nullable=True)

    __table_args__ = (db.UniqueConstraint('unit_id', 'ruleset_id', name='uq_unit_ruleset'),)

    unit = db.relationship('Unit', backref='versions')
    ruleset = db.relationship('Ruleset', backref='unit_versions')

    def __repr__(self):
        return f'<UnitVersion unit={self.unit_id} rs={self.ruleset_id}>'
