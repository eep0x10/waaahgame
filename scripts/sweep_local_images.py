"""
Sweep local static/img/units/ for units that have no image_path but a file exists.
Matches by slug (exact) or slug-with-dashes-vs-underscores.
"""
import sqlite3
import os
import json

DB = "/app/instance/waaahgame.db"
IMG_ROOT = "/app/app/static/img/units"

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# Build file index: {faction_slug: {stem: rel_path}}
file_index = {}
if os.path.isdir(IMG_ROOT):
    for faction_dir in os.listdir(IMG_ROOT):
        faction_path = os.path.join(IMG_ROOT, faction_dir)
        if not os.path.isdir(faction_path):
            continue
        file_index[faction_dir] = {}
        for fname in os.listdir(faction_path):
            stem = os.path.splitext(fname)[0]
            file_index[faction_dir][stem] = f"units/{faction_dir}/{fname}"

# Units without image_path
no_img_units = con.execute("""
    SELECT u.id, u.slug, u.name, f.slug as faction_slug
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    WHERE u.image_path IS NULL OR u.image_path = ''
""").fetchall()

found = []
for r in no_img_units:
    fac_slug = r["faction_slug"]
    unit_slug = r["slug"]
    if fac_slug not in file_index:
        continue
    fac_files = file_index[fac_slug]
    # Exact match
    if unit_slug in fac_files:
        found.append((fac_files[unit_slug], r["id"], r["name"]))
        continue
    # Fallback: replace hyphens with underscores
    alt = unit_slug.replace("-", "_")
    if alt in fac_files:
        found.append((fac_files[alt], r["id"], r["name"]))

print(f"Units with no image_path but local file found: {len(found)}")
if found:
    for path, uid, name in found:
        print(f"  [{uid}] {name} -> {path}")
    confirm = input("Apply these image_path updates? [y/N] ").strip().lower()
    if confirm == "y":
        con.executemany("UPDATE units SET image_path = ? WHERE id = ?",
                        [(p, uid) for p, uid, _ in found])
        con.commit()
        print(f"Updated {len(found)} units.")
    else:
        print("Skipped.")
else:
    print("Nothing to fix.")

# Summary of images that exist per faction
print("\nLocal image files per faction dir:")
for fac, files in sorted(file_index.items()):
    print(f"  {fac}: {len(files)} files")

con.close()
