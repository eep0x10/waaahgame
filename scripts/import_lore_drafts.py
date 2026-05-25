"""Import PT-BR lore drafts produced by background agents.

Each draft file is JSON: {"faction_slug": "...", "lores": {"unit-slug": "lore markdown", ...}}

Usage (inside container):
    python scripts/import_lore_drafts.py scripts/lore_drafts/skaven.json
or all:
    python scripts/import_lore_drafts.py scripts/lore_drafts/*.json
"""
import sys, json, glob
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import create_app, db
from app.models import Unit, Faction

def import_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    faction_slug = data['faction_slug']
    lores = data['lores']
    faction = db.session.query(Faction).filter_by(slug=faction_slug).first()
    if not faction:
        print(f'  ERROR: faction {faction_slug} not found')
        return 0, 0
    updated = missing = 0
    for unit_slug, lore_md in lores.items():
        if isinstance(lore_md, dict):
            lore_md = lore_md.get('lore_pt_md') or lore_md.get('lore') or ''
        if not lore_md or not lore_md.strip():
            continue
        u = db.session.query(Unit).filter_by(slug=unit_slug, faction_id=faction.id).first()
        if not u:
            print(f'  miss: {unit_slug}')
            missing += 1
            continue
        u.lore_pt_md = lore_md.strip()
        updated += 1
    db.session.commit()
    return updated, missing

def main():
    args = sys.argv[1:]
    if not args:
        print('usage: import_lore_drafts.py <file.json> [<file.json>...]')
        sys.exit(1)
    paths = []
    for a in args:
        paths.extend(glob.glob(a) if '*' in a else [a])
    app = create_app()
    with app.app_context():
        total_u = total_m = 0
        for p in paths:
            print(f'==> {p}')
            u, m = import_file(p)
            print(f'  updated={u} missing={m}')
            total_u += u
            total_m += m
        print(f'\nTOTAL updated={total_u} missing={total_m}')

if __name__ == '__main__':
    main()
