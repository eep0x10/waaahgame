"""Investigate suspicious cases flagged by reconciliation agent."""
import sqlite3
DB = "/app/instance/waaahgame.db"
con = sqlite3.connect(DB); con.row_factory = sqlite3.Row; cur = con.cursor()

def f(slug):
    return cur.execute("SELECT id FROM factions WHERE slug=? AND game_system_id=1", (slug,)).fetchone()["id"]

def show(faction_slug, name_like):
    fid = f(faction_slug)
    print(f"\n[{faction_slug}] LIKE '{name_like}':")
    for r in cur.execute(
        "SELECT id, name, points_cost, model_count, unit_category FROM units WHERE faction_id=? AND name LIKE ?",
        (fid, name_like)
    ):
        print(f"  id={r['id']} {r['name']!r} pts={r['points_cost']} models={r['model_count']} cat={r['unit_category']}")

# SCE singular-named phantoms
for n in ['%Annihilator%', '%Liberator%', '%Praetor%', '%Vigilor%', '%Vindictor%', '%Vanquisher%', '%Sequitor%']:
    show('stormcast-eternals', n)

# Skaven Stormfiend
show('skaven', '%Stormfiend%')

# Gloomspite Troggboss
show('gloomspite-gitz', '%Trogg%')

# StD Archaon
show('slaves-to-darkness', '%Archaon%')

# DoT Magister, Tzaangor Shaman
show('disciples-of-tzeentch', '%Magister%')
show('disciples-of-tzeentch', '%Tzaangor%')

# DoK Sisters of Slaughter
show('daughters-of-khaine', '%Sister%')

# Sylvaneth Kurnoth Hunters
show('sylvaneth', '%Kurnoth%')
con.close()
