import sqlite3

conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

# Get faction IDs
skaven = conn.execute("SELECT id FROM factions WHERE code='skaven'").fetchone()
skaventide = conn.execute("SELECT id FROM factions WHERE code='skaventide'").fetchone()
skaven_id = skaven['id']
skaventide_id = skaventide['id']
print(f"skaven_id={skaven_id}, skaventide_id={skaventide_id}")

# Get all units for both
skaven_units = {r['name']: dict(r) for r in conn.execute("SELECT * FROM units WHERE faction_id=?", (skaven_id,)).fetchall()}
skaventide_units = {r['name']: dict(r) for r in conn.execute("SELECT * FROM units WHERE faction_id=?", (skaventide_id,)).fetchall()}

print(f"\nskaven units ({len(skaven_units)}): {sorted(skaven_units.keys())}")
print(f"\nskaventide units ({len(skaventide_units)}): {sorted(skaventide_units.keys())}")

# Find overlaps by name
overlap_names = set(skaven_units.keys()) & set(skaventide_units.keys())
print(f"\nOverlapping by name ({len(overlap_names)}): {sorted(overlap_names)}")

# Find skaventide-only (need to move to skaven)
skaventide_only = set(skaventide_units.keys()) - set(skaven_units.keys())
print(f"\nSkaventide-only units ({len(skaventide_only)}): {sorted(skaventide_only)}")

# Check image_path on overlapping rows
print("\n=== OVERLAP detail (skaven vs skaventide) ===")
for name in sorted(overlap_names):
    s = skaven_units[name]
    sv = skaventide_units[name]
    print(f"  {name}:")
    print(f"    skaven:     id={s['id']} slug={s['slug']} pts={s['points_cost']} img={s['image_path']}")
    print(f"    skaventide: id={sv['id']} slug={sv['slug']} pts={sv['points_cost']} img={sv['image_path']}")

print("\n=== SKAVENTIDE-ONLY detail ===")
for name in sorted(skaventide_only):
    sv = skaventide_units[name]
    print(f"  {name}: id={sv['id']} slug={sv['slug']} pts={sv['points_cost']} img={sv['image_path']}")
