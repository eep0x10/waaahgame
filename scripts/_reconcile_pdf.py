"""One-shot: reassign orruk-warclans stragglers + add 6 universal manifestations."""
import sqlite3
import json
from datetime import datetime

DB = "/app/instance/waaahgame.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row
cur = con.cursor()

# 1. Reassign stragglers
cur.execute("UPDATE units SET faction_id=75 WHERE id IN (1748, 1749)")  # ironjawz
cur.execute("UPDATE units SET faction_id=76 WHERE id=1756")              # kruleboyz
# Savage Orruk Morboys (1754, legends) stays in orruk-warclans.

# 2. Get/create universal-manifestations faction
aos = cur.execute("SELECT id FROM game_systems WHERE code='aos4'").fetchone()
aos_id = aos["id"]

row = cur.execute(
    "SELECT id FROM factions WHERE slug='universal-manifestations' AND game_system_id=?",
    (aos_id,),
).fetchone()
if row:
    uni_id = row["id"]
else:
    now = datetime.utcnow().isoformat()
    cur.execute(
        """INSERT INTO factions (game_system_id, code, slug, name, grand_alliance, blurb, created_at, updated_at)
           VALUES (?, 'universal', 'universal-manifestations', 'Universal Manifestations', 'Universal',
                   'Manifestacoes universais disponiveis para qualquer exercito com WIZARD/PRIEST.', ?, ?)""",
        (aos_id, now, now),
    )
    uni_id = cur.lastrowid
print("universal faction id:", uni_id)

# 3. Add 6 universal manifestations
manifestations = [
    ("krondspine-incarnate", "Krondspine Incarnate of Ghur", 0),
    ("forbidden-power", "Forbidden Power", 20),
    ("morbid-conjuration", "Morbid Conjuration", 20),
    ("aetherwrought-machineries", "Aetherwrought Machineries", 0),
    ("primal-energy", "Primal Energy", 10),
    ("twilit-sorceries", "Twilit Sorceries", 0),
]
now = datetime.utcnow().isoformat()
for slug, name, pts in manifestations:
    existing = cur.execute(
        "SELECT id FROM units WHERE slug=? AND faction_id=?", (slug, uni_id)
    ).fetchone()
    if existing:
        print("skip exist:", name)
        continue
    cur.execute(
        """INSERT INTO units (faction_id, slug, name, points_cost, model_count, unit_role, unit_category,
                              can_be_general, can_be_reinforced,
                              stats_json, weapons_json, abilities_json, keywords_json, companions_json,
                              created_at, updated_at)
           VALUES (?, ?, ?, ?, 1, 'manifestation', 'manifestation', 0, 0, ?, ?, ?, ?, ?, ?, ?)""",
        (uni_id, slug, name, pts, "{}", "[]", "[]",
         json.dumps(["MANIFESTATION", "UNIVERSAL"]), "[]", now, now),
    )
    print("added:", name, pts)

con.commit()

# Verify
print("--- orruk-warclans (101) now:")
for r in cur.execute("SELECT id, name, unit_category FROM units WHERE faction_id=101"):
    print(" ", r["id"], r["name"], r["unit_category"])
print("--- universal manifestations:")
for r in cur.execute("SELECT id, name, points_cost FROM units WHERE faction_id=?", (uni_id,)):
    print(" ", r["id"], r["name"], r["points_cost"])
print("ironjawz count:", cur.execute("SELECT COUNT(*) c FROM units WHERE faction_id=75").fetchone()["c"])
print("kruleboyz count:", cur.execute("SELECT COUNT(*) c FROM units WHERE faction_id=76").fetchone()["c"])
con.close()
