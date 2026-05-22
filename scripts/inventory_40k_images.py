"""
Stage 4: Inventory 40K image situation.
Count units with/without images, list static dirs, generate punch-list.
"""
import sqlite3
import os
import json

DB_PATH = '/app/instance/waaahgame.db'
STATIC_IMG = '/app/app/static/img/units'
OUTPUT_PATH = '/app/scripts/cache/40k_image_needs.md'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row

# Get all 40K units with faction info
units = conn.execute("""
    SELECT u.id, u.slug, u.name, u.image_path, f.code as faction_code, f.name as faction_name
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='w40k10'
    ORDER BY f.code, u.name
""").fetchall()

# Check which have actual image files
def has_image(image_path):
    if not image_path:
        return False
    full_path = os.path.join(STATIC_IMG, image_path.replace('units/', '', 1))
    return os.path.exists(full_path)

total = len(units)
has_img = 0
missing_img = 0
null_img = 0

by_faction = {}

needs_image = []

for u in units:
    fcode = u['faction_code']
    if fcode not in by_faction:
        by_faction[fcode] = {'faction_name': u['faction_name'], 'total': 0, 'has_img': 0, 'missing': []}
    by_faction[fcode]['total'] += 1

    if u['image_path']:
        # Check if file exists
        full = os.path.join(STATIC_IMG, u['image_path'].replace('units/', '', 1))
        if os.path.exists(full):
            has_img += 1
            by_faction[fcode]['has_img'] += 1
        else:
            missing_img += 1
            by_faction[fcode]['missing'].append((u['slug'], u['name']))
            needs_image.append((fcode, u['faction_name'], u['slug'], u['name'], 'broken_path', u['image_path']))
    else:
        null_img += 1
        by_faction[fcode]['missing'].append((u['slug'], u['name']))
        needs_image.append((fcode, u['faction_name'], u['slug'], u['name'], 'null', ''))

# Check existing 40K dirs in static
print("=== 40K Static Dirs ===")
k40_dirs = []
if os.path.exists(STATIC_IMG):
    for d in os.listdir(STATIC_IMG):
        full_d = os.path.join(STATIC_IMG, d)
        if os.path.isdir(full_d):
            # Check if this is a 40K faction dir
            faction_check = conn.execute("""
                SELECT f.code FROM factions f
                JOIN game_systems gs ON gs.id=f.game_system_id
                WHERE gs.code='w40k10' AND f.code=?
            """, (d,)).fetchone()
            if faction_check:
                files = [f for f in os.listdir(full_d) if f.endswith(('.jpg','.png','.webp','.svg'))]
                print(f"  {d}: {len(files)} images")
                k40_dirs.append((d, len(files)))

print(f"\n=== 40K Image Summary ===")
print(f"Total 40K units: {total}")
print(f"  With confirmed image file: {has_img}")
print(f"  With image_path but file missing: {missing_img}")
print(f"  NULL image_path: {null_img}")
print(f"  Need image: {missing_img + null_img}")

print("\n=== By faction ===")
for fcode, data in sorted(by_faction.items()):
    pct = int(100 * data['has_img'] / data['total']) if data['total'] else 0
    print(f"  {data['faction_name']}: {data['has_img']}/{data['total']} ({pct}%)")

# Write punch-list
print(f"\nWriting punch-list to {OUTPUT_PATH}...")
with open(OUTPUT_PATH, 'w') as f:
    f.write("# 40K Image Needs\n\n")
    f.write(f"**Generated:** Stage 4 inventory\n\n")
    f.write(f"**Total 40K units:** {total}  \n")
    f.write(f"**Have confirmed image:** {has_img} ({int(100*has_img/total)}%)  \n")
    f.write(f"**Need image (null or broken):** {missing_img + null_img}  \n\n")
    f.write("---\n\n")

    current_faction = None
    for fcode, fname, slug, name, status, img_path in needs_image:
        if fcode != current_faction:
            if current_faction is not None:
                f.write("\n")
            f.write(f"## {fname} (`{fcode}`)\n\n")
            f.write("| slug | name | status |\n")
            f.write("|------|------|--------|\n")
            current_faction = fcode
        f.write(f"| `{slug}` | {name} | {status} |\n")

print(f"Done. Punch-list at {OUTPUT_PATH}")
