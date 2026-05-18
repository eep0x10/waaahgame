import sqlite3
conn = sqlite3.connect(r'C:\Users\eep0x10\dev\waaahgame\instance\waaahgame.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
rows = cur.fetchall()
print('Tables:', [r[0] for r in rows])
conn.close()
