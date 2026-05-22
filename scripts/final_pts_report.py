import sqlite3
conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

print("=== FINAL POINTS STATUS ===")

# AoS overall
aos_total = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='aos4'").fetchone()[0]
aos_zero = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='aos4' AND u.points_cost=0").fetchone()[0]
print(f"AoS: {aos_zero}/{aos_total} still at 0 pts ({int(100*(aos_total-aos_zero)/aos_total)}% have pts)")

# 40K overall
k40_total = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='w40k10'").fetchone()[0]
k40_zero = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='w40k10' AND u.points_cost=0").fetchone()[0]
print(f"40K: {k40_zero}/{k40_total} still at 0 pts ({int(100*(k40_total-k40_zero)/k40_total)}% have pts)")

print(f"\nOverall: {aos_zero+k40_zero}/{aos_total+k40_total} at 0 pts")

print("\n=== AoS zero by faction ===")
rows = conn.execute("""
    SELECT f.code, COUNT(*) as cnt
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='aos4' AND u.points_cost=0
    GROUP BY f.id ORDER BY cnt DESC
""").fetchall()
for r in rows:
    print(f"  {r['cnt']:3d} | {r['code']}")

print("\n=== 40K zero units ===")
rows2 = conn.execute("""
    SELECT u.slug, u.name, f.code as faction
    FROM units u
    JOIN factions f ON f.id=u.faction_id
    JOIN game_systems gs ON gs.id=f.game_system_id
    WHERE gs.code='w40k10' AND u.points_cost=0
    ORDER BY f.code, u.name
""").fetchall()
for r in rows2:
    print(f"  [{r['faction']}] {r['slug']} | {r['name']}")
