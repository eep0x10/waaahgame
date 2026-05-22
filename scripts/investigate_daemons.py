import sqlite3

conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

print("=== 40K Chaos Daemons faction units ===")
rows = conn.execute("""
    SELECT u.id, u.slug, u.name, u.points_cost, f.code as faction, gs.code as gs
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE f.code = 'chaos-daemons'
    ORDER BY u.name
""").fetchall()
print(f"Count: {len(rows)}")
for r in rows:
    print(f"  {r['slug']} | {r['name']} | pts={r['points_cost']}")

print("\n=== AoS factions with 'daemon' in name/code ===")
rows2 = conn.execute("""
    SELECT f.id, f.code, f.name, gs.code as gs, COUNT(u.id) as unit_count
    FROM factions f
    JOIN game_systems gs ON gs.id=f.game_system_id
    LEFT JOIN units u ON u.faction_id=f.id
    WHERE gs.code='aos4' AND (f.name LIKE '%Daemon%' OR f.code LIKE '%daemon%' OR f.name LIKE '%Chaos%' OR f.code LIKE '%chaos%')
    GROUP BY f.id
""").fetchall()
for r in rows2:
    print(f"  id={r['id']} gs={r['gs']} code={r['code']} name={r['name']} units={r['unit_count']}")

print("\n=== AoS units with 'daemon' in name ===")
rows3 = conn.execute("""
    SELECT u.id, u.slug, u.name, u.points_cost, f.code as faction, gs.code as gs
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4' AND (u.name LIKE '%Bloodthirster%' OR u.name LIKE '%Lord of Change%' OR u.name LIKE '%Keeper of Secrets%' OR u.name LIKE '%Great Unclean%')
    ORDER BY u.name
""").fetchall()
print(f"Count: {len(rows3)}")
for r in rows3:
    print(f"  [{r['gs']}] {r['faction']} | {r['slug']} | {r['name']} | pts={r['points_cost']}")

print("\n=== All factions list ===")
all_facs = conn.execute("""
    SELECT f.id, f.code, f.name, gs.code as gs, COUNT(u.id) as cnt
    FROM factions f
    JOIN game_systems gs ON gs.id=f.game_system_id
    LEFT JOIN units u ON u.faction_id=f.id
    GROUP BY f.id
    ORDER BY gs.code, f.name
""").fetchall()
for r in all_facs:
    print(f"  [{r['gs']}] id={r['id']} {r['code']} | {r['name']} | {r['cnt']} units")
