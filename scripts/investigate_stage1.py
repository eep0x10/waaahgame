import sqlite3

conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

print("=== SLUG COLLISIONS ===")
rows = conn.execute("SELECT slug, COUNT(*) as cnt FROM units GROUP BY slug HAVING COUNT(*) > 1 ORDER BY cnt DESC").fetchall()
for r in rows:
    print(f"  {r['slug']}: {r['cnt']}")
print(f"Total collisions: {len(rows)}")

print("\n=== GAME SYSTEMS ===")
gs = conn.execute("SELECT id, code, name FROM game_systems").fetchall()
for r in gs:
    print(f"  id={r['id']} code={r['code']} name={r['name']}")

print("\n=== FACTIONS (chaos/daemon relevant) ===")
facs = conn.execute("SELECT f.id, f.code, f.slug, f.name, gs.code as gs_code FROM factions f JOIN game_systems gs ON gs.id=f.game_system_id WHERE f.code LIKE '%daemon%' OR f.code LIKE '%chaos%' OR f.name LIKE '%daemon%' ORDER BY gs.code, f.slug").fetchall()
for r in facs:
    print(f"  id={r['id']} gs={r['gs_code']} code={r['code']} name={r['name']}")

print("\n=== DUPLICATE UNITS DETAIL ===")
for r in rows:
    slug = r['slug']
    units = conn.execute("SELECT u.id, u.slug, u.name, u.points_cost, f.code as faction, gs.code as gs FROM units u JOIN factions f ON f.id=u.faction_id JOIN game_systems gs ON gs.id=f.game_system_id WHERE u.slug=?", (slug,)).fetchall()
    for u in units:
        print(f"  slug={u['slug']} id={u['id']} gs={u['gs']} faction={u['faction']} pts={u['points_cost']}")

print("\n=== FACTIONS skaventide/skaven ===")
facs2 = conn.execute("SELECT f.id, f.code, f.slug, f.name, gs.code as gs_code FROM factions f JOIN game_systems gs ON gs.id=f.game_system_id WHERE f.slug IN ('skaventide','skaven') OR f.code IN ('skaventide','skaven')").fetchall()
for r in facs2:
    print(f"  id={r['id']} gs={r['gs_code']} code={r['code']} slug={r['slug']} name={r['name']}")

print("\n=== UNIT COUNTS BY FACTION (skaven/skaventide) ===")
for r in facs2:
    cnt = conn.execute("SELECT COUNT(*) as cnt FROM units WHERE faction_id=?", (r['id'],)).fetchone()['cnt']
    print(f"  faction_id={r['id']} {r['code']}: {cnt} units")

print("\n=== UNITS WITH points_cost=0 ===")
cnt0 = conn.execute("SELECT COUNT(*) as cnt FROM units WHERE points_cost=0").fetchone()['cnt']
print(f"  Total units with points_cost=0: {cnt0}")
total = conn.execute("SELECT COUNT(*) as cnt FROM units").fetchone()['cnt']
print(f"  Total units: {total}")

print("\n=== SCHEMA units table ===")
schema = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='units'").fetchone()
print(schema['sql'])
