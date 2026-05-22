import sqlite3
conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

# AoS zero pts breakdown by faction
print("=== AoS units with pts=0 by faction ===")
rows = conn.execute("""
    SELECT f.code, f.name, COUNT(*) as cnt
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4' AND u.points_cost=0
    GROUP BY f.id
    ORDER BY cnt DESC
""").fetchall()
for r in rows:
    print(f"  {r['cnt']:3d} | {r['code']}")

total_aos_zero = sum(r['cnt'] for r in rows)
total_aos = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4'
""").fetchone()['cnt']
print(f"\nAoS: {total_aos_zero}/{total_aos} at 0 pts")

# 40K remaining
k40_zero = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='w40k10' AND u.points_cost=0
""").fetchone()['cnt']
k40_total = conn.execute("""
    SELECT COUNT(*) as cnt FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='w40k10'
""").fetchone()['cnt']
print(f"\n40K: {k40_zero}/{k40_total} at 0 pts")

# Total
print(f"\nOverall: {total_aos_zero + k40_zero}/{total_aos + k40_total} at 0 pts")

# Sample AoS zero units - list them
print("\n=== Sample AoS units at 0 pts (first 50) ===")
sample = conn.execute("""
    SELECT u.slug, u.name, f.code as faction
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4' AND u.points_cost=0
    ORDER BY f.code, u.name
    LIMIT 50
""").fetchall()
for r in sample:
    print(f"  [{r['faction']}] {r['slug']} | {r['name']}")
