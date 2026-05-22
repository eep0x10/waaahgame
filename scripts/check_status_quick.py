import sqlite3
conn = sqlite3.connect('/app/instance/waaahgame.db')
aos_zero = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='aos4' AND u.points_cost=0").fetchone()[0]
aos_total = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='aos4'").fetchone()[0]
k40_zero = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='w40k10' AND u.points_cost=0").fetchone()[0]
k40_total = conn.execute("SELECT COUNT(*) FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE gs.code='w40k10'").fetchone()[0]
print(f'AoS: {aos_zero}/{aos_total} at 0 pts')
print(f'40K: {k40_zero}/{k40_total} at 0 pts')
print(f'Overall: {aos_zero+k40_zero}/{aos_total+k40_total} at 0 pts')
