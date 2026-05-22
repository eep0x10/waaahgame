"""
Extract 40K unit points from BSData Library .cat files and update units with points_cost=0.
Only updates where points_cost=0 (safe against hand-curated data).
"""
import xml.etree.ElementTree as ET
import sqlite3
import os
import re

DB_PATH = '/app/instance/waaahgame.db'
BSK40_DIR = '/app/scripts/cache/bsdata/40k'

def slugify(name):
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s

def parse_40k_library(cat_path):
    """Parse a 40K .cat file and return {unit_name: pts} for top-level unit entries."""
    try:
        tree = ET.parse(cat_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  Parse error {cat_path}: {e}")
        return {}

    tag = root.tag
    ns = ''
    if '{' in tag:
        ns = tag.split('}')[0] + '}'

    results = {}
    for se in root.iter(f'{ns}selectionEntry'):
        etype = se.get('type', '')
        if etype != 'unit':
            continue
        name = se.get('name', '').strip()
        if not name:
            continue
        # Get direct costs (not nested under child entries)
        costs_el = se.find(f'{ns}costs')
        if costs_el is not None:
            for cost in costs_el:
                cname = cost.get('name', '').lower()
                if cname in ('pts', 'points', 'pt'):
                    val = float(cost.get('value', '0'))
                    if val > 0:
                        results[name] = int(val)
                        break
    return results

# Build name→pts map from all 40K files
print("=== Parsing all 40K .cat files ===")
all_pts = {}  # name -> pts
source_map = {}  # name -> file

for fname in sorted(os.listdir(BSK40_DIR)):
    if not fname.endswith('.cat'):
        continue
    path = os.path.join(BSK40_DIR, fname)
    pts_map = parse_40k_library(path)
    if pts_map:
        print(f"  {fname}: {len(pts_map)} units with pts")
        for name, pts in pts_map.items():
            print(f"    '{name}' pts={pts}")
            if name not in all_pts:
                all_pts[name] = pts
                source_map[name] = fname

print(f"\nTotal 40K entries with pts > 0: {len(all_pts)}")

# Build slug->pts lookup
slug_pts = {}
for name, pts in all_pts.items():
    slug_pts[slugify(name)] = (pts, name)

# Also try some name variants (add -40k suffix)
slug_pts_40k = {}
for name, pts in all_pts.items():
    slug_pts_40k[slugify(name) + '-40k'] = (pts, name)

# Update DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Get all 40K units with points_cost=0
w40k_id = conn.execute("SELECT id FROM game_systems WHERE code='w40k10'").fetchone()['id']
zero_units = conn.execute("""
    SELECT u.id, u.slug, u.name, u.points_cost
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    WHERE f.game_system_id=? AND u.points_cost=0
    ORDER BY u.slug
""", (w40k_id,)).fetchall()

print(f"\n40K units with points_cost=0: {len(zero_units)}")

updated = 0
not_found = []

for unit in zero_units:
    slug = unit['slug']
    name = unit['name']
    pts = None
    matched_by = None

    # Try exact slug
    if slug in slug_pts:
        pts, matched_name = slug_pts[slug]
        matched_by = f"slug match '{matched_name}'"
    # Try -40k suffix slug
    elif slug in slug_pts_40k:
        pts, matched_name = slug_pts_40k[slug]
        matched_by = f"slug-40k match '{matched_name}'"
    # Try slugify of unit name
    elif slugify(name) in slug_pts:
        pts, matched_name = slug_pts[slugify(name)]
        matched_by = f"name-slug match '{matched_name}'"
    # Try stripping -40k from slug and matching
    elif slug.endswith('-40k') and slug[:-4] in slug_pts:
        pts, matched_name = slug_pts[slug[:-4]]
        matched_by = f"strip-40k match '{matched_name}'"

    if pts is not None:
        conn.execute("UPDATE units SET points_cost=? WHERE id=?", (pts, unit['id']))
        updated += 1
        print(f"  UPDATED: {slug} -> {pts} ({matched_by})")
    else:
        not_found.append((slug, name))

conn.commit()

print(f"\n=== RESULT ===")
print(f"Updated: {updated}")
print(f"Still zero: {len(not_found)}")
print("\nStill zero (not found in BSData):")
for slug, name in not_found:
    print(f"  {slug} | {name}")

# Final count
remaining_zero = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    WHERE f.game_system_id=? AND u.points_cost=0
""", (w40k_id,)).fetchone()['cnt']
print(f"\nFinal 40K units still at 0 pts: {remaining_zero}")
