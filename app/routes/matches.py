import json
import re
import random
from datetime import datetime, timezone
from flask import Blueprint, render_template, redirect, url_for, flash, request, abort
from flask_login import login_required, current_user
from app.extensions import db, socketio
from app.models.match import Match, PHASES, FORMAT_POINTS
from app.services.formats import all_formats as _all_formats, SYSTEM_FORMATS
from app.models.match_event import MatchEvent
from app.models.match_casualty import MatchCasualty
from app.models.match_dice_roll import MatchDiceRoll
from app.models.match_message import MatchMessage
from app.models.friendship import Friendship
from app.models.army import Army
from app.models.game import GameSystem

_DICE_RE = re.compile(r'^(\d+)d(\d+)([+-]\d+)?$')
_RNG = random.SystemRandom()

matches_bp = Blueprint('matches', __name__, url_prefix='/matches')


def _is_htmx():
    return request.headers.get('HX-Request') == 'true'


def _get_match_or_404(match_id):
    m = db.session.get(Match, match_id)
    if m is None:
        abort(404)
    return m


def _require_participant(match):
    if not match.is_participant(current_user):
        abort(403)


def _emit(event, match_id, payload=None):
    socketio.emit(event, payload or {'refresh': True}, room=f'match-{match_id}')


def _log_event(match, kind, payload=None):
    ev = MatchEvent(
        match_id=match.id,
        round=match.current_round,
        phase=match.current_phase,
        actor_id=current_user.id,
        kind=kind,
        payload_json=json.dumps(payload) if payload else None,
    )
    db.session.add(ev)


def _is_accepted_friend(user_a_id, user_b_id):
    fs = Friendship.query.filter(
        ((Friendship.requester_id == user_a_id) & (Friendship.addressee_id == user_b_id)) |
        ((Friendship.requester_id == user_b_id) & (Friendship.addressee_id == user_a_id))
    ).first()
    return fs is not None and fs.status == 'accepted'


@matches_bp.route('/')
@login_required
def index():
    invites = Match.query.filter_by(opponent_id=current_user.id, status='pending').all()
    active = Match.query.filter(
        ((Match.host_id == current_user.id) | (Match.opponent_id == current_user.id)),
        Match.status.in_(['army_select', 'active'])
    ).order_by(Match.created_at.desc()).all()
    finished = Match.query.filter(
        ((Match.host_id == current_user.id) | (Match.opponent_id == current_user.id)),
        Match.status.in_(['finished', 'cancelled'])
    ).order_by(Match.finished_at.desc().nullslast()).limit(10).all()
    return render_template('matches/index.html', invites=invites, active=active, finished=finished)


@matches_bp.route('/new', methods=['GET'])
@login_required
def new():
    systems = GameSystem.query.order_by(GameSystem.name).all()
    my_armies = Army.query.filter_by(user_id=current_user.id).order_by(Army.name).all()
    # Combine all formats for template; system_formats passed for JS filtering
    combined_format_points = _all_formats()
    formats = list(combined_format_points.keys())
    return render_template('matches/new.html', systems=systems, my_armies=my_armies, formats=formats,
                           FORMAT_POINTS=combined_format_points, system_formats=SYSTEM_FORMATS)


