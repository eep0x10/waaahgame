#!/usr/bin/env python3
"""Stage 7: Populate Sons of Behemat and Helsmiths of Hashut from BSData."""
import sqlite3, json, re, unicodedata

db = sqlite3.connect('/app/instance/waaahgame.db')
c = db.cursor()

with open('/app/scripts/cache/bsdata_aos.json') as f:
    bsdata = json.load(f)


def slugify(name):
    """Convert unit name to slug."""
    s = name.lower()
    # Remove apostrophes/special chars
    s = s.replace("'", '').replace("'", '').replace('"', '')
    # Replace non-alphanumeric with dash
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def insert_units(faction_slug, bsdata_key):
    c.execute('SELECT id FROM factions WHERE slug=?', (faction_slug,))
    frow = c.fetchone()
    if not frow:
        print(f'FACTION NOT FOUND: {faction_slug}')
        return 0
    fid = frow[0]

    units = bsdata.get(bsdata_key, [])
    if not units:
        print(f'{faction_slug}: no units in BSData key {bsdata_key}')
        return 0

    inserted = 0
    skipped = 0
    for name in units:
        slug = slugify(name)
        # Check if slug already exists
        c.execute('SELECT id, faction_id FROM units WHERE slug=?', (slug,))
        existing = c.fetchone()
        if existing:
            skipped += 1
            print(f'  SKIP (exists): {slug} (id={existing[0]})')
            continue
        try:
            c.execute('''INSERT INTO units (faction_id, slug, name, points_cost, model_count,
                                           stats_json, weapons_json, abilities_json, keywords_json, companions_json,
                                           image_path, created_at, updated_at)
                         VALUES (?, ?, ?, 0, 1, '{}', '[]', '[]', '[]', '[]', NULL, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP)''',
                      (fid, slug, name))
            inserted += 1
            print(f'  INSERT: {slug} ({name})')
        except Exception as e:
            print(f'  ERROR inserting {slug}: {e}')
            skipped += 1

    return inserted


print('=== Sons of Behemat ===')
ins = insert_units('sons-of-behemat', 'sons-of-behemat')
print(f'Inserted: {ins}')

print()
print('=== Helsmiths of Hashut ===')
ins = insert_units('helsmiths-of-hashut', 'helsmiths-of-hashut')
print(f'Inserted: {ins}')

db.commit()

# Verify final counts
print()
for faction_slug in ['sons-of-behemat', 'helsmiths-of-hashut']:
    c.execute('SELECT COUNT(*) FROM units WHERE faction_id=(SELECT id FROM factions WHERE slug=?)', (faction_slug,))
    cnt = c.fetchone()[0]
    print(f'{faction_slug}: {cnt} total units')

db.close()
