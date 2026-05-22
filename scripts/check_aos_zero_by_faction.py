import sqlite3
conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

rows = conn.execute("""
    SELECT f.code, COUNT(*) as cnt
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4' AND u.points_cost=0
    GROUP BY f.id ORDER BY f.code
""").fetchall()
total_factions_with_zero = len(rows)
print(f"AoS factions with >0 zero-pts units: {total_factions_with_zero}")
for r in rows:
    print(f"  {r['cnt']:3d} | {r['code']}")

total_zero = sum(r['cnt'] for r in rows)
total_aos = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='aos4'").fetchone()[0]
print(f"\nTotal AoS zero: {total_zero}/{total_aos}")
