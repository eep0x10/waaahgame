"""Rename orruk-warclans -> bonesplitterz (Legends Destruction) + add missing Bonesplitterz Legends units per PDF."""
import sqlite3
import json
from datetime import datetime

DB = "/app/instance/waaahgame.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# 1. Rename faction
cur.execute(
    """UPDATE factions
       SET code='bonesplitterz', slug='bonesplitterz', name='Bonesplitterz',
           blurb='Bonesplitterz (Warhammer Legends, Destruction). Tribos orruk selvagens caçando monstros.'
       WHERE id=101"""
)

# 2. Fix Savage Orruk Morboys points: PDF says 160 (not 140)
cur.execute("UPDATE units SET points_cost=160, model_count=10 WHERE id=1754")

# 3. Add missing Bonesplitterz Legends units per PDF lines 3618-3636
# (slug, name, pts, model_count, role, category)
units = [
    ("kragnos-the-end-of-empires", "Kragnos, the End of Empires", 580, 1, "hero", "legends"),
    ("maniak-weirdnob", "Maniak Weirdnob", 160, 1, "hero", "legends"),
    ("savage-big-boss", "Savage Big Boss", 110, 1, "hero", "legends"),
    ("wardokk", "Wardokk", 100, 1, "hero", "legends"),
    ("wurrgog-prophet", "Wurrgog Prophet", 160, 1, "hero", "legends"),
    ("hedkrakkas-madmob", "Hedkrakka's Madmob", 100, 4, "infantry", "legends"),
    ("savage-big-stabbas", "Savage Big Stabbas", 130, 2, "infantry", "legends"),
    ("savage-boarboy-maniaks", "Savage Boarboy Maniaks", 140, 5, "cavalry", "legends"),
    ("savage-boarboys", "Savage Boarboys", 140, 5, "cavalry", "legends"),
    ("savage-orruk-arrowboys", "Savage Orruk Arrowboys", 140, 10, "infantry", "legends"),
    ("savage-orruks", "Savage Orruks", 140, 10, "infantry", "legends"),
]
now = datetime.utcnow().isoformat()
added = 0
for slug, name, pts, mc, role, cat in units:
    existing = cur.execute(
        "SELECT id FROM units WHERE slug=? AND faction_id=101", (slug,)
    ).fetchone()
    if existing:
        print("skip exist:", name)
        continue
    cur.execute(
        """INSERT INTO units (faction_id, slug, name, points_cost, model_count,
                              unit_role, unit_category, can_be_general, can_be_reinforced,
                              stats_json, weapons_json, abilities_json, keywords_json, companions_json,
                              created_at, updated_at)
           VALUES (101, ?, ?, ?, ?, ?, ?, 0, 0, ?, ?, ?, ?, ?, ?, ?)""",
        (slug, name, pts, mc, role, cat,
         "{}", "[]", "[]",
         json.dumps(["DESTRUCTION", "BONESPLITTERZ", "ORRUK"]),
         "[]", now, now),
    )
    added += 1
    print("added:", name, pts)

con.commit()

print(f"\n--- bonesplitterz faction (id=101) now {cur.execute('SELECT COUNT(*) c FROM units WHERE faction_id=101').fetchone()['c']} units:")
for r in cur.execute("SELECT id, name, points_cost, unit_category FROM units WHERE faction_id=101 ORDER BY name"):
    print(" ", r["id"], r["name"], r["points_cost"], r["unit_category"])
print(f"\nadded {added} new units")
con.close()
