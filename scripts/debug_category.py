import sqlite3
con = sqlite3.connect("/app/instance/waaahgame.db")
con.row_factory = sqlite3.Row
rows = con.execute("SELECT name, unit_category, points_cost FROM units WHERE faction_id IN (SELECT id FROM factions WHERE slug='beasts-of-chaos') ORDER BY name").fetchall()
print(f"Beasts of Chaos units: {len(rows)}")
for r in rows:
    print(f"  {r['unit_category']:15} {r['name']}")
# Check category distribution
print("\nAll category counts:")
for row in con.execute("SELECT unit_category, COUNT(*) c FROM units GROUP BY unit_category").fetchall():
    print(f"  {row[0]}: {row[1]}")
con.close()
