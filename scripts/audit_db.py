import sqlite3
import json
import os

DB = "/app/instance/waaahgame.db"
con = sqlite3.connect(DB)
con.row_factory = sqlite3.Row

# 0. Tables
tables = con.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("TABLES:", [t[0] for t in tables])

# Check columns
cols = con.execute("PRAGMA table_info(units)").fetchall()
print("UNITS COLS:", [c[1] for c in cols])

# 1. Total
total = con.execute("SELECT COUNT(*) FROM units").fetchone()[0]
print(f"\n1. TOTAL UNITS: {total}")

# 2. 0 pts
zero_pts = con.execute("SELECT COUNT(*) FROM units WHERE points_cost = 0 OR points_cost IS NULL").fetchone()[0]
print(f"2. 0-pt or null pts: {zero_pts} ({round(100*zero_pts/total if total else 0, 1)}%)")

# 3. No image
no_img = con.execute("SELECT COUNT(*) FROM units WHERE image_path IS NULL OR image_path = ''").fetchone()[0]
print(f"3. No image_path: {no_img}")

# 4. Overlap: 0pts AND no image
overlap = con.execute("SELECT COUNT(*) FROM units WHERE (points_cost = 0 OR points_cost IS NULL) AND (image_path IS NULL OR image_path = '')").fetchone()[0]
print(f"4. 0pt + no image: {overlap}")

# 5. Missing warscroll JSON (all 3 null)
missing_ws = con.execute("""
    SELECT COUNT(*) FROM units
    WHERE (stats_json IS NULL OR stats_json = '' OR stats_json = 'null')
      AND (weapons_json IS NULL OR weapons_json = '' OR weapons_json = 'null')
      AND (abilities_json IS NULL OR abilities_json = '' OR abilities_json = 'null')
""").fetchone()[0]
print(f"5. Missing warscroll (all JSON null): {missing_ws}")

# 6. 0-pt units by keyword category
rows_zero = con.execute("""
    SELECT u.id, u.name, u.points_cost, u.keywords_json, gs.code as game_system
    FROM units u
    LEFT JOIN factions f ON u.faction_id = f.id
    LEFT JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE u.points_cost = 0 OR u.points_cost IS NULL
""").fetchall()
cats = {"Endless Spell/Manifestation": 0, "Faction Terrain": 0, "Invocation": 0,
        "Summoned": 0, "Legends": 0, "Battalion": 0, "Token/Free": 0, "Unknown/Regular": 0}
for r in rows_zero:
    kw = ""
    if r["keywords_json"]:
        try:
            kws = json.loads(r["keywords_json"])
            kw = " ".join(kws).upper() if isinstance(kws, list) else str(kws).upper()
        except:
            kw = str(r["keywords_json"]).upper()
    if "ENDLESS SPELL" in kw or "MANIFESTATION" in kw:
        cats["Endless Spell/Manifestation"] += 1
    elif "FACTION TERRAIN" in kw or "TERRAIN" in kw:
        cats["Faction Terrain"] += 1
    elif "INVOCATION" in kw:
        cats["Invocation"] += 1
    elif "SUMMONED" in kw:
        cats["Summoned"] += 1
    elif "LEGENDS" in kw or "LEGEND" in kw:
        cats["Legends"] += 1
    elif "BATTALION" in kw:
        cats["Battalion"] += 1
    elif "TOKEN" in kw or "FREE" in kw:
        cats["Token/Free"] += 1
    else:
        cats["Unknown/Regular"] += 1

print(f"\n6. 0-pt breakdown by keyword:")
for k, v in cats.items():
    if v > 0:
        print(f"   {k}: {v}")

# 7. Breakdown by game_system
print(f"\n7. 0-pt by game_system:")
sys_rows = con.execute("""
    SELECT gs.code, COUNT(*) c
    FROM units u
    LEFT JOIN factions f ON u.faction_id = f.id
    LEFT JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE u.points_cost = 0 OR u.points_cost IS NULL
    GROUP BY gs.code
""").fetchall()
for r in sys_rows:
    print(f"   {r[0]}: {r[1]}")

print(f"\n   No-image by game_system:")
sys_rows2 = con.execute("""
    SELECT gs.code, COUNT(*) c
    FROM units u
    LEFT JOIN factions f ON u.faction_id = f.id
    LEFT JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE u.image_path IS NULL OR u.image_path = ''
    GROUP BY gs.code
""").fetchall()
for r in sys_rows2:
    print(f"   {r[0]}: {r[1]}")

# Sample 0-pt unknown/regular (potential bugs)
print("\nAll 0-pt units sample (first 40):")
for r in rows_zero[:40]:
    kw = ""
    if r["keywords_json"]:
        try:
            kws = json.loads(r["keywords_json"])
            kw = " ".join(kws[:5]) if isinstance(kws, list) else str(r["keywords_json"])[:80]
        except:
            kw = str(r["keywords_json"])[:80]
    print(f"  [{r['game_system']}] {r['name']} | pts={r['points_cost']} | kw={kw[:80]}")

con.close()
