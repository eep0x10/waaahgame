import sqlite3
conn = sqlite3.connect('/app/instance/waaahgame.db')
cur = conn.cursor()

# Check remaining Beasts of Chaos and Bonesplitterz units
for faction in ['Beasts of Chaos', 'Bonesplitterz']:
    cur.execute("""
        SELECT u.id, u.name, u.unit_category, u.points_cost
        FROM units u JOIN factions f ON u.faction_id=f.id
        WHERE f.name = ?
    """, (faction,))
    rows = cur.fetchall()
    print(f"\n{faction} ({len(rows)} remaining):")
    for r in rows:
        print(f"  id={r[0]} name='{r[1]}' cat={r[2]} pts={r[3]}")

conn.close()
