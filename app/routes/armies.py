import json
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.army import Army, Regiment, ArmyUnit
from app.models.game import Faction, Unit, GameSystem, RegimentOfRenown
from app.models.army_template import ArmyTemplate
from app.services.validator import validate
from app.services.validators import validator_for, all_systems
from app.services.formats import formats_for_system


def _load_faction_rules(army):
    """Return (has_rules: bool, rules_dict: dict|None)."""
    faction = army.faction
    if not faction or not faction.rules_json:
        return False, None
    try:
        return True, json.loads(faction.rules_json)
    except (ValueError, TypeError):
        return False, None

armies_bp = Blueprint('armies', __name__, url_prefix='/armies')


def _owned_army_or_404(army_id):
    army = db.session.get(Army, army_id)
    if army is None or army.user_id != current_user.id:
        abort(404)
    return army


def _is_htmx():
    return request.headers.get('HX-Request') == 'true'


def _summary_html(army):
    result = validate(army)
    return render_template('armies/_summary.html', army=army, result=result)


def _army_validator(army):
    """Return the validator for an army, or abort(400) if system unknown."""
    try:
        code = army.faction.game_system.code
    except AttributeError:
        abort(400)
    if not code:
        abort(400)
    try:
        return validator_for(code)
    except ValueError:
        abort(400)


@armies_bp.route('/')
@login_required
def index():
    armies = Army.query.filter_by(user_id=current_user.id).order_by(Army.created_at.desc()).all()
    results = {a.id: validate(a) for a in armies}
    return render_template('armies/index.html', armies=armies, results=results)


@armies_bp.route('/templates')
@login_required
def templates():
    system_filter = request.args.get('system', '').strip()
    faction_filter = request.args.get('faction', '').strip()
    q = ArmyTemplate.query
    if system_filter:
        gs = GameSystem.query.filter_by(code=system_filter).first()
        if gs:
            q = q.filter_by(system_id=gs.id)
    if faction_filter:
        fac = Faction.query.filter_by(slug=faction_filter).first()
        if fac:
            q = q.filter_by(faction_id=fac.id)
    army_templates = q.order_by(ArmyTemplate.name).all()
    systems = GameSystem.query.order_by(GameSystem.name).all()
    factions = Faction.query.order_by(Faction.name).all()

    # Build validators_by_code for template badge rendering
    validators_by_code = {code: cls for code, cls in all_systems().items()}

    return render_template('armies/templates.html', army_templates=army_templates,
                           systems=systems, factions=factions,
                           system_filter=system_filter, faction_filter=faction_filter,
                           validators_by_code=validators_by_code)


@armies_bp.route('/from-template/<int:template_id>', methods=['POST'])
@login_required
def from_template(template_id):
    tmpl = db.session.get(ArmyTemplate, template_id)
    if tmpl is None:
        abort(404)

    faction = db.session.get(Faction, tmpl.faction_id)
    if not faction:
        abort(400)

    if not faction.game_system:
        abort(400)

    system_code = faction.game_system.code
    try:
        v = validator_for(system_code)
    except ValueError:
        abort(400)

    valid_formats = v.formats
    pts_limit = valid_formats.get(tmpl.format, tmpl.points_target)

    army = Army(
        user_id=current_user.id,
        faction_id=tmpl.faction_id,
        name=tmpl.name,
        battlepack=tmpl.format,
        points_limit=pts_limit,
        notes=tmpl.summary,
    )
    db.session.add(army)
    db.session.flush()

    unit_cache = {}

    for reg_data in (tmpl.regiments_layout_json or []):
        # Only create regiment structure if system supports groups
        if v.supports_groups:
            reg = Regiment(army_id=army.id, position=reg_data.get('position', 1))
            db.session.add(reg)
            db.session.flush()
            reg_id = reg.id
        else:
            reg_id = None

        sort_counter = [0]

        def _add_unit(slug, is_leader=False, is_general=False, _reg_id=reg_id):
            if slug not in unit_cache:
                unit_cache[slug] = Unit.query.filter_by(slug=slug, faction_id=tmpl.faction_id).first()
            unit = unit_cache[slug]
            if not unit:
                return
            sort_counter[0] += 1
            au = ArmyUnit(
                army_id=army.id,
                unit_id=unit.id,
                regiment_id=_reg_id,
                is_leader=is_leader,
                is_general=is_general,
                sort_order=sort_counter[0],
            )
            db.session.add(au)

        leader_slug = reg_data.get('leader_slug')
        if leader_slug:
            _add_unit(leader_slug, is_leader=v.supports_groups,
                      is_general=(reg_data.get('position', 1) == 1))

        for comp_slug in reg_data.get('companion_slugs', []):
            _add_unit(comp_slug)

    db.session.commit()
    flash(f'Exército "{army.name}" criado a partir do modelo.', 'success')
    return redirect(url_for('armies.show', army_id=army.id))


