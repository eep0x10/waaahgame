import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from datetime import date
from app import create_app
from app.extensions import db
from app.models.game import GameSystem, Ruleset, Unit, UnitVersion


def run():
    app = create_app()
    with app.app_context():
        gs = GameSystem.query.filter_by(code='aos4').first()
        if gs is None:
            print('[ERROR] GameSystem aos4 não existe'); return

        # 1. Historical ruleset
        rs = Ruleset.query.filter_by(code='aos4_ghb2024_25').first()
        if rs is None:
            rs = Ruleset(
                game_system_id=gs.id,
                code='aos4_ghb2024_25',
                name='GHB 2024-25 (launch)',
                edition='4th Edition (Skaventide 2024)',
                release_date=date(2024, 7, 6),
                is_current=False,
                notes='Initial AoS4 launch — pre-April 2026 Battlescroll',
                source_url='https://www.warhammer-community.com/2024/07/'
            )
            db.session.add(rs)
            db.session.flush()
            print(f'[SAVE ] Ruleset aos4_ghb2024_25 criado id={rs.id}')
        else:
            print(f'[SKIP ] Ruleset aos4_ghb2024_25 já existe id={rs.id}')

        # 2. UnitVersion overrides — historical (GHB 2024-25 launch) absolute points
        # Format: (slug, historical_pts_absolute, notes_dict)
        # Valores fictícios-plausíveis demonstrando mecanismo; substituir por dados reais
        HISTORICAL = [
            ('clanrat',              100, {'points': 'launch 100'}),
            ('stormvermin',          140, {'points': 'launch 140'}),
            ('clawlord',             115, {'points': 'launch 115'}),
            ('grey-seer',            130, {'points': 'launch 130'}),
            ('warlock-engineer',     110, {'points': 'launch 110'}),
            ('warlock-bombardier',   100, {'points': 'launch 100'}),
            ('plague-priest',         90, {'points': 'launch 90'}),
            ('hell-pit-abomination', 240, {'points': 'launch 240'}),
        ]

        created = skipped = missing = 0
        for slug, hist_pts, notes in HISTORICAL:
            unit = Unit.query.filter_by(slug=slug).first()
            if unit is None:
                print(f'[WARN ] unit {slug!r} não existe'); missing += 1; continue
            existing = UnitVersion.query.filter_by(unit_id=unit.id, ruleset_id=rs.id).first()
            if existing:
                print(f'[SKIP ] UnitVersion {slug} já existe (pts={existing.points_cost})'); skipped += 1; continue
            uv = UnitVersion(
                unit_id=unit.id,
                ruleset_id=rs.id,
                points_cost=hist_pts,
                notes_json=notes,
            )
            db.session.add(uv)
            print(f'[SAVE ] UnitVersion {slug}: base={unit.points_cost} → historical={hist_pts}')
            created += 1

        db.session.commit()
        print(f'\nCreated: {created}  Skipped: {skipped}  Missing: {missing}')


if __name__ == '__main__':
    run()
