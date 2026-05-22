#!/usr/bin/env python3
"""Check image files for plural slugs and for the old rename slugs."""
import sqlite3, os

DB_PATH = '/app/instance/waaahgame.db'
STATIC_DIR = '/app/app/static/img/units'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

# For conflicts: show which one has an image and which data looks better
conflicts_to_delete_old = [
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

print("=== PLURAL OLD SLUGS (to delete) - image check ===")
for slug in conflicts_to_delete_old:
    rows = q("SELECT slug, image_path FROM units WHERE slug=?", (slug,))
    if rows:
        img_path = rows[0][1]
        if img_path:
            full = os.path.join(STATIC_DIR, '..', '..', img_path).replace('\\', '/')
            # image_path is like 'units/faction/slug.jpg', STATIC parent is img/
            full = '/app/app/static/img/' + img_path
            exists = os.path.exists(full)
            size = os.path.getsize(full) if exists else 0
            if exists:
                print(f"  {slug}: HAS IMAGE at {img_path} ({size}b)")
        else:
            print(f"  {slug}: no image_path")

print("\n=== OLD RENAME SLUGS (dupes to delete) ===")
for slug in ['black-knights', 'moonclan-grots', 'vampire-lord-on-zombie-dragon']:
    rows = q("SELECT slug, image_path FROM units WHERE slug=?", (slug,))
    if rows:
        img_path = rows[0][1]
        if img_path:
            full = '/app/app/static/img/' + img_path
            exists = os.path.exists(full)
            size = os.path.getsize(full) if exists else 0
            print(f"  {slug}: {'HAS IMAGE' if exists else 'no file'} {img_path} ({size}b)")

print("\n=== NEW SINGULAR SLUGS - image check ===")
new_slugs_sample = [
    'barrow-knight', 'stabba', 'vampire-lord',
    'aggradon-lancer', 'annihilator', 'blood-knight',
    'deathrattle-skeleton', 'skink',
]
for slug in new_slugs_sample:
    rows = q("SELECT slug, image_path FROM units WHERE slug=?", (slug,))
    if rows:
        img_path = rows[0][1]
        if img_path:
            full = '/app/app/static/img/' + img_path
            exists = os.path.exists(full)
            size = os.path.getsize(full) if exists else 0
            print(f"  {slug}: {'HAS IMAGE' if exists else 'NO IMAGE'} {img_path} ({size}b)")
        else:
            print(f"  {slug}: no image_path in DB")

conn.close()
print("\nDone.")
