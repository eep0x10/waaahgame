from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort, jsonify
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.army import Army, Regiment, ArmyUnit, BATTLEPACKS
from app.models.game import Faction, Unit
from app.services.validator import validate

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


@armies_bp.route('/')
@login_required
def index():
    armies = Army.query.filter_by(user_id=current_user.id).order_by(Army.created_at.desc()).all()
    results = {a.id: validate(a) for a in armies}
    return render_template('armies/index.html', armies=armies, results=results)


@armies_bp.route('/new', methods=['GET'])
@login_required
def new():
    factions = Faction.query.order_by(Faction.name).all()
    battlepacks = BATTLEPACKS
    return render_template('armies/new.html', factions=factions, battlepacks=battlepacks)


@armies_bp.route('/new', methods=['POST'])
@login_required
def new_post():
    name = request.form.get('name', '').strip()
    faction_id = request.form.get('faction_id', type=int)
    battlepack = request.form.get('battlepack', 'vanguard')

    if not name or not faction_id:
        flash('Name and faction are required.', 'error')
        return redirect(url_for('armies.new'))

    if battlepack not in BATTLEPACKS:
        battlepack = 'vanguard'

    faction = db.session.get(Faction, faction_id)
    if not faction:
        abort(400)

    pts_limit = BATTLEPACKS[battlepack]['pts']

    army = Army(
        user_id=current_user.id,
        faction_id=faction_id,
        name=name,
        battlepack=battlepack,
        points_limit=pts_limit,
    )
    db.session.add(army)
    db.session.flush()

    reg1 = Regiment(army_id=army.id, position=1)
    db.session.add(reg1)
    db.session.commit()

    return redirect(url_for('armies.show', army_id=army.id))


@armies_bp.route('/<int:army_id>', methods=['GET'])
@login_required
def show(army_id):
    army = _owned_army_or_404(army_id)
    units = sorted(army.faction.units, key=lambda u: (u.unit_role or 'zz', u.name))
    aux_units = [au for au in army.army_units if au.regiment_id is None]
    result = validate(army)
    return render_template(
        'armies/show.html',
        army=army,
        units=units,
        aux_units=aux_units,
        result=result,
        battlepacks=BATTLEPACKS,
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
        summary = _summary_html(army)
        if regiment:
            regiment = db.session.get(Regiment, regiment.id)
            partial = render_template('armies/_regiment.html', regiment=regiment, army=army, result=result)
        else:
            aux_units = [a for a in army.army_units if a.regiment_id is None]
            partial = render_template('armies/_auxiliary.html', army=army, aux_units=aux_units, result=result)
        return partial + summary
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/move', methods=['POST'])
@login_required
def move_unit(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()
    target = request.form.get('target', 'aux').strip()

    old_regiment_id = au.regiment_id

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
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result) + summary

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
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result) + summary

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
        summary = _summary_html(army)
        row = render_template('armies/_army_unit_row.html', au=au, army=army, result=result)
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
        summary = _summary_html(army)
        partial = render_template('armies/_regiment.html', regiment=regiment, army=army, result=result)
        return partial + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/units/<int:au_id>/set-general', methods=['POST'])
@login_required
def set_general(army_id, au_id):
    army = _owned_army_or_404(army_id)
    au = ArmyUnit.query.filter_by(id=au_id, army_id=army_id).first_or_404()

    for other in army.army_units:
        other.is_general = False
    au.is_general = True
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        return _summary_html(army)

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/regiments', methods=['POST'])
@login_required
def add_regiment(army_id):
    army = _owned_army_or_404(army_id)
    bp = BATTLEPACKS.get(army.battlepack, BATTLEPACKS['vanguard'])
    _, reg_max = bp['regiments']

    if len(army.regiments) >= reg_max:
        flash(f'Maximum {reg_max} regiments for {army.battlepack.capitalize()}.', 'error')
        if _is_htmx():
            result = validate(army)
            return render_template('armies/_regiments_and_aux.html', army=army, result=result)
        return redirect(url_for('armies.show', army_id=army_id))

    next_pos = max((r.position for r in army.regiments), default=0) + 1
    reg = Regiment(army_id=army.id, position=next_pos)
    db.session.add(reg)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result) + summary

    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/regiments/<int:reg_id>/remove', methods=['POST'])
@login_required
def remove_regiment(army_id, reg_id):
    army = _owned_army_or_404(army_id)
    regiment = Regiment.query.filter_by(id=reg_id, army_id=army_id).first_or_404()

    for au in regiment.army_units:
        au.regiment_id = None
        au.is_leader = False

    db.session.delete(regiment)
    db.session.commit()

    if _is_htmx():
        result = validate(army)
        summary = _summary_html(army)
        return render_template('armies/_regiments_and_aux.html', army=army, result=result) + summary

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
    flash('Army updated.', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/delete', methods=['POST'])
@login_required
def delete(army_id):
    army = _owned_army_or_404(army_id)
    db.session.delete(army)
    db.session.commit()
    flash('Army deleted.', 'success')
    return redirect(url_for('armies.index'))


@armies_bp.route('/<int:army_id>/publish', methods=['POST'])
@login_required
def publish(army_id):
    army = _owned_army_or_404(army_id)
    army.ensure_public_token()
    db.session.commit()
    share_url = url_for('armies.public_view', token=army.public_token, _external=True)
    flash(f'Army published. Share link: {share_url}', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/<int:army_id>/unpublish', methods=['POST'])
@login_required
def unpublish(army_id):
    army = _owned_army_or_404(army_id)
    army.public_token = None
    db.session.commit()
    flash('Army unpublished.', 'success')
    return redirect(url_for('armies.show', army_id=army_id))


@armies_bp.route('/p/<token>')
def public_view(token):
    army = Army.query.filter_by(public_token=token).first_or_404()
    result = validate(army)
    aux_units = [au for au in army.army_units if au.regiment_id is None]
    return render_template(
        'armies/public.html',
        army=army,
        result=result,
        aux_units=aux_units,
    )


def _is_hero(unit):
    kws = unit.keywords_json or []
    return 'HERO' in {k.upper() for k in kws}
