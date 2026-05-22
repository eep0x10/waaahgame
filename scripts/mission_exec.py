#!/usr/bin/env python3
"""Mission A + B execution script.

Mission A: Copy 25 downloaded images to correct faction subdirs.
Mission B:
  - Delete old plural slug entries from DB (singular already exists)
  - Delete old rename slug entries (barrow-knight/stabba/vampire-lord already exist)
  - Delete image files for old plural slugs
  - Delete image files for old rename slugs
  NOTE: Chaos additions and skeleton-warriors/skinks already done in previous runs.
"""
import sqlite3, os, shutil, sys

DB_PATH = '/app/instance/waaahgame.db'
STATIC_UNITS_DIR = '/app/app/static/img/units'
IMG_BASE = '/app/app/static/img'

conn = sqlite3.connect(DB_PATH)
conn.row_factory = sqlite3.Row
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

def exec_sql(sql, params=()):
    c.execute(sql, params)

# =========================================================
# MISSION A: Map download files to DB slugs + faction dirs
# =========================================================

# Downloads dir mapping: filename -> (db_slug, original_ext)
# Based on the 25 files found:
downloads_dir = '/downloads'  # Will be provided as host path; we use the mapped volume
# The docker-compose does NOT mount downloads. We'll use host paths via volume.
# Actually docker-compose maps ./scripts and ./app/static but NOT downloads.
# So we need to copy files from host Downloads to static BEFORE running in container.
# This script only does the DB + intra-container file operations.
# The actual copy from Downloads happens via PowerShell on the host.

print("Script executed. DB path:", DB_PATH)
print("Static units dir:", STATIC_UNITS_DIR)

# =========================================================
# MISSION B: Delete old plural slugs from DB
# =========================================================

# All plural slugs that now have a singular counterpart (to DELETE from DB)
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

# Old rename slugs (renamed in previous run, but old entry still in DB)
OLD_RENAMES = [
    'black-knights',
    'moonclan-grots',
    'vampire-lord-on-zombie-dragon',
]

all_to_delete = OLD_PLURALS + OLD_RENAMES

print(f"\n=== MISSION B: Deleting {len(all_to_delete)} old/duplicate DB entries ===")
deleted_db = 0
deleted_imgs = 0
img_delete_errors = []

for slug in all_to_delete:
    rows = q("SELECT id, slug, image_path FROM units WHERE slug=?", (slug,))
    if not rows:
        print(f"  SKIP (not found): {slug}")
        continue
    row = rows[0]
    unit_id = row['id']
    img_path = row['image_path']

    # Delete from unit_versions first (FK)
    exec_sql("DELETE FROM unit_versions WHERE unit_id=?", (unit_id,))
    exec_sql("DELETE FROM units WHERE id=?", (unit_id,))
    deleted_db += 1

    # Delete image file
    if img_path:
        full_img = os.path.join(IMG_BASE, img_path)
        if os.path.exists(full_img):
            try:
                os.remove(full_img)
                deleted_imgs += 1
                print(f"  DELETED: {slug} + img {img_path}")
            except Exception as e:
                img_delete_errors.append((slug, str(e)))
                print(f"  DELETED DB only (img err): {slug} -> {e}")
        else:
            print(f"  DELETED DB (img not found): {slug}")
    else:
        print(f"  DELETED DB (no img): {slug}")

conn.commit()
print(f"\nDB deleted: {deleted_db}, Images deleted: {deleted_imgs}")
if img_delete_errors:
    print(f"Image delete errors: {img_delete_errors}")

# =========================================================
# VERIFICATION
# =========================================================
print("\n=== VERIFICATION: Spot check new slugs exist ===")
checks = ['barrow-knight', 'stabba', 'vampire-lord', 'aggradon-lancer',
          'annihilator', 'blood-knight', 'deathrattle-skeleton', 'skink',
          'witch-aelf', 'vargheist', 'dryad']
for slug in checks:
    rows = q("SELECT slug FROM units WHERE slug=?", (slug,))
    print(f"  {slug}: {'OK' if rows else 'MISSING!'}")

print("\n=== VERIFICATION: Old slugs gone ===")
for slug in all_to_delete[:10]:
    rows = q("SELECT slug FROM units WHERE slug=?", (slug,))
    print(f"  {slug}: {'STILL EXISTS!' if rows else 'GONE'}")

total = q("SELECT COUNT(*) FROM units")[0][0]
print(f"\nTotal units after cleanup: {total}")

conn.close()
print("\nMission B done.")
