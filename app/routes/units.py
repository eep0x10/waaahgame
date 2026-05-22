import os
import io
from flask import (
    Blueprint, render_template, redirect, url_for, flash, request, abort
)
from flask_login import login_required, current_user
from app.extensions import db
from app.models.game import Unit, Faction, GameSystem

units_bp = Blueprint('units', __name__, url_prefix='/units')


@units_bp.route('/')
def index():
    system_filter = request.args.get('system', '').strip()
    faction_filter = request.args.get('faction', '').strip()
    q = request.args.get('q', '').strip()
    pts_min = request.args.get('pts_min', type=int)
    pts_max = request.args.get('pts_max', type=int)
    only_incomplete = bool(request.args.get('only_incomplete', '').strip())

    unit_query = Unit.query.join(Faction).join(GameSystem)

    if system_filter:
        unit_query = unit_query.filter(GameSystem.code == system_filter)
    if faction_filter:
        unit_query = unit_query.filter(Faction.slug == faction_filter)
    if q:
        unit_query = unit_query.filter(Unit.name.ilike(f'%{q}%'))
    if pts_min is not None:
        unit_query = unit_query.filter(Unit.points_cost >= pts_min)
    if pts_max is not None:
        unit_query = unit_query.filter(Unit.points_cost <= pts_max)
    if only_incomplete:
        unit_query = unit_query.filter(Unit.unit_category == 'incomplete')

    from sqlalchemy import case
    units = unit_query.order_by(
        GameSystem.name,
        Faction.name,
        case((Unit.unit_category == 'legends', 1), else_=0),
        Unit.name,
    ).all()

    # Build grouped structure: [(system, [(faction, [units])])]
    from collections import OrderedDict
    sys_map = OrderedDict()
    for unit in units:
        gs = unit.faction.game_system
        fac = unit.faction
        if gs.id not in sys_map:
            sys_map[gs.id] = {'system': gs, 'factions': OrderedDict()}
        if fac.id not in sys_map[gs.id]['factions']:
            sys_map[gs.id]['factions'][fac.id] = {'faction': fac, 'units': []}
        sys_map[gs.id]['factions'][fac.id]['units'].append(unit)

    grouped = [
        (entry['system'], [
            (fac_entry['faction'], fac_entry['units'])
            for fac_entry in entry['factions'].values()
        ])
        for entry in sys_map.values()
    ]

    total_units = len(units)
    systems = GameSystem.query.order_by(GameSystem.name).all()
    factions = Faction.query.order_by(Faction.name).all()

    is_htmx = request.headers.get('HX-Request') == 'true'
    if is_htmx:
        return render_template('units/_unit_rows.html', grouped=grouped,
                               total_units=total_units,
                               system_filter=system_filter, faction_filter=faction_filter,
                               q=q, pts_min=pts_min, pts_max=pts_max,
                               only_incomplete=only_incomplete)

    return render_template(
        'units/index.html',
        grouped=grouped,
        total_units=total_units,
        systems=systems,
        factions=factions,
        system_filter=system_filter,
        faction_filter=faction_filter,
        q=q,
        pts_min=pts_min,
        pts_max=pts_max,
        only_incomplete=only_incomplete,
    )

ALLOWED_MIME = {'image/jpeg', 'image/png', 'image/webp'}
STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'static',
)


@units_bp.route('/<unit_slug>')
def detail(unit_slug):
    from app.services.unit_view import unit_view, current_ruleset_for_system
    from app.models.game import Ruleset

    unit = Unit.query.filter_by(slug=unit_slug).first_or_404()
    rs_code = request.args.get('ruleset')
    ruleset = None
    if rs_code:
        ruleset = Ruleset.query.filter_by(code=rs_code).first()
    if ruleset is None:
        ruleset = current_ruleset_for_system(unit.faction.game_system)
    view = unit_view(unit, ruleset)
    available_rulesets = unit.faction.game_system.rulesets if unit.faction.game_system else []
    return render_template('units/detail.html', unit=view, raw_unit=unit,
                           current_ruleset=ruleset, available_rulesets=available_rulesets)


@units_bp.route('/<unit_slug>/upload-image', methods=['GET'])
@login_required
def upload_image(unit_slug):
    if not current_user.is_admin:
        abort(403)
    unit = Unit.query.filter_by(slug=unit_slug).first_or_404()
    return render_template('units/upload.html', unit=unit)


@units_bp.route('/<unit_slug>/upload-image', methods=['POST'])
@login_required
def upload_image_post(unit_slug):
    if not current_user.is_admin:
        abort(403)
    unit = Unit.query.filter_by(slug=unit_slug).first_or_404()

    f = request.files.get('image')
    if not f or not f.filename:
        flash('Nenhum arquivo selecionado.', 'error')
        return redirect(url_for('units.upload_image', unit_slug=unit_slug))

    # Validate MIME type
    mime = f.mimetype
    if mime not in ALLOWED_MIME:
        flash('Tipo de arquivo inválido. Envie uma imagem JPEG, PNG ou WebP.', 'error')
        return redirect(url_for('units.upload_image', unit_slug=unit_slug))

    try:
        from PIL import Image
        img = Image.open(io.BytesIO(f.read())).convert('RGB')
    except Exception:
        flash('Não foi possível ler o arquivo de imagem. Envie um JPEG, PNG ou WebP válido.', 'error')
        return redirect(url_for('units.upload_image', unit_slug=unit_slug))

    max_w = 600
    if img.width > max_w:
        ratio = max_w / img.width
        img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

    faction_slug = unit.faction.slug
    dest_rel = 'units/{}/{}.jpg'.format(faction_slug, unit.slug)
    dest_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, '{}.jpg'.format(unit.slug))
    os.makedirs(os.path.dirname(dest_abs), exist_ok=True)
    img.save(dest_abs, 'JPEG', quality=85, optimize=True)

    unit.image_path = dest_rel
    unit.image_source_url = None
    unit.image_search_url = None
    db.session.commit()

    flash('Imagem de bandeira definida para {}.'.format(unit.name), 'success')
    return redirect(url_for('units.detail', unit_slug=unit_slug))
