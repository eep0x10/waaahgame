import sqlite3
import os

conn = sqlite3.connect('/app/instance/waaahgame.db')
conn.row_factory = sqlite3.Row

# IDs
skaven_id = 1
skaventide_id = 34

print("=== PRE-FIX STATE ===")
print(f"skaven units: {conn.execute('SELECT COUNT(*) FROM units WHERE faction_id=?', (skaven_id,)).fetchone()[0]}")
print(f"skaventide units: {conn.execute('SELECT COUNT(*) FROM units WHERE faction_id=?', (skaventide_id,)).fetchone()[0]}")

# Step 1: Move skaventide units to skaven faction, update image_path if it's skaventide/
skaventide_units = conn.execute("SELECT id, slug, name, image_path FROM units WHERE faction_id=?", (skaventide_id,)).fetchall()

print(f"\nMoving {len(skaventide_units)} skaventide units to skaven...")
for u in skaventide_units:
    new_image_path = u['image_path']
    if new_image_path and 'skaventide/' in new_image_path:
        new_image_path = new_image_path.replace('skaventide/', 'skaven/')
    conn.execute(
        "UPDATE units SET faction_id=?, image_path=? WHERE id=?",
        (skaven_id, new_image_path, u['id'])
    )
    print(f"  Moved: {u['name']} (id={u['id']}) img: {u['image_path']} -> {new_image_path}")

# Step 2: Also update image_source_url if any reference skaventide path
conn.execute(
    "UPDATE units SET image_source_url = REPLACE(image_source_url, '/skaventide/', '/skaven/') WHERE faction_id=? AND image_source_url LIKE '%/skaventide/%'",
    (skaven_id,)
)

conn.commit()

print(f"\n=== POST-MOVE STATE ===")
print(f"skaven units: {conn.execute('SELECT COUNT(*) FROM units WHERE faction_id=?', (skaven_id,)).fetchone()[0]}")
print(f"skaventide units: {conn.execute('SELECT COUNT(*) FROM units WHERE faction_id=?', (skaventide_id,)).fetchone()[0]}")

# Step 3: Delete the skaventide faction row
print("\nDeleting skaventide faction row...")
conn.execute("DELETE FROM factions WHERE id=?", (skaventide_id,))
conn.commit()

# Verify
remaining = conn.execute("SELECT * FROM factions WHERE slug='skaventide'").fetchall()
print(f"skaventide faction remaining: {len(remaining)}")

# Also check the faction code for skaven
skaven_fac = conn.execute("SELECT * FROM factions WHERE id=?", (skaven_id,)).fetchone()
print(f"\nskaven faction: id={skaven_fac['id']} code={skaven_fac['code']} name={skaven_fac['name']}")
print(f"skaven total units now: {conn.execute('SELECT COUNT(*) FROM units WHERE faction_id=?', (skaven_id,)).fetchone()[0]}")

print("\nDone!")
