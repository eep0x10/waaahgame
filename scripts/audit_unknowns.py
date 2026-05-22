import sqlite3, json
con = sqlite3.connect("/app/instance/waaahgame.db")
con.row_factory = sqlite3.Row

rows_zero = con.execute("""
    SELECT u.id, u.name, u.points_cost, u.keywords_json, gs.code as game_system, f.name as faction_name
    FROM units u
    LEFT JOIN factions f ON u.faction_id = f.id
    LEFT JOIN game_systems gs ON f.game_system_id = gs.id
    WHERE u.points_cost = 0 OR u.points_cost IS NULL
""").fetchall()

cats = {"manifestation": [], "terrain": [], "summoned": [], "legends": [], "token": [], "unknown": []}
for r in rows_zero:
    kw = ""
    if r["keywords_json"]:
        try:
            kws = json.loads(r["keywords_json"])
            kw = " ".join(kws).upper() if isinstance(kws, list) else str(kws).upper()
        except:
            kw = str(r["keywords_json"]).upper()
    if "ENDLESS SPELL" in kw or "MANIFESTATION" in kw or "INVOCATION" in kw:
        cats["manifestation"].append(r)
    elif "FACTION TERRAIN" in kw or "TERRAIN" in kw:
        cats["terrain"].append(r)
    elif "SUMMONED" in kw:
        cats["summoned"].append(r)
    elif "LEGENDS" in kw or "LEGEND" in kw:
        cats["legends"].append(r)
    elif "TOKEN" in kw or "FREE" in kw:
        cats["token"].append(r)
    else:
        cats["unknown"].append(r)

print("=== UNKNOWN/UNCLASSIFIED 0-pt units (potential data bugs) ===")
for r in cats["unknown"]:
    kw = ""
    if r["keywords_json"]:
        try:
            kws = json.loads(r["keywords_json"])
            kw = ",".join(kws[:6]) if isinstance(kws, list) else str(r["keywords_json"])[:100]
        except:
            kw = str(r["keywords_json"])[:100]
    print(f"  [{r['game_system']}|{r['faction_name']}] {r['name']} | kw={kw}")

print(f"\nTotals: manifestation={len(cats['manifestation'])}, terrain={len(cats['terrain'])}, summoned={len(cats['summoned'])}, legends={len(cats['legends'])}, token={len(cats['token'])}, unknown={len(cats['unknown'])}")

# Also check 40k unknowns
print("\n=== 40K 0-pt breakdown ===")
for r in rows_zero:
    if r["game_system"] == "w40k10":
        kw = ""
        if r["keywords_json"]:
            try:
                kws = json.loads(r["keywords_json"])
                kw = ",".join(kws[:6]) if isinstance(kws, list) else str(r["keywords_json"])[:100]
            except:
                kw = str(r["keywords_json"])[:100]
        print(f"  [{r['faction_name']}] {r['name']} | kw={kw}")

con.close()
