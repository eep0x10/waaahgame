"""Create all tables directly (bypasses alembic)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from app import create_app
from app.extensions import db

app = create_app()
with app.app_context():
    db.create_all()
    print('Tables created.')
    import sqlite3
    conn = sqlite3.connect('instance/waaahgame.db')
    cur = conn.cursor()
    cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
    print('Tables:', [r[0] for r in cur.fetchall()])
    conn.close()
