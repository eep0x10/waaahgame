from flask import Blueprint, render_template, abort, request
from app.models.game import GameSystem, Faction

factions_bp = Blueprint('factions', __name__, url_prefix='/factions')


@factions_bp.route('/')
def index():
    system_filter = request.args.get('system', '').strip()
    q = request.args.get('q', '').strip()

    systems = GameSystem.query.order_by(GameSystem.name).all()

    faction_query = Faction.query
    if system_filter:
        gs = GameSystem.query.filter_by(code=system_filter).first()
        if gs:
            faction_query = faction_query.filter_by(game_system_id=gs.id)
    if q:
        faction_query = faction_query.filter(Faction.name.ilike(f'%{q}%'))

    filtered_factions = faction_query.order_by(Faction.name).all()

    template = 'factions/_results.html' if request.headers.get('HX-Request') == 'true' else 'factions/index.html'
    return render_template(
        template,
        systems=systems,
        filtered_factions=filtered_factions,
        system_filter=system_filter,
        q=q,
    )


@factions_bp.route('/<faction_slug>')
def detail(faction_slug):
    faction = Faction.query.filter_by(slug=faction_slug).first_or_404()
    units = sorted(faction.units, key=lambda u: (u.unit_role or 'zz', u.name))
    return render_template('factions/detail.html', faction=faction, units=units)
