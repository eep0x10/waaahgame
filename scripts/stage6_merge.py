#!/usr/bin/env python3
"""Stage 6 merge: handle duplicate old-slug vs canonical-slug pairs.

Category A: old has image, canonical does NOT -> copy image path to canonical, delete old
Category B: both have images, canonical is authoritative -> just delete old (no img transfer)
"""
import sqlite3, os, shutil

db = sqlite3.connect('/app/instance/waaahgame.db')
c = db.cursor()

STATIC = '/app/app/static/img/units'

# (old_slug, canonical_slug, category)
CASES = [
    # +s / +es found by script
    ('dire-wolf',          'dire-wolves',          'A'),
    ('flamer-of-tzeentch', 'flamers-of-tzeentch',  'A'),
    ('pox-wretch',         'pox-wretches',          'A'),
    ('screamer-of-tzeentch','screamers-of-tzeentch','A'),
    ('sister-of-slaughter','sisters-of-slaughter',  'A'),
    ('witch-aelf',         'witch-aelves',          'A'),
    # Slaanesh / Tzeentch daemons with faction suffix in old slug
    ('pink-horror-of-tzeentch',  'pink-horrors',    'A'),
    ('daemonette-of-slaanesh',   'daemonettes',     'A'),
    ('fiend-of-slaanesh',        'fiends',          'A'),
    ('seeker-of-slaanesh',       'seekers',         'A'),
    ('hellstrider-of-slaanesh',  'hellstriders',    'A'),
    # Nurgle: both have images, canonical is authoritative
    ('plague-drone-of-nurgle',   'plague-drones',   'B'),
    ('plaguebearer-of-nurgle',   'plaguebearers',   'B'),
    # Fyreslayers: generic vs specific loadout
    ('hearthguard-berzerker',    'hearthguard-berzerkers-with-flamestrike-poleaxes', 'A'),
    ('vulkite-berzerker',        'vulkite-berzerkers-with-fyresteel-weapons',         'A'),
    # Stormcast: generic vs specific loadout
    ('concussor',       'dracothian-guard-concussors',                'A'),
    ('judicator',       'judicators-with-boltstorm-crossbows',        'A'),
    ('vanguard-pallador','vanguard-palladors-with-starstrike-javelins','A'),
    # vanguard-raptor: canonical longstrike already has image
    ('vanguard-raptor', 'vanguard-raptors-with-longstrike-crossbows', 'B'),
    # Gloomspite
    ('boingrot-bounder','boingrot-bounderz', 'A'),
]

merged = 0
errors = []

for old_slug, can_slug, cat in CASES:
    c.execute('SELECT id, image_path, faction_id FROM units WHERE slug=?', (old_slug,))
    old = c.fetchone()
    if not old:
        print(f'SKIP (not in DB): {old_slug}')
        continue

    old_id, old_img, old_fid = old

    c.execute('SELECT id, image_path, faction_id FROM units WHERE slug=?', (can_slug,))
    can = c.fetchone()
    if not can:
        print(f'SKIP (canonical not in DB): {can_slug} <- would have used {old_slug}')
        continue

    can_id, can_img, can_fid = can

    # Check army refs (safety)
    c.execute('SELECT COUNT(*) FROM army_units WHERE unit_id=?', (old_id,))
    refs = c.fetchone()[0]
    if refs > 0:
        errors.append(f'SKIP {old_slug} id={old_id}: has {refs} army_units refs, manual action needed')
        continue

    if cat == 'A':
        # Transfer image from old to canonical
        if old_img:
            # Determine new image path: same filename, but under canonical faction slug
            c.execute('SELECT slug FROM factions WHERE id=?', (can_fid,))
            can_faction = c.fetchone()[0]
            ext = os.path.splitext(old_img)[1]
            new_img = f'units/{can_faction}/{can_slug}{ext}'
            src = os.path.join(STATIC, can_faction.replace('/', os.sep), f'{old_slug}{ext}')
            # Actually old img path stored as units/<old_faction>/<old_slug>.ext
            # Source is the old file
            old_parts = old_img.replace('\\', '/').split('/')
            src_path = os.path.join(STATIC, *old_parts[1:])  # skip 'units/'
            dst_dir = os.path.join(STATIC, can_faction)
            dst_path = os.path.join(dst_dir, f'{can_slug}{ext}')

            if os.path.exists(src_path):
                os.makedirs(dst_dir, exist_ok=True)
                if not os.path.exists(dst_path):
                    shutil.copy2(src_path, dst_path)
                    print(f'  COPY: {src_path} -> {dst_path}')
                else:
                    print(f'  SKIP COPY (exists): {dst_path}')
                # Update canonical row
                c.execute('UPDATE units SET image_path=? WHERE id=?', (new_img, can_id))
                print(f'  SET image on [{can_id}] {can_slug} = {new_img}')
            else:
                print(f'  WARN: image file not found: {src_path} -- updating path anyway if old_img set')
                # Update canonical with old img path since file may still be usable
                c.execute('UPDATE units SET image_path=? WHERE id=?', (old_img, can_id))

    # Delete old row
    c.execute('DELETE FROM units WHERE id=?', (old_id,))
    print(f'[{cat}] DELETE [{old_id}] {old_slug}  |  canonical=[{can_id}] {can_slug}')
    merged += 1

db.commit()
print(f'\nMerged {merged} pairs. Errors: {len(errors)}')
for e in errors:
    print(f'  {e}')
db.close()
