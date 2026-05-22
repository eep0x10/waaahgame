from flask import Blueprint, render_template
from app.extensions import db
from app.models.game import RegimentOfRenown
import json

rules_bp = Blueprint('rules', __name__, url_prefix='/rules')


@rules_bp.route('/')
def index():
    return render_template('rules/index.html')


@rules_bp.route('/aos')
def aos_overview():
    return render_template('rules/aos/index.html')


@rules_bp.route('/aos/turn-structure')
def aos_turn():
    return render_template('rules/aos/turn.html')


@rules_bp.route('/aos/abilities')
def aos_abilities():
    return render_template('rules/aos/abilities.html')


@rules_bp.route('/aos/composition')
def aos_composition():
    return render_template('rules/aos/composition.html')


@rules_bp.route('/aos/setup')
def aos_setup():
    return render_template('rules/aos/setup.html')


@rules_bp.route('/aos/movement')
def aos_movement():
    return render_template('rules/aos/movement.html')


@rules_bp.route('/aos/combat')
def aos_combat():
    return render_template('rules/aos/combat.html')


@rules_bp.route('/aos/shooting')
def aos_shooting():
    return render_template('rules/aos/shooting.html')


@rules_bp.route('/aos/charge')
def aos_charge():
    return render_template('rules/aos/charge.html')


@rules_bp.route('/aos/magic')
def aos_magic():
    return render_template('rules/aos/magic.html')


@rules_bp.route('/aos/terrain')
def aos_terrain():
    return render_template('rules/aos/terrain.html')


@rules_bp.route('/aos/battle-tactics')
def aos_battle_tactics():
    return render_template('rules/aos/battle-tactics.html')


@rules_bp.route('/aos/battleplans')
def aos_battleplans():
    return render_template('rules/aos/battleplans.html')


@rules_bp.route('/aos/glossary')
def aos_glossary():
    return render_template('rules/aos/glossary.html')


@rules_bp.route('/aos/tournament')
def aos_tournament():
    return render_template('rules/aos/tournament.html')


@rules_bp.route('/aos/regiments-of-renown')
def aos_regiments_of_renown():
    rors = RegimentOfRenown.query.order_by(RegimentOfRenown.alliance, RegimentOfRenown.name).all()
    for r in rors:
        r.units_list = json.loads(r.units_json) if r.units_json else []
        r.factions_list = json.loads(r.eligible_factions_json) if r.eligible_factions_json else []
    by_alliance = {}
    alliance_order = ['Mercenary', 'Order', 'Chaos', 'Death', 'Destruction']
    for r in rors:
        key = r.alliance or 'Outro'
        by_alliance.setdefault(key, []).append(r)
    grouped = [(a, by_alliance[a]) for a in alliance_order if a in by_alliance]
    for a, lst in by_alliance.items():
        if a not in alliance_order:
            grouped.append((a, lst))
    return render_template('rules/aos_regiments_of_renown.html', grouped=grouped, total=len(rors))
