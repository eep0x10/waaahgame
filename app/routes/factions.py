from flask import Blueprint, render_template, abort
from app.models.game import GameSystem, Faction

factions_bp = Blueprint('factions', __name__, url_prefix='/factions')


@factions_bp.route('/')
def index():
    systems = GameSystem.query.order_by(GameSystem.name).all()
    return render_template('factions/index.html', systems=systems)


@factions_bp.route('/<faction_slug>')
def detail(faction_slug):
    faction = Faction.query.filter_by(slug=faction_slug).first_or_404()
    units = sorted(faction.units, key=lambda u: (u.unit_role or 'zz', u.name))
    return render_template('factions/detail.html', faction=faction, units=units)
