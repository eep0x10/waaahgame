#!/usr/bin/env python3
"""Mission A+B: image import and DB alignment script."""
import sqlite3
import os
import shutil
import sys

DB_PATH = '/app/instance/waaahgame.db'
STATIC_DIR = '/app/app/static/img/units'

conn = sqlite3.connect(DB_PATH)
c = conn.cursor()

# --- Query helpers ---
def q(sql, params=()):
    c.execute(sql, params)
    return c.fetchall()

# === INSPECT phase ===
print("=== BROKK SLUG ===")
rows = q("SELECT slug, name, image_path FROM units WHERE slug LIKE '%brokk%' OR slug LIKE '%grungsson%'")
for r in rows:
    print(r)

print("\n=== ALL 25 MISSION A SLUGS ===")
slugs = [
    'skragrott-the-loonking','moonclan-grots','brokk-grungsson',
    'brokk-grungsson-lord-magnate-of-barak-nar',
    'alarith-spirit-of-the-mountain','alarith-stoneguard','alarith-stonemage',
    'scinari-cathallar','the-light-of-eltharion','light-of-eltharion',
    'vanari-lord-regent','vanari-auralan-wardens','rotigus',
    'gordrakk-the-fist-of-gork','swampcalla-shaman-with-pot-grot',
    'swampcalla-shaman','kruleboyz-gutrippaz',
    'nagash-supreme-lord-of-the-undead','nagash',
    'thanquol-on-boneripper','archaon-the-everchosen',
    'be-lakor-the-dark-master','belakor',
    'black-knights','barrow-knight',
    'mannfred-von-carstein-mortarch-of-night','mannfred-von-carstein',
    'vampire-lord-on-zombie-dragon','vampire-lord',
    'yndrasta-the-celestial-spear','drycha-hamadreth',
    'morathi-khaine','kairos-fateweaver',
]
for s in slugs:
    rows = q("SELECT slug, name, image_path FROM units WHERE slug=?", (s,))
    for r in rows:
        print(r)

print("\n=== FACTION CHECK for target units ===")
targets = [
    'skragrott-the-loonking','moonclan-grots',
    'alarith-spirit-of-the-mountain','alarith-stoneguard','alarith-stonemage',
    'scinari-cathallar','the-light-of-eltharion',
    'vanari-lord-regent','vanari-auralan-wardens','rotigus',
    'gordrakk-the-fist-of-gork','swampcalla-shaman-with-pot-grot',
    'kruleboyz-gutrippaz','nagash-supreme-lord-of-the-undead',
    'thanquol-on-boneripper','archaon-the-everchosen',
    'be-lakor-the-dark-master','black-knights',
    'mannfred-von-carstein-mortarch-of-night','vampire-lord-on-zombie-dragon',
    'yndrasta-the-celestial-spear','drycha-hamadreth',
    'morathi-khaine','kairos-fateweaver',
    'brokk-grungsson-lord-magnate-of-barak-nar',
]
for s in targets:
    rows = q("SELECT u.slug, u.image_path, f.slug as faction_slug FROM units u JOIN factions f ON u.faction_id=f.id WHERE u.slug=?", (s,))
    for r in rows:
        print(r)

conn.close()
print("\nDone inspect.")
