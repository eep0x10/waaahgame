"""
Extract AoS unit points from BSData .cat files and update units with points_cost=0.
Only updates where points_cost=0 (safe against hand-curated data).
AoS cats use entryLink elements with direct costs (not selectionEntry type=unit).
"""
import xml.etree.ElementTree as ET
import sqlite3
import os
import re

DB_PATH = '/app/instance/waaahgame.db'
BSAOS_DIR = '/app/scripts/cache/bsdata/aos'


def slugify(name):
    s = name.lower()
    # Handle common HTML entities
    s = s.replace('&apos;', "'").replace('&amp;', '&').replace('&#39;', "'")
    s = re.sub(r"[''`]", '', s)
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def parse_aos_cat(cat_path):
    """Parse an AoS .cat file and return {unit_name: pts} from entryLink elements."""
    try:
        tree = ET.parse(cat_path)
        root = tree.getroot()
    except Exception as e:
        print(f"  Parse error {cat_path}: {e}")
        return {}

    tag = root.tag
    ns = tag.split('}')[0] + '}' if '{' in tag else ''

    results = {}
    # Try entryLinks (main AoS pattern)
    for el in root.iter(f'{ns}entryLink'):
        name = el.get('name', '').strip()
        if not name:
            continue
        costs_el = el.find(f'{ns}costs')
        if costs_el is not None:
            for cost in costs_el:
                cname = cost.get('name', '').lower()
                if any(x in cname for x in ('pts', 'point')):
                    val = float(cost.get('value', '0'))
                    if val > 0:
                        results[name] = int(val)
                        break

    # Also try selectionEntry type=unit (fallback)
    for se in root.iter(f'{ns}selectionEntry'):
        etype = se.get('type', '')
        if etype not in ('unit', 'model'):
            continue
        name = se.get('name', '').strip()
        if not name:
            continue
        costs_el = se.find(f'{ns}costs')
        if costs_el is not None:
            for cost in costs_el:
                cname = cost.get('name', '').lower()
                if any(x in cname for x in ('pts', 'point')):
                    val = float(cost.get('value', '0'))
                    if val > 0:
                        if name not in results:
                            results[name] = int(val)
                        break

    return results


# Build name→pts map from all AoS files
print("=== Parsing all AoS .cat files ===")
all_pts = {}   # name -> pts
source_map = {}  # name -> file

for fname in sorted(os.listdir(BSAOS_DIR)):
    if not fname.endswith('.cat'):
        continue
    path = os.path.join(BSAOS_DIR, fname)
    pts_map = parse_aos_cat(path)
    if pts_map:
        print(f"  {fname}: {len(pts_map)} units")
        for name, pts in pts_map.items():
            if name not in all_pts:
                all_pts[name] = pts
                source_map[name] = fname

print(f"\nTotal AoS entries with pts > 0: {len(all_pts)}")

# Build slug->pts lookup
slug_pts = {}
for name, pts in all_pts.items():
    sl = slugify(name)
    if sl not in slug_pts:
        slug_pts[sl] = (pts, name)

# Update DB
conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

aos_id = conn.execute("SELECT id FROM game_systems WHERE code='aos4'").fetchone()['id']
zero_units = conn.execute("""
    SELECT u.id, u.slug, u.name, u.points_cost
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    WHERE f.game_system_id=? AND u.points_cost=0
    ORDER BY u.slug
""", (aos_id,)).fetchall()

print(f"\nAoS units with points_cost=0: {len(zero_units)}")

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
        matched_by = f"slug '{matched_name}'"
    # Try slugify of unit name
    elif slugify(name) in slug_pts:
        pts, matched_name = slug_pts[slugify(name)]
        matched_by = f"name-slug '{matched_name}'"
    # Try stripping trailing comma/qualifier from name
    else:
        base = re.sub(r',.*$', '', name).strip()
        base_slug = slugify(base)
        if base_slug in slug_pts:
            pts, matched_name = slug_pts[base_slug]
            matched_by = f"base-name '{matched_name}'"

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
if not_found:
    print("\nStill zero (not found in BSData):")
    for slug, name in not_found:
        print(f"  {slug} | {name}")

# Final count
remaining_zero = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    WHERE f.game_system_id=? AND u.points_cost=0
""", (aos_id,)).fetchone()['cnt']
total_aos = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    WHERE f.game_system_id=?
""", (aos_id,)).fetchone()['cnt']
print(f"\nFinal AoS: zero={remaining_zero}/{total_aos} ({round(100*remaining_zero/total_aos,1)}%)")

conn.close()
