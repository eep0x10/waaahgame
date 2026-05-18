"""One-shot: clear image_path for all units so scraper re-fetches."""
import sqlite3
conn = sqlite3.connect(r'C:\Users\eep0x10\dev\waaahgame\instance\waaahgame.db')
cur = conn.cursor()
cur.execute("UPDATE units SET image_path = NULL, image_source_url = NULL")
print(f'Cleared {cur.rowcount} rows')
conn.commit()
conn.close()
