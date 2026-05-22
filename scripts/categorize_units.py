"""
Categorize units: regular | manifestation | legends | incomplete
Run AFTER alembic upgrade adds unit_category column.
"""
import sqlite3
import json
import shutil
import os

DB = "/app/instance/waaahgame.db"
BAK = "/app/instance/waaahgame.db.bak_pre_categorize"

# Backup
if not os.path.exists(BAK):
    shutil.copy2(DB, BAK)
    print(f"Backup created: {BAK}")
else:
    print(f"Backup already exists: {BAK} — skipping copy")

con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# Ensure column exists (idempotent)
cols = [c[1] for c in con.execute("PRAGMA table_info(units)").fetchall()]
if "unit_category" not in cols:
    con.execute("ALTER TABLE units ADD COLUMN unit_category TEXT NOT NULL DEFAULT 'regular'")
    con.commit()
    print("Added unit_category column via raw ALTER TABLE")

rows = con.execute("SELECT id, name, points_cost, keywords_json FROM units").fetchall()

counts = {"regular": 0, "manifestation": 0, "legends": 0, "incomplete": 0}
updates = []

# These units are known legends in 40K that have [Legends] in name
# AoS incomplete: real units (Hero/Battleline etc) with 0 pts and no keywords signal
LEGENDS_NAMES_40K = {"[Legends]"}  # detected by substring

# AoS units that are summoned companions (0pts, blank keywords, specific roles)
COMPANION_NAMES = {
    "Deathrunner", "Riptooth", "Packmaster", "Blight Templar",
    "Warpspark Weapon Battery", "Razordon", "Salamander", "Skink Handler",
    "Branchwraith",
}

for r in rows:
    uid = r["id"]
    name = r["name"]
    pts = r["points_cost"]
    kw_raw = r["keywords_json"] or "[]"
    try:
        kws = json.loads(kw_raw)
        kw = " ".join(kws).upper() if isinstance(kws, list) else str(kws).upper()
    except Exception:
        kw = str(kw_raw).upper()

    cat = "regular"

    # Manifestation / Endless Spell / Faction Terrain / Invocation
    if any(x in kw for x in ("ENDLESS SPELL", "MANIFESTATION", "INVOCATION", "FACTION TERRAIN")):
        cat = "manifestation"

    # Legends — keyword-based OR name contains [Legends]
    elif "LEGENDS" in kw or "LEGEND" in kw or "[LEGENDS]" in name.upper():
        cat = "legends"

    # 40K units where name ends with [Legends]
    elif name.endswith("[Legends]") or name.endswith("[Legends]"):
        cat = "legends"

    # AoS companion/summoned models (blank keywords, 0pts, known names)
    elif name in COMPANION_NAMES:
        cat = "manifestation"  # treat as non-regular — no pts expected

    # Real units that are 0pts with no keyword justification = incomplete
    elif pts == 0 and cat == "regular":
        # Heroes with UNIQUE keyword that have 0pts → incomplete data
        if "UNIQUE" in kw or "HERO" in kw or "BATTLELINE" in kw:
            cat = "incomplete"
        # 40K regular units with actual keywords but 0pts
        elif "FACTION:" in kw and pts == 0:
            cat = "incomplete"
        # Still unknown but 0pts → incomplete
        else:
            cat = "incomplete"

    updates.append((cat, uid))
    counts[cat] += 1

con.executemany("UPDATE units SET unit_category = ? WHERE id = ?", updates)
con.commit()
print(f"\nCategorized {len(updates)} units:")
for k, v in counts.items():
    print(f"  {k}: {v}")

# Show incomplete list
print("\nUnits marked 'incomplete':")
incs = con.execute("SELECT name, points_cost, keywords_json FROM units WHERE unit_category = 'incomplete' ORDER BY name").fetchall()
for r in incs:
    print(f"  {r['name']} pts={r['points_cost']}")

# Show legends
print("\nUnits marked 'legends':")
legs = con.execute("SELECT name, points_cost FROM units WHERE unit_category = 'legends' ORDER BY name").fetchall()
for r in legs:
    print(f"  {r['name']}")

con.close()
