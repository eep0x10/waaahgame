"""Seed Rulesets from existing GameSystems. Idempotent."""
import sys
from pathlib import Path
_REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_REPO_ROOT))

from app import create_app
from app.extensions import db
from app.models.game import GameSystem, Ruleset
from app.models.army import Army
from datetime import date

_RELEASE_DATES = {
    'aos4': date(2024, 7, 1),
    'w40k10': date(2023, 6, 1),
}

app = create_app()

with app.app_context():
    for gs in GameSystem.query.all():
        code = f"{gs.code}_current"
        existing = Ruleset.query.filter_by(code=code).first()
        if existing:
            print(f'[SKIP ] Ruleset already exists: {code}')
            continue
        rs = Ruleset(
            game_system_id=gs.id,
            code=code,
            name=gs.ruleset_label,
            edition=gs.edition,
            release_date=_RELEASE_DATES.get(gs.code),
            is_current=True,
        )
        db.session.add(rs)
        db.session.flush()
        print(f'[SAVE ] Ruleset created: {code} — {rs.name}')

    db.session.commit()
    print('[INFO ] Rulesets committed.')

    # Backfill armies without ruleset_id
    armies = Army.query.filter(Army.ruleset_id.is_(None)).all()
    print(f'[INFO ] Backfilling {len(armies)} armies...')
    for army in armies:
        try:
            gs = army.faction.game_system
        except Exception:
            print(f'[SKIP ] Army {army.id} has no game_system, skipping.')
            continue
        if gs is None:
            print(f'[SKIP ] Army {army.id} faction has no game_system.')
            continue
        rs = next((r for r in gs.rulesets if r.is_current), None) or (gs.rulesets[0] if gs.rulesets else None)
        if rs is None:
            print(f'[SKIP ] No ruleset found for system {gs.code}.')
            continue
        army.ruleset_id = rs.id
        print(f'[SAVE ] Army {army.id} ({army.name}) -> ruleset {rs.code}')

    db.session.commit()
    print('[INFO ] Army backfill committed.')
