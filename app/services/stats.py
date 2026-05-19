import json
from app.models.match import Match


def _determine_winner(match):
    if not match.scores_json:
        return None
    scores = json.loads(match.scores_json)
    h_vp = scores.get('host', {}).get('vp', 0)
    o_vp = scores.get('opponent', {}).get('vp', 0)
    h_cp = scores.get('host', {}).get('cp', 0)
    o_cp = scores.get('opponent', {}).get('cp', 0)
    if h_vp > o_vp:
        return 'host'
    if o_vp > h_vp:
        return 'opponent'
    if h_cp > o_cp:
        return 'host'
    if o_cp > h_cp:
        return 'opponent'
    return 'draw'


def compute_stats(user_id):
    finished = Match.query.filter(
        ((Match.host_id == user_id) | (Match.opponent_id == user_id)),
        Match.status == 'finished',
    ).order_by(Match.finished_at.desc()).all()

    total = len(finished)
    won = 0
    lost = 0
    system_stats = {}
    faction_stats = {}

    for m in finished:
        winner = _determine_winner(m)
        is_host = (m.host_id == user_id)
        user_key = 'host' if is_host else 'opponent'
        opp_key = 'opponent' if is_host else 'host'

        if winner == user_key:
            result = 'W'
            won += 1
        elif winner == opp_key:
            result = 'L'
            lost += 1
        else:
            result = 'D'

        sys_code = m.system.code if m.system else 'unknown'
        if sys_code not in system_stats:
            system_stats[sys_code] = {'name': m.system.name if m.system else sys_code, 'W': 0, 'L': 0, 'D': 0}
        system_stats[sys_code][result] += 1

        army = m.army_host if is_host else m.army_opponent
        if army and army.faction:
            fname = army.faction.name
            if fname not in faction_stats:
                faction_stats[fname] = {'W': 0, 'L': 0, 'D': 0}
            faction_stats[fname][result] += 1

    win_rate = round(won / total * 100) if total > 0 else 0

    recent_form = []
    for m in finished[:5]:
        winner = _determine_winner(m)
        is_host = (m.host_id == user_id)
        user_key = 'host' if is_host else 'opponent'
        opp_key = 'opponent' if is_host else 'host'
        if winner == user_key:
            recent_form.append('W')
        elif winner == opp_key:
            recent_form.append('L')
        else:
            recent_form.append('D')

    return {
        'total': total,
        'won': won,
        'lost': lost,
        'draws': total - won - lost,
        'win_rate': win_rate,
        'system_stats': system_stats,
        'faction_stats': faction_stats,
        'recent_form': recent_form,
    }