@matches_bp.route('/new', methods=['POST'])
@login_required
def new_post():
    opponent_id = request.form.get('opponent_id', type=int)
    system_id = request.form.get('system_id', type=int)
    fmt = request.form.get('format', 'vanguard').strip()
    army_host_id = request.form.get('army_host_id', type=int)

    if not opponent_id or not system_id or not army_host_id:
        flash('All fields are required.', 'error')
        return redirect(url_for('matches.new'))

    if opponent_id == current_user.id:
        flash('You cannot challenge yourself.', 'error')
        return redirect(url_for('matches.new'))

    if not _is_accepted_friend(current_user.id, opponent_id):
        flash('You can only challenge accepted friends.', 'error')
        return redirect(url_for('matches.new'))

    army = db.session.get(Army, army_host_id)
    if army is None or army.user_id != current_user.id:
        abort(403)

    # Accept both AoS and 40k formats
    combined_fp = _all_formats()
    pts = combined_fp.get(fmt) or FORMAT_POINTS.get(fmt)
    if pts is None:
        flash('Invalid format.', 'error')
        return redirect(url_for('matches.new'))

    if army.points_limit < pts:
        flash(f'Army points limit ({army.points_limit}) is below format limit ({pts}).', 'error')
        return redirect(url_for('matches.new'))

    system = db.session.get(GameSystem, system_id)
    if system is None:
        abort(400)

    match = Match(
        host_id=current_user.id,
        opponent_id=opponent_id,
        system_id=system_id,
        format=fmt,
        points_limit=pts,
        army_host_id=army_host_id,
        status='pending',
    )
    db.session.add(match)
    db.session.commit()
    return redirect(url_for('matches.show', match_id=match.id))


@matches_bp.route('/<int:match_id>/accept', methods=['POST'])
@login_required
def accept(match_id):
    match = _get_match_or_404(match_id)
    if match.opponent_id != current_user.id or match.status != 'pending':
        abort(403)
    match.status = 'army_select'
    db.session.commit()
    flash('Challenge accepted. Choose your army.', 'success')
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/decline', methods=['POST'])
@login_required
def decline(match_id):
    match = _get_match_or_404(match_id)
    if match.opponent_id != current_user.id or match.status != 'pending':
        abort(403)
    match.status = 'cancelled'
    db.session.commit()
    flash('Challenge declined.', 'success')
    return redirect(url_for('matches.index'))


@matches_bp.route('/<int:match_id>/cancel', methods=['POST'])
@login_required
def cancel(match_id):
    match = _get_match_or_404(match_id)
    if match.host_id != current_user.id or match.status not in ('pending', 'army_select'):
        abort(403)
    match.status = 'cancelled'
    db.session.commit()
    flash('Match cancelled.', 'success')
    return redirect(url_for('matches.index'))


@matches_bp.route('/<int:match_id>/choose-army', methods=['POST'])
@login_required
def choose_army(match_id):
    match = _get_match_or_404(match_id)
    if match.opponent_id != current_user.id or match.status != 'army_select':
        abort(403)
    army_id = request.form.get('army_opponent_id', type=int)
    if not army_id:
        flash('Select an army.', 'error')
        return redirect(url_for('matches.show', match_id=match_id))
    army = db.session.get(Army, army_id)
    if army is None or army.user_id != current_user.id:
        abort(403)
    if army.points_limit < match.points_limit:
        flash('Army points limit is below match limit.', 'error')
        return redirect(url_for('matches.show', match_id=match_id))
    match.army_opponent_id = army_id
    db.session.commit()
    flash('Army chosen!', 'success')
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/start', methods=['POST'])
@login_required
def start(match_id):
    match = _get_match_or_404(match_id)
    if match.host_id != current_user.id or match.status != 'army_select':
        abort(403)
    if not match.army_host_id or not match.army_opponent_id:
        flash('Both players must choose an army first.', 'error')
        return redirect(url_for('matches.show', match_id=match_id))
    match.status = 'active'
    match.current_round = 1
    match.current_phase = 'hero'
    match.active_player_id = match.host_id
    match.started_at = datetime.now(timezone.utc)
    match.scores_json = json.dumps({
        'host': {'vp': 0, 'cp': 1, 'turns': []},
        'opponent': {'vp': 0, 'cp': 0, 'turns': []},
    })
    _log_event(match, 'match_start')
    db.session.commit()
    _emit('phase_changed', match.id)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>')
@login_required
def show(match_id):
    match = _get_match_or_404(match_id)
    if not match.is_participant(current_user):
        return redirect(url_for('matches.public_view', token=match.public_token))
    recent_events = match.events[-20:] if match.events else []
    host_army = match.army_host
    opp_army = match.army_opponent
    scores = match.get_scores() if match.scores_json else {'host': {'vp': 0, 'cp': 0}, 'opponent': {'vp': 0, 'cp': 0}}
    return render_template('matches/show.html', match=match, recent_events=recent_events,
                           host_army=host_army, opp_army=opp_army, scores=scores,
                           PHASES=PHASES)


