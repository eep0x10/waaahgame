#!/usr/bin/env python3
import sqlite3
DB_PATH = '/app/instance/waaahgame.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("SELECT slug, name, image_path FROM units WHERE slug IN ('chaos-lord','chaos-lord-aos','beastrider','burning-chariot','disc-of-tzeentch','ethereal-steed','grot-scuttling','herald-of-nurgle','karkadrak','seeker-chariot','tzeentch-sorcerer-lord')")
for r in c.fetchall():
    print(r)
conn.close()
