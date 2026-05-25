"""Delete phantom units not in PDF + fix model_count anomalies."""
import sqlite3
DB = "/app/instance/waaahgame.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

# Verify no Sequitors plural before nuking singular
seq_plural = cur.execute("SELECT id, name, points_cost, model_count, unit_category FROM units WHERE faction_id=(SELECT id FROM factions WHERE slug='stormcast-eternals') AND name LIKE 'Sequitors%'").fetchall()
print("Sequitors plural in DB:", [(r['id'], r['name'], r['points_cost']) for r in seq_plural])

# Phantoms to delete (verified against PDF)
phantoms = [
    (640,  "SCE singular 'Annihilator'"),
    (660,  "SCE singular 'Liberator'"),
    (669,  "SCE singular 'Praetor'"),
    (682,  "SCE singular 'Vanquisher'"),
    (683,  "SCE singular 'Vigilor'"),
    (684,  "SCE singular 'Vindictor'"),
    (675,  "SCE singular 'Sequitor' (legends)"),
    (318,  "Skaven singular 'Stormfiend' (wrong pts/name)"),
    (1758, "Gloomspite 'Troggboss' (canonical is Dankhold Troggboss)"),
    (1738, "StD 'Archaon the Everchosen' duplicate (canon=1702)"),
    (1739, "DoT 'Magister' 90 duplicate (canon=1688)"),
    (1740, "DoT 'Tzaangor Shaman' 120 duplicate (canon=1690)"),
    (1726, "Sylvaneth 'Kurnoth Hunters with Greatswords' phantom (PDF: 'with Kurnoth Greatswords')"),
    (1727, "Sylvaneth 'Kurnoth Hunters with Greatbows' phantom"),
    (1735, "DoK generic 'Sisters of Slaughter' (PDF only has 2 variants)"),
]
for uid, reason in phantoms:
    row = cur.execute("SELECT name, points_cost FROM units WHERE id=?", (uid,)).fetchone()
    if row:
        print(f"DELETE id={uid} {row['name']!r}@{row['points_cost']} — {reason}")
        cur.execute("DELETE FROM units WHERE id=?", (uid,))
    else:
        print(f"skip id={uid} not found")

# Fix model_count for id=1245
r = cur.execute("SELECT name, model_count FROM units WHERE id=1245").fetchone()
if r:
    print(f"FIX id=1245 {r['name']!r} model_count {r['model_count']} -> 3")
    cur.execute("UPDATE units SET model_count=3 WHERE id=1245")

con.commit()

# Audit
print("\n=== Per Faction after purge ===")
for r in cur.execute("SELECT f.slug, COUNT(u.id) c FROM factions f LEFT JOIN units u ON u.faction_id=f.id WHERE f.game_system_id=1 GROUP BY f.id ORDER BY f.slug"):
    print(f"  {r['slug']:<32} {r['c']:>3}")
total = cur.execute("SELECT COUNT(*) c FROM units u JOIN factions f ON u.faction_id=f.id WHERE f.game_system_id=1").fetchone()['c']
print(f"\nTOTAL aos4 units: {total}")
con.close()
