#!/usr/bin/env python3
"""Full plural check."""
import sqlite3

DB_PATH = '/app/instance/waaahgame.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

# All 54 plural->singular pairs from audit
plural_to_singular = [
    ('aggradon-lancers', 'aggradon-lancer'),
    ('annihilators', 'annihilator'),
    ('beasts-of-nurgle', 'beast-of-nurgle'),
    ('bladegheist-revenants', 'bladegheist-revenant'),
    ('blood-knights', 'blood-knight'),
    ('blood-sisters', 'blood-sister'),
    ('blood-stalkers', 'blood-stalker'),
    ('chainrasps', 'chainrasp'),
    ('chaos-knights', 'chaos-knight'),
    ('chaos-warriors', 'chaos-warrior'),
    ('clanrats', 'clanrat'),
    ('dire-wolves', 'dire-wolf'),
    ('doomfire-warlocks', 'doomfire-warlock'),
    ('dryads', 'dryad'),
    ('fellwater-troggoths', 'fellwater-troggoth'),
    ('flamers-of-tzeentch', 'flamer-of-tzeentch'),
    ('freeguild-cavaliers', 'freeguild-cavalier'),
    ('freeguild-steelhelms', 'freeguild-steelhelm'),
    ('glaivewraith-stalkers', 'glaivewraith-stalker'),
    ('grimghast-reapers', 'grimghast-reaper'),
    ('gutter-runners', 'gutter-runner'),
    ('hexwraiths', 'hexwraith'),
    ('irondrakes', 'irondrake'),
    ('kairic-acolytes', 'kairic-acolyte'),
    ('kavalos-deathriders', 'kavalos-deathrider'),
    ('khinerai-lifetakers', 'khinerai-lifetaker'),
    ('liberators', 'liberator'),
    ('necropolis-stalkers', 'necropolis-stalker'),
    ('night-runners', 'night-runner'),
    ('nurglings', 'nurgling'),
    ('orruk-weirdnob-shaman', 'weirdnob-shaman'),
    ('pink-horrors-of-tzeentch', 'pink-horror-of-tzeentch'),
    ('plague-censer-bearers', 'plague-censer-bearer'),
    ('plague-monks', 'plague-monk'),
    ('praetors', 'praetor'),
    ('putrid-blightkings', 'putrid-blightking'),
    ('rat-ogors', 'rat-ogor'),
    ('rockgut-troggoths', 'rockgut-troggoth'),
    ('saurus-warriors', 'saurus-warrior'),
    ('savage-orruk-morboys', 'savage-orruk-morboy'),
    ('screamers-of-tzeentch', 'screamer-of-tzeentch'),
    ('sisters-of-slaughter', 'sister-of-slaughter'),
    ('skeleton-warriors', 'deathrattle-skeleton'),  # special case
    ('skinks', 'skink'),
    ('skywardens', 'skywarden'),
    ('spirit-hosts', 'spirit-host'),
    ('spite-revenants', 'spite-revenant'),
    ('squig-hoppers', 'squig-hopper'),
    ('stormfiends', 'stormfiend'),
    ('tree-revenants', 'tree-revenant'),
    ('tzaangors', 'tzaangor'),
    ('vargheists', 'vargheist'),
    ('vindictors', 'vindictor'),
    ('warplock-jezzails', 'warplock-jezzail'),
    ('witch-aelves', 'witch-aelf'),
]

print("=== PLURAL->SINGULAR STATUS (ALL 54) ===")
needs_rename = []
already_done = []
for old, new in plural_to_singular:
    old_exists = bool(q("SELECT 1 FROM units WHERE slug=?", (old,)))
    new_exists = bool(q("SELECT 1 FROM units WHERE slug=?", (new,)))
    if old_exists and not new_exists:
        needs_rename.append((old, new))
        print(f"  NEEDS RENAME: {old} -> {new}")
    elif old_exists and new_exists:
        print(f"  CONFLICT (both exist): {old} + {new}")
    elif not old_exists and new_exists:
        already_done.append((old, new))
    else:
        print(f"  BOTH MISSING: {old} / {new}")

print(f"\nNeeds rename: {len(needs_rename)}")
print(f"Already done: {len(already_done)}")

# Check light-of-eltharion
print("\n=== LIGHT OF ELTHARION ===")
rows = q("SELECT slug, name, image_path FROM units WHERE slug LIKE '%eltharion%'")
for r in rows: print(r)

# Check what image files exist for target units
print("\n=== EXISTING IMAGE FILES (spot check) ===")
import os
checks = [
    '/app/app/static/img/units/gloomspite-gitz/skragrott-the-loonking.jpg',
    '/app/app/static/img/units/gloomspite-gitz/moonclan-grots.jpg',
    '/app/app/static/img/units/kharadron-overlords/brokk-grungsson-lord-magnate-of-barak-nar.jpg',
    '/app/app/static/img/units/lumineth-realm-lords/alarith-spirit-of-the-mountain.jpg',
    '/app/app/static/img/units/soulblight-gravelords/black-knights.jpg',
    '/app/app/static/img/units/soulblight-gravelords/barrow-knight.jpg',
]
for p in checks:
    size = os.path.getsize(p) if os.path.exists(p) else 0
    print(f"  {os.path.basename(p)}: {'EXISTS' if os.path.exists(p) else 'MISSING'} ({size}b)")

conn.close()
print("\nDone.")
