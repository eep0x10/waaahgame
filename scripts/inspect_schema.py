import sqlite3
con = sqlite3.connect("/app/instance/waaahgame.db")
for t in ["game_systems", "factions", "units"]:
    cols = con.execute(f"PRAGMA table_info({t})").fetchall()
    print(f"{t}: {[c[1] for c in cols]}")
    sample = con.execute(f"SELECT * FROM {t} LIMIT 2").fetchall()
    for row in sample:
        print(f"  {dict(zip([c[1] for c in cols], row))}")
con.close()