@armies_bp.route('/new', methods=['GET'])
@login_required
def new():
    from app.models.game import Ruleset
    from app.services.formats import _get_system_formats
    factions = Faction.query.order_by(Faction.name).all()
    systems = GameSystem.query.order_by(GameSystem.name).all()
    rulesets_by_system = {}
    for gs in systems:
        rulesets_by_system[gs.code] = [
            {'id': r.id, 'code': r.code, 'name': r.name, 'edition': r.edition,
             'release_date': r.release_date.isoformat() if r.release_date else None,
             'is_current': r.is_current}
            for r in gs.rulesets
        ]
    return render_template('armies/new.html', factions=factions, systems=systems,
                           system_formats=_get_system_formats(),
                           rulesets_by_system=rulesets_by_system)


@armies_bp.route('/new', methods=['POST'])
@login_required
def new_post():
    from app.models.game import Ruleset
    from app.services.unit_view import current_ruleset_for_system
    name = request.form.get('name', '').strip()
    faction_id = request.form.get('faction_id', type=int)
    battlepack = request.form.get('battlepack', '').strip()
    ruleset_id = request.form.get('ruleset_id', type=int)

    if not name or not faction_id:
        flash('Nome e facção são obrigatórios.', 'error')
        return redirect(url_for('armies.new'))

    faction = db.session.get(Faction, faction_id)
    if not faction:
        abort(400)

    if not faction.game_system:
        flash('Facção sem sistema de jogo configurado.', 'error')
        abort(400)

    system_code = faction.game_system.code
    try:
        v = validator_for(system_code)
    except ValueError:
        abort(400)

    valid_formats = v.formats

    if battlepack not in valid_formats:
        battlepack = v.default_format

    pts_limit = valid_formats.get(battlepack, 1000)

    if ruleset_id is None:
        rs = current_ruleset_for_system(faction.game_system)
        if rs:
            ruleset_id = rs.id

    army = Army(
        user_id=current_user.id,
        faction_id=faction_id,
        name=name,
        battlepack=battlepack,
        points_limit=pts_limit,
        ruleset_id=ruleset_id,
    )
    db.session.add(army)
    db.session.flush()

    # Only create initial regiment structure for systems that use groups
    if v.supports_groups:
        reg1 = Regiment(army_id=army.id, position=1)
        db.session.add(reg1)

    db.session.commit()

    return redirect(url_for('armies.show', army_id=army.id))


@armies_bp.route('/<int:army_id>', methods=['GET'])
@login_required
def show(army_id):
    army = _owned_army_or_404(army_id)
    # Bug 7: manifestations are summoned via lores, not added to regiments/aux.
    units = sorted(
        [u for u in army.faction.units if u.unit_category != 'manifestation'],
        key=lambda u: (1 if u.unit_category == 'legends' else 0, u.unit_role or 'zz', u.name)
    )
    aux_units = [au for au in army.army_units if au.regiment_id is None]
    result = validate(army)
    v = _army_validator(army)
    faction_has_rules, faction_rules = _load_faction_rules(army)
    return render_template(
        'armies/show.html',
        army=army,
        units=units,
        aux_units=aux_units,
        result=result,
        validator=v,
        faction_has_rules=faction_has_rules,
        faction_rules=faction_rules,
    )


