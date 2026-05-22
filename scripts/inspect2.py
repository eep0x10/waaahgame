#!/usr/bin/env python3
"""Inspect current DB state for Mission B."""
import sqlite3

DB_PATH = '/app/instance/waaahgame.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

print("=== RENAME STATUS ===")
rename_checks = [
    'black-knights', 'barrow-knight',
    'moonclan-grots', 'stabba',
    'vampire-lord-on-zombie-dragon', 'vampire-lord',
]
for s in rename_checks:
    rows = q("SELECT slug, name FROM units WHERE slug=?", (s,))
    status = "EXISTS" if rows else "MISSING"
    print(f"  {s}: {status}", rows[0] if rows else "")

print("\n=== DELETE STATUS ===")
for s in ['freeguild-crossbowmen', 'helblaster-volley-gun']:
    rows = q("SELECT slug, name FROM units WHERE slug=?", (s,))
    print(f"  {s}: {'EXISTS' if rows else 'ALREADY GONE'}")

print("\n=== PLURAL->SINGULAR STATUS (sample 10) ===")
plural_slugs = [
    'aggradon-lancers', 'annihilators', 'beasts-of-nurgle', 'bladegheist-revenants',
    'blood-knights', 'blood-sisters', 'chainrasps', 'chaos-knights', 'clanrats',
    'skeleton-warriors', 'skinks',
]
for s in plural_slugs:
    rows = q("SELECT slug FROM units WHERE slug=?", (s,))
    print(f"  {s}: {'EXISTS (needs rename)' if rows else 'ALREADY RENAMED'}")

print("\n=== MISSING CHAOS ADDITIONS STATUS ===")
chaos_slugs = ['beastrider', 'burning-chariot', 'chaos-lord', 'disc-of-tzeentch',
               'ethereal-steed', 'grot-scuttling', 'herald-of-nurgle', 'karkadrak',
               'seeker-chariot', 'tzeentch-sorcerer-lord']
for s in chaos_slugs:
    rows = q("SELECT slug, name FROM units WHERE slug=?", (s,))
    print(f"  {s}: {'EXISTS' if rows else 'MISSING (needs add)'}")

print("\n=== TOTAL UNIT COUNT ===")
rows = q("SELECT COUNT(*) FROM units")
print(f"  Total units: {rows[0][0]}")

print("\n=== FACTIONS for chaos additions ===")
chaos_factions = ['beastclaw-raiders', 'disciples-of-tzeentch', 'daemons-of-tzeentch',
                  'slaves-to-darkness', 'nighthaunt', 'gloomspite-gitz',
                  'maggotkin-of-nurgle', 'daemons-of-nurgle', 'hedonites-of-slaanesh']
for f in chaos_factions:
    rows = q("SELECT id, slug, name, grand_alliance FROM factions WHERE slug=?", (f,))
    if rows:
        print(f"  {f}: id={rows[0][0]} ga={rows[0][3]}")

conn.close()
print("\nDone.")
