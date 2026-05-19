"""One-shot script to update image_path for aggradon-lancers and sunblood-pack."""
import sqlite3
import os

db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'instance', 'waaahgame.db')
con = sqlite3.connect(db_path)
cur = con.cursor()

updates = [
    ('units/seraphon/aggradon-lancers.svg', 'aggradon-lancers'),
    ('units/seraphon/sunblood-pack.svg', 'sunblood-pack'),
]

for image_path, slug in updates:
    cur.execute("UPDATE units SET image_path = ? WHERE slug = ?", (image_path, slug))
    print(f"Updated {slug} -> {image_path} (rows affected: {cur.rowcount})")

con.commit()
con.close()
print("Done.")
