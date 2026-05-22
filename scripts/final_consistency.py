#!/usr/bin/env python3
"""Final consistency check: for every AoS unit in DB, does the image file exist?"""
import sqlite3, os

DB_PATH = '/app/instance/waaahgame.db'
IMG_BASE = '/app/app/static/img'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

# Get all AoS units (joined with game_system to filter AoS only)
c.execute("""
    SELECT u.slug, u.name, u.image_path, f.slug as faction_slug, gs.code as gs_code
    FROM units u
    JOIN factions f ON u.faction_id = f.id
    JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE gs.code = 'aos4'
    ORDER BY f.slug, u.slug
""")
rows = c.fetchall()

has_image = 0
missing_image = []
total = len(rows)

for row in rows:
    img_path = row['image_path']
    if img_path:
        full = os.path.join(IMG_BASE, img_path)
        if os.path.exists(full) and os.path.getsize(full) > 10240:
            has_image += 1
        else:
            missing_image.append((row['slug'], img_path, 'FILE_MISSING_OR_SMALL'))
    else:
        missing_image.append((row['slug'], None, 'NO_IMAGE_PATH'))

print(f"Total AoS units: {total}")
print(f"With valid image: {has_image}")
print(f"Missing image: {len(missing_image)}")
print()
if missing_image:
    print("=== SLUGS WITHOUT PHOTO ===")
    for slug, path, reason in missing_image:
        print(f"  {reason}: {slug} (path={path})")

conn.close()