@matches_bp.route('/<int:match_id>/advance-phase', methods=['POST'])
@login_required
def advance_phase(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'active':
        abort(403)
    if match.active_player_id != current_user.id and match.host_id != current_user.id:
        abort(403)

    phases = list(PHASES)
    current = match.current_phase
    if current not in phases:
        current = phases[0]
    idx = phases.index(current)

    if idx < len(phases) - 1:
        match.current_phase = phases[idx + 1]
    else:
        # end of this player's turn
        scores = match.get_scores()
        other = match.other_player(current_user)
        other_key = 'opponent' if current_user.id == match.host_id else 'host'

        if match.active_player_id == match.host_id:
            # host just finished, switch to opponent
            match.active_player_id = match.opponent_id
            match.current_phase = phases[0]
            # give opponent cp
            scores[other_key]['cp'] = scores[other_key].get('cp', 0) + 1
            match.scores_json = json.dumps(scores)
        else:
            # opponent just finished — round ends
            if match.current_round >= 5:
                match.status = 'finished'
                match.finished_at = datetime.now(timezone.utc)
                _log_event(match, 'match_finish')
                db.session.commit()
                _emit('match_finished', match.id)
                if _is_htmx():
                    return render_template('matches/_phase_header.html', match=match, PHASES=PHASES)
                return redirect(url_for('matches.show', match_id=match_id))
            else:
                match.current_round += 1
                match.active_player_id = match.host_id
                match.current_phase = phases[0]
                scores['host']['cp'] = scores['host'].get('cp', 0) + 1
                match.scores_json = json.dumps(scores)

    _log_event(match, 'phase_advance', {'phase': match.current_phase, 'round': match.current_round})
    db.session.commit()
    _emit('phase_changed', match.id)

    if _is_htmx():
        return render_template('matches/_phase_header.html', match=match, PHASES=PHASES)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/score', methods=['POST'])
@login_required
def score(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'active':
        abort(403)

    vp_delta = request.form.get('vp', type=int, default=0)
    cp_delta = request.form.get('cp', type=int, default=0)

    scores = match.get_scores()
    key = 'host' if current_user.id == match.host_id else 'opponent'
    scores[key]['vp'] = max(0, scores[key].get('vp', 0) + vp_delta)
    scores[key]['cp'] = max(0, scores[key].get('cp', 0) + cp_delta)
    match.scores_json = json.dumps(scores)

    _log_event(match, 'score_change', {'vp_delta': vp_delta, 'cp_delta': cp_delta})
    db.session.commit()
    _emit('score_updated', match.id)

    if _is_htmx():
        return render_template('matches/_score_panel.html', match=match, scores=scores)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/casualty', methods=['POST'])
@login_required
def casualty(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'active':
        abort(403)

    au_id = request.form.get('army_unit_id', type=int)
    if not au_id:
        abort(400)

    existing = MatchCasualty.query.filter_by(match_id=match_id, army_unit_id=au_id).first()
    if existing:
        existing.removed = not existing.removed
    else:
        existing = MatchCasualty(
            match_id=match_id,
            army_unit_id=au_id,
            round=match.current_round,
            removed=True,
        )
        db.session.add(existing)

    _log_event(match, 'casualty', {'army_unit_id': au_id, 'removed': existing.removed})
    db.session.commit()
    _emit('casualty_changed', match.id)

    if _is_htmx():
        casualties = {c.army_unit_id: c for c in match.casualties}
        return render_template('matches/_casualty_row.html', au=existing.army_unit,
                               match=match, casualties=casualties)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/finish', methods=['POST'])
@login_required
def finish(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'active':
        abort(403)
    if match.host_id != current_user.id and match.active_player_id != current_user.id:
        abort(403)
    match.status = 'finished'
    match.finished_at = datetime.now(timezone.utc)
    _log_event(match, 'match_finish')
    db.session.commit()
    _emit('match_finished', match.id)
    flash('Match finished!', 'success')
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/state')
@login_required
def state(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    scores = match.get_scores() if match.scores_json else {'host': {'vp': 0, 'cp': 0}, 'opponent': {'vp': 0, 'cp': 0}}
    recent_events = match.events[-20:] if match.events else []
    casualties = {c.army_unit_id: c for c in match.casualties}
    return render_template('matches/_state.html', match=match, scores=scores,
                           recent_events=recent_events, casualties=casualties, PHASES=PHASES)


@matches_bp.route('/<int:match_id>/roll', methods=['POST'])
@login_required
def roll(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'active':
        abort(403)

    formula = (request.form.get('formula') or '').strip().lower()
    m = _DICE_RE.match(formula)
    if not m:
        abort(400)

    n_dice = int(m.group(1))
    sides = int(m.group(2))
    modifier_str = m.group(3) or '+0'
    modifier = int(modifier_str)

    if n_dice < 1 or n_dice > 50 or sides < 2 or sides > 100:
        abort(400)

    results = [_RNG.randint(1, sides) for _ in range(n_dice)]
    total = sum(results) + modifier

    roll_obj = MatchDiceRoll(
        match_id=match_id,
        actor_id=current_user.id,
        round=match.current_round,
        phase=match.current_phase,
        formula=formula,
        results_json=json.dumps(results),
        total=total,
    )
    db.session.add(roll_obj)
    db.session.commit()

    socketio.emit('dice_rolled', {'roll_id': roll_obj.id}, room=f'match-{match_id}')

    recent_rolls = MatchDiceRoll.query.filter_by(match_id=match_id).order_by(
        MatchDiceRoll.created_at.desc()).limit(10).all()

    if _is_htmx():
        return render_template('matches/_dice_panel.html', match=match, recent_rolls=recent_rolls)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/message', methods=['POST'])
@login_required
def message(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)

    body = (request.form.get('body') or '').strip()[:500]
    if not body:
        abort(400)

    msg = MatchMessage(
        match_id=match_id,
        actor_id=current_user.id,
        body=body,
    )
    db.session.add(msg)
    db.session.commit()

    socketio.emit('message_posted', {'message_id': msg.id}, room=f'match-{match_id}')

    recent_messages = MatchMessage.query.filter_by(match_id=match_id).order_by(
        MatchMessage.created_at.asc()).all()

    if _is_htmx():
        return render_template('matches/_chat_panel.html', match=match, messages=recent_messages)
    return redirect(url_for('matches.show', match_id=match_id))


@matches_bp.route('/<int:match_id>/replay')
@login_required
def replay(match_id):
    match = _get_match_or_404(match_id)
    _require_participant(match)
    if match.status != 'finished':
        abort(403)
    scores = match.get_scores() if match.scores_json else {'host': {'vp': 0, 'cp': 0}, 'opponent': {'vp': 0, 'cp': 0}}
    return render_template('matches/replay.html', match=match, scores=scores, PHASES=PHASES)


@matches_bp.route('/m/<token>/replay')
def public_replay(token):
    match = Match.query.filter_by(public_token=token).first_or_404()
    if match.status != 'finished':
        abort(403)
    scores = match.get_scores() if match.scores_json else {'host': {'vp': 0, 'cp': 0}, 'opponent': {'vp': 0, 'cp': 0}}
    return render_template('matches/replay.html', match=match, scores=scores, PHASES=PHASES)


@matches_bp.route('/m/<token>')
def public_view(token):
    match = Match.query.filter_by(public_token=token).first_or_404()
    scores = match.get_scores() if match.scores_json else {'host': {'vp': 0, 'cp': 0}, 'opponent': {'vp': 0, 'cp': 0}}
    recent_events = match.events[-20:] if match.events else []
    return render_template('matches/public.html', match=match, scores=scores,
                           recent_events=recent_events, PHASES=PHASES)
