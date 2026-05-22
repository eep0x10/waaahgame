#!/usr/bin/env python3
"""Mission B: DB cleanup - delete old plural/duplicate slug entries."""
import sqlite3, os

DB_PATH = '/app/instance/waaahgame.db'
IMG_BASE = '/app/app/static/img'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

def exec_sql(sql, params=()):
    c.execute(sql, params)

# All old plural slugs to delete (singular counterpart already exists)
OLD_PLURALS = [
    'aggradon-lancers', 'annihilators', 'beasts-of-nurgle', 'bladegheist-revenants',
    'blood-knights', 'blood-sisters', 'blood-stalkers', 'chainrasps',
    'chaos-knights', 'chaos-warriors', 'clanrats', 'dire-wolves',
    'doomfire-warlocks', 'dryads', 'fellwater-troggoths', 'flamers-of-tzeentch',
    'freeguild-cavaliers', 'freeguild-steelhelms', 'glaivewraith-stalkers',
    'grimghast-reapers', 'gutter-runners', 'hexwraiths', 'irondrakes',
    'kairic-acolytes', 'kavalos-deathriders', 'khinerai-lifetakers',
    'liberators', 'necropolis-stalkers', 'night-runners', 'nurglings',
    'orruk-weirdnob-shaman', 'pink-horrors-of-tzeentch', 'plague-censer-bearers',
    'plague-monks', 'praetors', 'putrid-blightkings', 'rat-ogors',
    'rockgut-troggoths', 'saurus-warriors', 'savage-orruk-morboys',
    'screamers-of-tzeentch', 'sisters-of-slaughter', 'skywardens',
    'spirit-hosts', 'spite-revenants', 'squig-hoppers', 'stormfiends',
    'tree-revenants', 'tzaangors', 'vargheists', 'vindictors',
    'warplock-jezzails', 'witch-aelves',
]

# Old rename slugs (already renamed to new slug in previous run)
OLD_RENAMES = [
    'black-knights',
    'moonclan-grots',
    'vampire-lord-on-zombie-dragon',
]

all_to_delete = OLD_PLURALS + OLD_RENAMES

print(f"=== MISSION B: Deleting {len(all_to_delete)} old/duplicate DB entries ===")
deleted_db = 0
deleted_imgs = 0

for slug in all_to_delete:
    rows = q("SELECT id, slug, image_path FROM units WHERE slug=?", (slug,))
    if not rows:
        print(f"  SKIP (not found): {slug}")
        continue
    row = rows[0]
    unit_id = row['id']
    img_path = row['image_path']

    # Delete from unit_versions first (FK constraint)
    exec_sql("DELETE FROM unit_versions WHERE unit_id=?", (unit_id,))
    exec_sql("DELETE FROM units WHERE id=?", (unit_id,))
    deleted_db += 1

    # Delete image file (the old plural-named file)
    if img_path:
        full_img = os.path.join(IMG_BASE, img_path)
        if os.path.exists(full_img):
            try:
                os.remove(full_img)
                deleted_imgs += 1
            except Exception as e:
                print(f"  IMG DELETE ERR: {slug}: {e}")
        # else already gone

conn.commit()
print(f"DB entries deleted: {deleted_db}")
print(f"Image files deleted: {deleted_imgs}")

# Fix vampire-lord image_path: we imported .webp but DB still says .jpg
rows = q("SELECT id, image_path FROM units WHERE slug='vampire-lord'")
if rows:
    vid = rows[0]['id']
    old_path = rows[0]['image_path']
    new_path = 'units/soulblight-gravelords/vampire-lord.webp'
    # Check if the webp exists
    webp_full = os.path.join(IMG_BASE, new_path)
    jpg_full = os.path.join(IMG_BASE, 'units/soulblight-gravelords/vampire-lord.jpg')
    if os.path.exists(webp_full) and not os.path.exists(jpg_full):
        exec_sql("UPDATE units SET image_path=? WHERE id=?", (new_path, vid))
        conn.commit()
        print(f"Updated vampire-lord image_path: {old_path} -> {new_path}")
    elif os.path.exists(jpg_full):
        print(f"vampire-lord .jpg exists ({os.path.getsize(jpg_full)}b), keeping .jpg path")
    else:
        print(f"Warning: neither .jpg nor .webp found for vampire-lord")

# =========================================================
# VERIFICATION
# =========================================================
print("\n=== VERIFICATION ===")

# Old slugs should be gone
print("Old slugs gone?")
for slug in all_to_delete[:10]:
    rows = q("SELECT slug FROM units WHERE slug=?", (slug,))
    print(f"  {slug}: {'STILL EXISTS!' if rows else 'GONE ok'}")

# New slugs exist
print("\nNew canonical slugs present?")
canonical_checks = [
    'barrow-knight', 'stabba', 'vampire-lord',
    'aggradon-lancer', 'annihilator', 'blood-knight', 'blood-sister',
    'chainrasp', 'chaos-knight', 'dryad', 'deathrattle-skeleton', 'skink',
    'witch-aelf', 'vargheist', 'vindictor', 'warplock-jezzail',
]
for slug in canonical_checks:
    rows = q("SELECT slug FROM units WHERE slug=?", (slug,))
    print(f"  {slug}: {'OK' if rows else 'MISSING!'}")

total = q("SELECT COUNT(*) FROM units")[0][0]
print(f"\nTotal units after cleanup: {total}")

conn.close()
print("Mission B done.")
