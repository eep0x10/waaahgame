#!/usr/bin/env python3
"""Stage 6: Analyze AoS extras, find all singular/plural duplicate pairs."""
import sqlite3, json, os

with open('/app/scripts/cache/canonical_aos_verified.json') as f:
    canonical_data = json.load(f)

canonical_slugs = set()
for faction_key, faction_val in canonical_data.items():
    for u in faction_val['units']:
        canonical_slugs.add(u['slug'])

db = sqlite3.connect('/app/instance/waaahgame.db')
c = db.cursor()

c.execute('''SELECT u.id, u.slug, u.name, f.slug as faction_slug, u.image_path, u.faction_id
             FROM units u JOIN factions f ON u.faction_id=f.id
             JOIN game_systems gs ON f.game_system_id=gs.id
             WHERE gs.code='aos4' ORDER BY u.slug''')
aos_units = c.fetchall()

extras = [(uid, slug, name, fslu, img, fid) for uid, slug, name, fslu, img, fid in aos_units if slug not in canonical_slugs]

# Build aos slug->id map
aos_db = {row[1]: row[0] for row in aos_units}

# Find pairs: extra singular -> canonical plural already in DB
pairs = []
no_pair = []

for uid, slug, name, fslu, img, fid in extras:
    parts = slug.split('-')
    candidates = [slug+'s', slug+'es']
    if len(parts) > 1:
        # sisters-of-slaughter from sister-of-slaughter (add s to first word)
        candidates.append(parts[0]+'s'+'-'+'-'.join(parts[1:]))
        candidates.append(parts[0]+'es'+'-'+'-'.join(parts[1:]))
        # witch-aelves from witch-aelf (last word f->ves)
        if parts[-1].endswith('lf'):
            candidates.append('-'.join(parts[:-1]+[parts[-1][:-2]+'lves']))
        if parts[-1].endswith('f') and not parts[-1].endswith('lf'):
            candidates.append('-'.join(parts[:-1]+[parts[-1][:-1]+'ves']))
        # last word +s or +es
        candidates.append('-'.join(parts[:-1]+[parts[-1]+'s']))
        candidates.append('-'.join(parts[:-1]+[parts[-1]+'es']))

    matched = None
    for cand in candidates:
        if cand in canonical_slugs and cand in aos_db:
            matched = (cand, aos_db[cand])
            break

    if matched:
        c.execute('SELECT image_path FROM units WHERE id=?', (matched[1],))
        cand_img = c.fetchone()[0]
        pairs.append({
            'singular_id': uid, 'singular_slug': slug, 'name': name,
            'faction': fslu, 'singular_img': img, 'faction_id': fid,
            'plural_slug': matched[0], 'plural_id': matched[1], 'plural_img': cand_img
        })
    else:
        no_pair.append((uid, slug, name, fslu, img))

print(f"Total AoS extras: {len(extras)}")
print(f"Singular-of-canonical-plural pairs: {len(pairs)}")
for p in pairs:
    si = bool(p['singular_img'])
    pi = bool(p['plural_img'])
    print(f"  [{p['singular_id']}] {p['singular_slug']} img={si} -> [{p['plural_id']}] {p['plural_slug']} img={pi}")

print(f"\nExtras with no plural match: {len(no_pair)}")
for uid, slug, name, fslu, img in sorted(no_pair, key=lambda x: x[3]):
    print(f"  [{uid}] {slug} ({name}) faction={fslu} img={bool(img)}")

db.close()