@armies_bp.route('/<int:army_id>/units', methods=['POST'])
@login_required
def add_unit(army_id):
    army = _owned_army_or_404(army_id)
    unit_slug = request.form.get('unit_slug', '').strip()
    target = request.form.get('target', 'aux').strip()
    reinforced = request.form.get('reinforced', '0') in ('1', 'true', 'on')

    unit = Unit.query.filter_by(slug=unit_slug).first()
    if not unit or unit.faction_id != army.faction_id:
        abort(400)
    # Bug 7: manifestations are managed via lore selection, not added manually.
    if getattr(unit, 'unit_category', None) == 'manifestation':
        abort(400, "Manifestações são gerenciadas separadamente via Lore de Manifestação.")

    regiment = None
    regiment_id = None
    is_leader = False
    is_general = False

    if target.startswith('reg-'):
        try:
            reg_id = int(target.split('-', 1)[1])
        except (ValueError, IndexError):
            abort(400)
        regiment = Regiment.query.filter_by(id=reg_id, army_id=army.id).first_or_404()
        regiment_id = regiment.id
        existing_leaders = [au for au in regiment.army_units if au.is_leader]
        if not existing_leaders and _is_hero(unit):
            is_leader = True
            reg1_list = [r for r in army.regiments if r.position == 1]
            if reg1_list and reg1_list[0].id == regiment.id:
                generals = [au for au in army.army_units if au.is_general]
                if not generals:
                    is_general = True

    max_sort = db.session.query(
        db.func.max(ArmyUnit.sort_order)
    ).filter_by(army_id=army.id).scalar() or 0

    au = ArmyUnit(
        army_id=army.id,
        unit_id=unit.id,
        regiment_id=regiment_id,
        is_reinforced=reinforced and unit.can_be_reinforced,
        is_leader=is_leader,
        is_general=is_general,
        sort_order=max_sort + 1,
    )
    db.session.add(au)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        if regiment:
            regiment = db.session.get(Regiment, regiment.id)
            faction_has_rules, faction_rules = _load_faction_rules(army)
            partial = render_template('armies/_regiment.html', regiment=regiment, army=army,
                                      result=result, validator=v,
                                      faction_has_rules=faction_has_rules,
                                      faction_rules=faction_rules)
        else:
            aux_units = [a for a in army.army_units if a.regiment_id is None]
            partial = render_template('armies/_auxiliary.html', army=army, aux_units=aux_units,
                                      result=result, validator=v)
        return partial + summary
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/move', methods=['POST'])
@login_required
def move_unit(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()
    target = request.form.get('target', 'aux').strip()

    old_regiment_id = au.regiment_id  # noqa: F841

    if target == 'aux':
        au.regiment_id = None
        au.is_leader = False
        if au.is_general:
            au.is_general = False
    elif target.startswith('reg-'):
        try:
            reg_id = int(target.split('-', 1)[1])
        except (ValueError, IndexError):
            abort(400)
        regiment = Regiment.query.filter_by(id=reg_id, army_id=army.id).first_or_404()
        au.regiment_id = regiment.id
        existing_leaders = [a for a in regiment.army_units if a.is_leader and a.id != au.id]
        if not existing_leaders and _is_hero(au.unit):
            au.is_leader = True
        else:
            au.is_leader = False

    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                               validator=v) + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/remove', methods=['POST'])
@login_required
def remove_unit(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()
    db.session.delete(au)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                               validator=v) + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/reinforce', methods=['POST'])
