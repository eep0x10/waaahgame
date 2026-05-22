#!/usr/bin/env python3
import sqlite3
DB='/app/instance/waaahgame.db'
conn=sqlite3.connect(DB)
c=conn.cursor()
c.execute('SELECT COUNT(*) FROM units')
total=c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM units u JOIN factions f ON u.faction_id=f.id JOIN game_systems gs ON f.game_system_id=gs.id WHERE gs.code='aos4'")
aos=c.fetchone()[0]
print(f'Total units: {total}, AoS: {aos}')
conn.close()
