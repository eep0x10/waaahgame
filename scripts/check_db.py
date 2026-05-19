import sqlite3
conn = sqlite3.connect('instance/waaahgame.db')
cur = conn.cursor()
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
print('Tables:', [r[0] for r in cur.fetchall()])
try:
    cur.execute("SELECT version_num FROM alembic_version")
    print('Alembic:', cur.fetchall())
except Exception as e:
    print('Alembic error:', e)
conn.close()
