#!/usr/bin/env python3
import sqlite3, os
DB_PATH = '/app/instance/waaahgame.db'
conn = sqlite3.connect(DB_PATH)
c = conn.cursor()
c.execute("UPDATE units SET image_path='units/soulblight-gravelords/vampire-lord.webp' WHERE slug='vampire-lord'")
conn.commit()
c.execute("SELECT slug, image_path FROM units WHERE slug='vampire-lord'")
print(c.fetchone())
conn.close()
print("Done.")