@login_required
def reinforce_unit(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()
    if au.unit.can_be_reinforced:
        au.is_reinforced = not au.is_reinforced
        db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        row = render_template('armies/_army_unit_row.html', au=au, army=army, result=result,
                              validator=v)
        return row + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/promote-leader', methods=['POST'])
@login_required
def promote_leader(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()

    if au.regiment_id is None:
        abort(400)

    regiment = db.session.get(Regiment, au.regiment_id)
    for other in regiment.army_units:
        other.is_leader = False
    au.is_leader = True
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        faction_has_rules, faction_rules = _load_faction_rules(army)
        partial = render_template('armies/_regiment.html', regiment=regiment, army=army,
                                  result=result, validator=v,
                                  faction_has_rules=faction_has_rules,
                                  faction_rules=faction_rules)
        return partial + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/set-general', methods=['POST'])
@login_required
def set_general(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()

    # Bug 4: validate can_be_general.
    # If any unit in the army has can_be_general=True explicitly set, enforce it.
    # Otherwise (all False/NULL — typical for most heroes), allow any Hero.
    any_explicit = any(other.unit.can_be_general for other in army.army_units)
    if any_explicit and not au.unit.can_be_general:
        abort(400, "Esta unidade não pode ser General (sem keyword CAN BE GENERAL).")

    # Also must be a Hero (rule 3.2)
    if not _is_hero(au.unit):
        abort(400, "Apenas Heroes podem ser o General.")

    for other in army.army_units:
        other.is_general = False
    au.is_general = True
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        return _summary_html(army)

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/enhancement', methods=['POST'])
@login_required
def set_enhancement(army_id, au_id):
    """Set or clear heroic_trait / artefact / command_trait on a Regiment leader."""
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()

    # Must be a Regiment leader
    if au.regiment_id is None:
        abort(400, "Auxiliares não podem receber Aprimoramentos.")
    # RoR members cannot receive enhancements
    reg = db.session.get(Regiment, au.regiment_id)
    if reg and reg.is_ror:
        abort(400, "Unidades de Regimento de Renome não podem receber Aprimoramentos.")
    if not au.is_leader:
        abort(400, "Apenas líderes de Regimento podem receber Aprimoramentos.")

    # Load faction rules to validate values
    _, faction_rules = _load_faction_rules(army)
    faction_rules = faction_rules or {}

    valid_traits    = {t['name'] for t in faction_rules.get('heroic_traits', []) if t.get('name')}
    valid_artefacts = {a['name'] for a in faction_rules.get('artefacts', []) if a.get('name')}
    valid_cmd       = {c['name'] for c in faction_rules.get('command_traits', []) if c.get('name')}
    if not valid_cmd:
        valid_cmd = valid_traits  # fallback

    enh_type  = request.form.get('enhancement_type', '').strip()
    enh_value = request.form.get('enhancement_value', '').strip()

    # Empty value = clear
    if enh_value == '':
        enh_value = None

    if enh_type == 'heroic_trait':
        if enh_value and valid_traits and enh_value not in valid_traits:
            abort(400, f'Heroic Trait "{enh_value}" inválido para esta facção.')
        # Uniqueness check
        if enh_value:
            conflict = ArmyUnit.query.filter_by(army_id=army_id, heroic_trait=enh_value).filter(
                ArmyUnit.id != au_id).first()
            if conflict:
                abort(400, f'Heroic Trait "{enh_value}" já está em uso neste exército.')
        au.heroic_trait = enh_value

    elif enh_type == 'artefact':
        if enh_value and valid_artefacts and enh_value not in valid_artefacts:
            abort(400, f'Artefact "{enh_value}" inválido para esta facção.')
        if enh_value:
            conflict = ArmyUnit.query.filter_by(army_id=army_id, artefact=enh_value).filter(
                ArmyUnit.id != au_id).first()
            if conflict:
                abort(400, f'Artefact "{enh_value}" já está em uso neste exército.')
        au.artefact = enh_value

    elif enh_type == 'command_trait':
        if not au.is_general:
            abort(400, 'Command Trait só pode ser atribuído ao General.')
        if enh_value and valid_cmd and enh_value not in valid_cmd:
            abort(400, f'Command Trait "{enh_value}" inválido para esta facção.')
        au.command_trait = enh_value

    else:
        abort(400, 'Tipo de aprimoramento desconhecido.')

    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        regiment = db.session.get(Regiment, au.regiment_id)
        faction_has_rules, faction_rules_fresh = _load_faction_rules(army)
        partial = render_template('armies/_regiment.html', regiment=regiment, army=army,
                                  result=result, validator=v,
                                  faction_has_rules=faction_has_rules,
                                  faction_rules=faction_rules_fresh)
        return partial + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/regiments', methods=['POST'])
@login_required
def add_regiment(army_id):
    army = _owned_army_or_404(army_id)
    v = _army_validator(army)

    if not v.supports_groups:
        abort(400)

    # Use AoS-specific BATTLEPACKS if available, otherwise use formats
    from app.services.validators.aos import AoSValidator
    if isinstance(v, AoSValidator):
        bp = AoSValidator.BATTLEPACKS.get(army.battlepack, AoSValidator.BATTLEPACKS['vanguard'])
        _, reg_max = bp['regiments']
    else:
        # Generic fallback for future systems that support groups
        reg_max = 4

    if len(army.regiments) >= reg_max:
        flash(f'Máximo de {reg_max} {v.group_label_plural.lower()} para {army.battlepack.capitalize()}.', 'error')
        if _is_htmx():
            result = validate(army)
            return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                                   validator=v)
        return redirect(url_for('armies.show', army_id=army_id))

    next_pos = max((r.position for r in army.regiments), default=0) + 1
    reg = Regiment(army_id=army.id, position=next_pos)
    db.session.add(reg)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                               validator=v) + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/ror/available', methods=['GET'])
@login_required
def ror_available(army_id):
    """HTMX partial: list of RoR available for army's grand alliance."""
    army = _owned_army_or_404(army_id)
    faction = army.faction
    army_alliance = faction.grand_alliance if faction else None

    q = RegimentOfRenown.query
    if army_alliance:
        q = q.filter(
            db.or_(
                RegimentOfRenown.alliance == army_alliance,
                db.func.lower(RegimentOfRenown.alliance) == 'mercenary',
            )
        )
    else:
        # No faction alliance defined — show only Mercenary
        q = q.filter(db.func.lower(RegimentOfRenown.alliance) == 'mercenary')

    available = q.order_by(RegimentOfRenown.name).all()
    return render_template('armies/_ror_picker.html', army=army, available=available)


@armies_bp.route('/<int:army_id>/ror/add', methods=['POST'])
@login_required
def add_ror(army_id):
    """Add a Regiment of Renown as a regiment slot in the army."""
    army = _owned_army_or_404(army_id)
    v = _army_validator(army)

    if not v.supports_groups:
        abort(400)

    ror_id = request.form.get('ror_id', type=int)
    if not ror_id:
        abort(400)

    ror = db.session.get(RegimentOfRenown, ror_id)
    if not ror:
        abort(404)

    # Alliance check
    faction = army.faction
    army_alliance = faction.grand_alliance if faction else None
    ror_alliance = ror.alliance or ''
    if ror_alliance.lower() != 'mercenary':
        if army_alliance and ror_alliance != army_alliance:
            flash(
                f'RoR "{ror.name}" é da aliança {ror_alliance}; '
                f'exército é {army_alliance}.',
                'error'
            )
            if _is_htmx():
                result = validate(army)
                return render_template('armies/_regiments_and_aux.html', army=army,
                                       result=result, validator=v)
            return redirect(url_for('armies.show', army_id=army_id))

    # Regiment count check (RoR counts as regiment)
    from app.services.validators.aos import AoSValidator
    if isinstance(v, AoSValidator):
        bp = AoSValidator.BATTLEPACKS.get(army.battlepack, AoSValidator.BATTLEPACKS['vanguard'])
        _, reg_max = bp['regiments']
    else:
        reg_max = 4

    if len(army.regiments) >= reg_max:
        flash(f'Máximo de {reg_max} regimentos para {army.battlepack.capitalize()}.', 'error')
        if _is_htmx():
            result = validate(army)
            return render_template('armies/_regiments_and_aux.html', army=army,
                                   result=result, validator=v)
        return redirect(url_for('armies.show', army_id=army_id))

    next_pos = max((r.position for r in army.regiments), default=0) + 1
    reg = Regiment(army_id=army.id, position=next_pos, ror_id=ror.id)
    db.session.add(reg)
    db.session.flush()

    # Populate ArmyUnit stubs for each unit string in the RoR
    # units_json is a list of strings like "3 Warpvolt Scourgers"
    import json as _json
    units_list = _json.loads(ror.units_json) if ror.units_json else []
    sort_counter = max((au.sort_order for au in army.army_units), default=0)
    first = True
    for unit_str in units_list:
        # unit_str may be "1 Warlock Galvaneer" or "3 Warpvolt Scourgers"
        # We store regiment_id but leave unit_id as a placeholder (no real Unit match needed)
        # Best-effort: try to find unit by name in any faction
        parts = unit_str.split(' ', 1)
        unit_name = parts[1] if len(parts) == 2 and parts[0].isdigit() else unit_str
        unit_count = int(parts[0]) if len(parts) == 2 and parts[0].isdigit() else 1

        unit = Unit.query.filter(Unit.name.ilike(unit_name)).first()
        if not unit:
            # Try partial match
            unit = Unit.query.filter(Unit.name.ilike(f'%{unit_name}%')).first()

        if unit:
            for _ in range(unit_count):
                sort_counter += 1
                au = ArmyUnit(
                    army_id=army.id,
                    unit_id=unit.id,
                    regiment_id=reg.id,
                    is_leader=first,  # mark first unit as "leader" for display
                    is_general=False,
                    sort_order=sort_counter,
                )
                db.session.add(au)
                first = False

    db.session.commit()

    if _is_htmx():
        result = validate(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                               validator=v) + summary
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/regiments/<int:reg_id>/remove', methods=['POST'])
@login_required
def remove_regiment(army_id, reg_id):
    army = _owned_army_or_404(army_id)
    regiment = Regiment.query.filter_by(id=reg_id, army_id=army_id).first_or_404()

    if regiment.is_ror:
        # RoR: delete all member units (fixed composition, no orphan to aux)
        for au in list(regiment.army_units):
            db.session.delete(au)
    else:
        for au in regiment.army_units:
            au.regiment_id = None
            au.is_leader = False

    db.session.delete(regiment)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        v = _army_validator(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result,
                               validator=v) + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/edit', methods=['POST'])
@login_required
def edit(army_id):
    army = _owned_army_or_404(army_id)
    name = request.form.get('name', '').strip()
    notes = request.form.get('notes', '').strip()
    if name:
        army.name = name
    army.notes = notes or None
    db.session.commit()
    flash('Exército atualizado.', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/delete', methods=['POST'])
@login_required
def delete(army_id):
    army = _owned_army_or_404(army_id)
    db.session.delete(army)
    db.session.commit()
    flash('Exército excluído.', 'success')
    return redirect(url_for('armies.index'))


@armies_bp.route('/<int:army_id>/publish', methods=['POST'])
@login_required
def publish(army_id):
    army = _owned_army_or_404(army_id)
    army.ensure_public_token()
    db.session.commit()
    share_url = url_for('armies.public_view', token=army.public_token, _external=True)
    flash(f'Exército publicado. Link para compartilhar: {share_url}', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/unpublish', methods=['POST'])
@login_required
def unpublish(army_id):
    army = _owned_army_or_404(army_id)
    army.public_token = None
    db.session.commit()
    flash('Exército despublicado.', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/p/<token>')
def public_view(token):
    army = Army.query.filter_by(public_token=token).first_or_404()
    result = validate(army)
    aux_units = [au for au in army.army_units if au.regiment_id is None]
    v = _army_validator(army)
    return render_template(
        'armies/public.html',
        army=army,
        result=result,
        aux_units=aux_units,
        validator=v,
    )


@armies_bp.route('/<int:army_id>/select-formation', methods=['POST'])
@login_required
def select_formation(army_id):
    army = _owned_army_or_404(army_id)
    name = request.form.get('formation_name', '').strip()
    if name:
        army.formation_id = name
        db.session.commit()
    faction_has_rules, faction_rules = _load_faction_rules(army)
    return render_template(
        'armies/_faction_rules.html',
        army=army,
        faction_has_rules=faction_has_rules,
        faction_rules=faction_rules,
    )


@armies_bp.route('/<int:army_id>/select-sub-faction', methods=['POST'])
@login_required
def select_sub_faction(army_id):
    army = _owned_army_or_404(army_id)
    name = request.form.get('sub_faction_name', '').strip()
    if name:
        army.sub_faction_id = name
        db.session.commit()
    faction_has_rules, faction_rules = _load_faction_rules(army)
    return render_template(
        'armies/_faction_rules.html',
        army=army,
        faction_has_rules=faction_has_rules,
        faction_rules=faction_rules,
    )


@armies_bp.route('/<int:army_id>/select-lore', methods=['POST'])
@login_required
def select_lore(army_id):
    army = _owned_army_or_404(army_id)
    lore_type = request.form.get('lore_type', '').strip()
    lore_name = request.form.get('lore_name', '').strip()
    if lore_name and lore_type in ('spell', 'prayer', 'manifestation'):
        if lore_type == 'spell':
            army.spell_lore_id = lore_name
        elif lore_type == 'prayer':
            army.prayer_lore_id = lore_name
        else:
            army.manifestation_lore_id = lore_name
        db.session.commit()
    faction_has_rules, faction_rules = _load_faction_rules(army)
    return render_template(
        'armies/_faction_rules.html',
        army=army,
        faction_has_rules=faction_has_rules,
        faction_rules=faction_rules,
    )


def _is_hero(unit):
    kws = unit.keywords_json or []
    return 'HERO' in {k.upper() for k in kws}
