#!/usr/bin/env python3
"""Triple-source canonical roster reconciliation for AoS 4e and 40K 10e."""
import json, re, os
from collections import defaultdict

CACHE = "c:/Users/eep0x10/dev/waaahgame/scripts/cache"

import html as _html_mod

def slugify(name):
    # Decode HTML entities first (BSData uses &apos; etc.)
    n = _html_mod.unescape(name)
    n = n.lower()
    n = re.sub(r"^the\s+", "", n)
    n = re.sub(r"[',\.\-\(\)\[\]!&/\\+]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    n = n.replace(" ", "-")
    return n

# ============================================================
# LOAD SOURCES
# ============================================================

# Wahapedia AoS
with open(f"{CACHE}/wahapedia_aos.json") as f:
    waha_raw = json.load(f)

waha_aos = {}
for fac_slug, data in waha_raw.items():
    waha_aos[fac_slug] = {}
    # Handle both list format and dict-with-units format
    if isinstance(data, list):
        units = data
    elif isinstance(data, dict):
        units = data.get("units", [])
    else:
        units = []
    for u in units:
        if isinstance(u, str):
            waha_aos[fac_slug][slugify(u)] = u
        elif isinstance(u, dict):
            nm = u.get("name") or u.get("title", "")
            if nm:
                waha_aos[fac_slug][slugify(nm)] = nm

# BSData AoS
with open(f"{CACHE}/bsdata_aos.json") as f:
    bs_raw_aos = json.load(f)

BS_FAC_MAP_AOS = {
    "beasts-of-chaos": "beasts-of-chaos",
    "blades-of-khorne": "blades-of-khorne",
    "bonesplitterz": "bonesplitterz",
    "cities-of-sigmar": "cities-of-sigmar",
    "daughters-of-khaine": "daughters-of-khaine",
    "disciples-of-tzeentch": "disciples-of-tzeentch",
    "flesh-eater-courts": "flesh-eater-courts",
    "fyreslayers": "fyreslayers",
    "gloomspite-gitz": "gloomspite-gitz",
    "hedonites-of-slaanesh": "hedonites-of-slaanesh",
    "helsmiths-of-hashut": "helsmiths-of-hashut",
    "idoneth-deepkin": "idoneth-deepkin",
    "ironjawz": "ironjawz",
    "kharadron-overlords": "kharadron-overlords",
    "kruleboyz": "kruleboyz",
    "lumineth-realm-lords": "lumineth-realm-lords",
    "maggotkin-of-nurgle": "maggotkin-of-nurgle",
    "nighthaunt": "nighthaunt",
    "ogor-mawtribes": "ogor-mawtribes",
    "orruk-warclans": "orruk-warclans",
    "ossiarch-bonereapers": "ossiarch-bonereapers",
    "seraphon": "seraphon",
    "skaven": "skaven",
    "slaves-to-darkness": "slaves-to-darkness",
    "sons-of-behemat": "sons-of-behemat",
    "soulblight-gravelords": "soulblight-gravelords",
    "stormcast-eternals": "stormcast-eternals",
    "sylvaneth": "sylvaneth",
    "slaves-to-darkness---legion-of-the-first-prince": "slaves-to-darkness",
    "disciples-of-tzeentch---pyrofane-cult": "disciples-of-tzeentch",
    "stormcast-eternals---astral-templars": "stormcast-eternals",
}

bsdata_aos = defaultdict(dict)
for bs_slug, units in bs_raw_aos.items():
    canonical = BS_FAC_MAP_AOS.get(bs_slug)
    if canonical and units:
        for u in units:
            bsdata_aos[canonical][slugify(u)] = u

# Lexicanum AoS
with open(f"{CACHE}/lexicanum_manifest.json") as f:
    lex_raw = json.load(f)

lex_units_raw = lex_raw["units"]

LEX_FAC_MAP = {
    "Brayherds": "beasts-of-chaos",
    "Beasts of Chaos": "beasts-of-chaos",
    "Blades of Khorne": "blades-of-khorne",
    "Daemons of Khorne": "blades-of-khorne",
    "Khorne Bloodbound": "blades-of-khorne",
    "Bonesplitterz": "bonesplitterz",
    "Cities of Sigmar": "cities-of-sigmar",
    "Collegiate Arcane": "cities-of-sigmar",
    "Darkling Covens": "cities-of-sigmar",
    "Devoted of Sigmar": "cities-of-sigmar",
    "Dispossessed": "cities-of-sigmar",
    "Freeguild": "cities-of-sigmar",
    "Ironweld Arsenal": "cities-of-sigmar",
    "Lion Rangers": "cities-of-sigmar",
    "Order Serpentis": "cities-of-sigmar",
    "Scourge Privateers": "cities-of-sigmar",
    "Shadowblades": "cities-of-sigmar",
    "Daughters of Khaine": "daughters-of-khaine",
    "Disciples of Tzeentch": "disciples-of-tzeentch",
    "Tzeentch Arcanites": "disciples-of-tzeentch",
    "Daemons of Tzeentch": "disciples-of-tzeentch",
    "Flesh-Eater Courts": "flesh-eater-courts",
    "Fyreslayers": "fyreslayers",
    "Gloomspite Gitz": "gloomspite-gitz",
    "Moonclan Grots": "gloomspite-gitz",
    "Gitmob Grots": "gloomspite-gitz",
    "Spiderfang Grots": "gloomspite-gitz",
    "Troggherds": "gloomspite-gitz",
    "Aleguzzler Gargants": "gloomspite-gitz",
    "Hedonites of Slaanesh": "hedonites-of-slaanesh",
    "Slaanesh Sybarites": "hedonites-of-slaanesh",
    "Daemons of Slaanesh": "hedonites-of-slaanesh",
    "Idoneth Deepkin": "idoneth-deepkin",
    "Ironjawz": "ironjawz",
    "Kharadron Overlords": "kharadron-overlords",
    "Maggotkin of Nurgle": "maggotkin-of-nurgle",
    "Daemons of Nurgle": "maggotkin-of-nurgle",
    "Nurgle Rotbringers": "maggotkin-of-nurgle",
    "Nighthaunt": "nighthaunt",
    "Ogor Mawtribes": "ogor-mawtribes",
    "Beastclaw Raiders": "ogor-mawtribes",
    "Gutbusters": "ogor-mawtribes",
    "Firebellies": "ogor-mawtribes",
    "Maneaters": "ogor-mawtribes",
    "Orruk Warclans": "orruk-warclans",
    "Ossiarch Bonereapers": "ossiarch-bonereapers",
    "Seraphon": "seraphon",
    "Skaven": "skaven",
    "Skaventide": "skaven",
    "Masterclan": "skaven",
    "Eshin": "skaven",
    "Moulder": "skaven",
    "Skryre": "skaven",
    "Pestilens": "skaven",
    "Verminus": "skaven",
    "Slaves to Darkness": "slaves-to-darkness",
    "Warriors of Chaos": "slaves-to-darkness",
    "Everchosen": "slaves-to-darkness",
    "Monsters of Chaos": "slaves-to-darkness",
    "Thunderscorn": "slaves-to-darkness",
    "Warherds": "slaves-to-darkness",
    "Daemons of Chaos": "slaves-to-darkness",
    "Soulblight Gravelords": "soulblight-gravelords",
    "Beasts of the Grave": "soulblight-gravelords",
    "Deadwalkers": "soulblight-gravelords",
    "Deathlords": "soulblight-gravelords",
    "Deathmages": "soulblight-gravelords",
    "Deathrattle": "soulblight-gravelords",
    "Soulblight": "soulblight-gravelords",
    "Stormcast Eternals": "stormcast-eternals",
    "Sylvaneth": "sylvaneth",
}

lex_aos = defaultdict(dict)
for unit_slug, unit_data in lex_units_raw.items():
    title = unit_data.get("title", unit_slug)
    factions = unit_data.get("factions", [])
    assigned = False
    for lex_fac in factions:
        canonical = LEX_FAC_MAP.get(lex_fac)
        if canonical:
            lex_aos[canonical][slugify(title)] = title
            assigned = True
            # Don't break - unit can appear in multiple mapped factions

print("Sources loaded:")
print(f"  Wahapedia AoS: {sum(len(v) for v in waha_aos.values())} units, {len(waha_aos)} factions")
print(f"  BSData AoS:    {sum(len(v) for v in bsdata_aos.values())} units, {len(bsdata_aos)} factions")
print(f"  Lexicanum AoS: {sum(len(v) for v in lex_aos.values())} units, {len(lex_aos)} factions")

# ============================================================
# AOS TRIPLE-SOURCE RECONCILIATION
# ============================================================
all_aos_factions = sorted(set(list(waha_aos.keys()) + list(bsdata_aos.keys()) + list(lex_aos.keys())))

canonical_aos = {}
waha_only = []
bs_only = []
lex_only = []

for fac_slug in all_aos_factions:
    waha_u = waha_aos.get(fac_slug, {})
    bs_u = bsdata_aos.get(fac_slug, {})
    lex_u = lex_aos.get(fac_slug, {})

    superset = set(list(waha_u.keys()) + list(bs_u.keys()) + list(lex_u.keys()))

    confirmed = []
    wonly = []
    bonly = []
    lonly = []

    for norm in superset:
        srcs = []
        nm = None
        if norm in waha_u:
            srcs.append("wahapedia")
            nm = waha_u[norm]
        if norm in bs_u:
            srcs.append("bsdata")
            if not nm:
                nm = bs_u[norm]
        if norm in lex_u:
            srcs.append("lexicanum")
            if not nm:
                nm = lex_u[norm]

        entry = {"name": nm, "slug": norm, "sources": srcs}
        if len(srcs) >= 2:
            confirmed.append(entry)
        elif srcs == ["wahapedia"]:
            wonly.append(entry)
        elif srcs == ["bsdata"]:
            bonly.append(entry)
        elif srcs == ["lexicanum"]:
            lonly.append(entry)

        if len(srcs) == 1:
            if "wahapedia" in srcs:
                waha_only.append({"name": nm, "slug": norm, "faction": fac_slug})
            elif "bsdata" in srcs:
                bs_only.append({"name": nm, "slug": norm, "faction": fac_slug})
            elif "lexicanum" in srcs:
                lex_only.append({"name": nm, "slug": norm, "faction": fac_slug})

    canonical_aos[fac_slug] = {
        "name": fac_slug.replace("-", " ").title(),
        "slug": fac_slug,
        "units": confirmed,
        "waha_only": wonly,
        "bs_only": bonly,
        "lex_only": lonly,
        "source_coverage": {
            "wahapedia": bool(waha_u),
            "bsdata": bool(bs_u),
            "lexicanum": bool(lex_u),
        }
    }

confirmed_count_aos = sum(len(v["units"]) for v in canonical_aos.values())
print(f"\nAoS Results:")
print(f"  Confirmed (>=2 sources): {confirmed_count_aos}")
print(f"  Wahapedia-only:          {len(waha_only)}")
print(f"  BSData-only:             {len(bs_only)}")
print(f"  Lexicanum-only:          {len(lex_only)}")
print(f"  Waha total input:        {sum(len(v) for v in waha_aos.values())}")

# per-faction breakdown
print("\nPer-faction (confirmed | waha-only | bs-only | lex-only):")
for fac_slug in sorted(canonical_aos.keys()):
    d = canonical_aos[fac_slug]
    print(f"  {fac_slug}: {len(d['units'])} conf | {len(d['waha_only'])} waha | {len(d['bs_only'])} bs | {len(d['lex_only'])} lex")

# Save canonical AoS
out_aos = {}
for fac_slug, data in canonical_aos.items():
    out_aos[fac_slug] = {
        "name": data["name"],
        "slug": data["slug"],
        "units": [{"name": u["name"], "slug": u["slug"], "sources": u["sources"]} for u in data["units"]],
        "source_coverage": data["source_coverage"],
    }
with open(f"{CACHE}/canonical_aos_verified.json", "w", encoding="utf-8") as f:
    json.dump(out_aos, f, indent=2, ensure_ascii=False)
print("\nSaved canonical_aos_verified.json")

with open(f"{CACHE}/aos_waha_only.json", "w", encoding="utf-8") as f:
    json.dump(waha_only, f, indent=2, ensure_ascii=False)

# ============================================================
# 40K DOUBLE-SOURCE (BSData + Wahapedia)
# ============================================================
with open(f"{CACHE}/wahapedia_40k.json") as f:
    waha_40k_raw = json.load(f)

with open(f"{CACHE}/bsdata_40k.json") as f:
    bs_40k_raw = json.load(f)

# Wahapedia 40k - inspect structure
waha_40k = {}
for fac_slug, data in waha_40k_raw.items():
    waha_40k[fac_slug] = {}
    if isinstance(data, list):
        units = data
    elif isinstance(data, dict):
        units = data.get("units", [])
    else:
        units = []
    for u in units:
        if isinstance(u, str):
            waha_40k[fac_slug][slugify(u)] = u
        elif isinstance(u, dict):
            nm = u.get("name") or u.get("title", "")
            if nm:
                waha_40k[fac_slug][slugify(nm)] = nm

# BSData 40k
BS_FAC_MAP_40K = {
    "chaos---chaos-space-marines": "chaos-space-marines",
    "chaos---death-guard": "death-guard",
    "chaos---emperors-children": "emperors-children",
    "chaos---thousand-sons": "thousand-sons",
    "chaos---world-eaters": "world-eaters",
    "genestealer-cults": "genestealer-cults",
    "adepta-sororitas": "adepta-sororitas",
    "adeptus-custodes": "adeptus-custodes",
    "adeptus-mechanicus": "adeptus-mechanicus",
    "agents-of-the-imperium": "agents-of-the-imperium",
    "black-templars": "black-templars",
    "blood-angels": "blood-angels",
    "dark-angels": "dark-angels",
    "deathwatch": "deathwatch",
    "grey-knights": "grey-knights",
    "space-marines": "space-marines",
    "space-wolves": "space-wolves",
    "ultramarines": "ultramarines",
    "leagues-of-votann": "leagues-of-votann",
    "necrons": "necrons",
    "orks": "orks",
    "tau-empire": "tau-empire",
    "tyranids": "tyranids",
    "aeldari": "aeldari",
    "chaos-daemons": "chaos-daemons",
    "astra-militarum": "astra-militarum",
    "imperial-knights": "imperial-knights",
}

bsdata_40k = defaultdict(dict)
for bs_slug, units in bs_40k_raw.items():
    canonical = BS_FAC_MAP_40K.get(bs_slug, bs_slug)
    for u in units:
        bsdata_40k[canonical][slugify(u)] = u

print(f"\n40K Sources:")
print(f"  Wahapedia 40k: {sum(len(v) for v in waha_40k.values())} units, {len(waha_40k)} factions")
print(f"  BSData 40k:    {sum(len(v) for v in bsdata_40k.values())} units, {len(bsdata_40k)} factions")

# Double-source reconciliation
all_40k_factions = sorted(set(list(waha_40k.keys()) + list(bsdata_40k.keys())))

canonical_40k = {}
for fac_slug in all_40k_factions:
    waha_u = waha_40k.get(fac_slug, {})
    bs_u = bsdata_40k.get(fac_slug, {})
    superset = set(list(waha_u.keys()) + list(bs_u.keys()))

    confirmed = []
    wonly = []
    bonly = []

    for norm in superset:
        srcs = []
        nm = None
        if norm in waha_u:
            srcs.append("wahapedia")
            nm = waha_u[norm]
        if norm in bs_u:
            srcs.append("bsdata")
            if not nm:
                nm = bs_u[norm]

        entry = {"name": nm, "slug": norm, "sources": srcs}
        # For 40k: confirmed if >=2, OR if bsdata-only when wahapedia has no coverage for this faction
        if len(srcs) >= 2:
            confirmed.append(entry)
        elif srcs == ["wahapedia"]:
            wonly.append(entry)
        elif srcs == ["bsdata"]:
            if not waha_u:  # no waha coverage - accept bsdata-only
                entry["confidence"] = "lower_bsdata_only"
                confirmed.append(entry)
            else:
                bonly.append(entry)

    canonical_40k[fac_slug] = {
        "name": fac_slug.replace("-", " ").title(),
        "slug": fac_slug,
        "units": confirmed,
        "waha_only": wonly,
        "bs_only": bonly,
        "source_coverage": {
            "wahapedia": bool(waha_u),
            "bsdata": bool(bs_u),
        }
    }

confirmed_count_40k = sum(len(v["units"]) for v in canonical_40k.values())
print(f"\n40K Results:")
print(f"  Confirmed: {confirmed_count_40k}")
for fac_slug in sorted(canonical_40k.keys()):
    d = canonical_40k[fac_slug]
    print(f"  {fac_slug}: {len(d['units'])} conf | {len(d['waha_only'])} waha-only | {len(d['bs_only'])} bs-only")

# Save canonical 40k
out_40k = {}
for fac_slug, data in canonical_40k.items():
    out_40k[fac_slug] = {
        "name": data["name"],
        "slug": data["slug"],
        "units": [{"name": u["name"], "slug": u["slug"], "sources": u["sources"]} for u in data["units"]],
        "source_coverage": data["source_coverage"],
    }
with open(f"{CACHE}/canonical_40k_verified.json", "w", encoding="utf-8") as f:
    json.dump(out_40k, f, indent=2, ensure_ascii=False)
print("\nSaved canonical_40k_verified.json")

# ============================================================
# DB RECONCILIATION
# ============================================================
with open(f"{CACHE}/db_roster.json") as f:
    db_data = json.load(f)

db_aos_facs = db_data["aos4"]["factions"]
db_40k_facs = db_data["w40k10"]["factions"]

db_aos_units = {}
for fac_slug, fac_data in db_aos_facs.items():
    db_aos_units[fac_slug] = {slugify(u["name"]): u["name"] for u in fac_data.get("units", [])}

db_40k_units = {}
for fac_slug, fac_data in db_40k_facs.items():
    db_40k_units[fac_slug] = {slugify(u["name"]): u["name"] for u in fac_data.get("units", [])}

print(f"\nDB AoS: {sum(len(v) for v in db_aos_units.values())} units, {len(db_aos_units)} factions")
print(f"DB 40k: {sum(len(v) for v in db_40k_units.values())} units, {len(db_40k_units)} factions")

# AoS gaps
print("\n--- AoS DB vs Canonical ---")
aos_missing = []  # in canonical, not in DB
aos_extras = []   # in DB, not in canonical

for fac_slug in sorted(canonical_aos.keys()):
    canonical_units = {u["slug"]: u for u in canonical_aos[fac_slug]["units"]}
    db_units = db_aos_units.get(fac_slug, {})

    missing = [(slug, canonical_units[slug]) for slug in canonical_units if slug not in db_units]
    extras = [(slug, name) for slug, name in db_units.items() if slug not in canonical_units]

    if missing:
        aos_missing.extend([(fac_slug, slug, d["name"], d["sources"]) for slug, d in missing])
    if extras:
        aos_extras.extend([(fac_slug, slug, name) for slug, name in extras])

print(f"AoS missing from DB (in canonical): {len(aos_missing)}")
print(f"AoS extras in DB (not in canonical): {len(aos_extras)}")

# 40k gaps
print("\n--- 40K DB vs Canonical ---")
k40_missing = []
k40_extras = []

for fac_slug in sorted(canonical_40k.keys()):
    canonical_units = {u["slug"]: u for u in canonical_40k[fac_slug]["units"]}
    db_units = db_40k_units.get(fac_slug, {})

    missing = [(slug, canonical_units[slug]) for slug in canonical_units if slug not in db_units]
    extras = [(slug, name) for slug, name in db_units.items() if slug not in canonical_units]

    if missing:
        k40_missing.extend([(fac_slug, slug, d["name"], d["sources"]) for slug, d in missing])
    if extras:
        k40_extras.extend([(fac_slug, slug, name) for slug, name in extras])

print(f"40K missing from DB (in canonical): {len(k40_missing)}")
print(f"40K extras in DB (not in canonical): {len(k40_extras)}")

# Top 5 high-confidence gaps (all 3 sources for AoS, 2 for 40k)
print("\n=== TOP 5 HIGH-CONFIDENCE AoS GAPS (all 3 sources) ===")
all3 = [(fac, slug, nm, srcs) for fac, slug, nm, srcs in aos_missing if len(srcs) == 3]
for item in all3[:5]:
    print(f"  [{item[0]}] {item[2]} ({item[3]})")

print("\n=== TOP 5 40K GAPS (double-confirmed) ===")
both_srcs = [(fac, slug, nm, srcs) for fac, slug, nm, srcs in k40_missing if len(srcs) >= 2]
for item in both_srcs[:5]:
    print(f"  [{item[0]}] {item[2]} ({item[3]})")

# Save full reconciliation data
reconcile_data = {
    "aos": {
        "confirmed_total": confirmed_count_aos,
        "waha_input": sum(len(v) for v in waha_aos.values()),
        "waha_only_count": len(waha_only),
        "bs_only_count": len(bs_only),
        "lex_only_count": len(lex_only),
        "db_total": sum(len(v) for v in db_aos_units.values()),
        "missing_from_db": len(aos_missing),
        "extras_in_db": len(aos_extras),
        "missing_list": [(f, n, s) for f, sl, n, s in aos_missing],
        "extras_list": [(f, n) for f, sl, n in aos_extras],
        "waha_only_list": waha_only,
    },
    "40k": {
        "confirmed_total": confirmed_count_40k,
        "db_total": sum(len(v) for v in db_40k_units.values()),
        "missing_from_db": len(k40_missing),
        "extras_in_db": len(k40_extras),
        "missing_list": [(f, n, s) for f, sl, n, s in k40_missing],
        "extras_list": [(f, n) for f, sl, n in k40_extras],
    }
}
with open(f"{CACHE}/reconcile_data.json", "w", encoding="utf-8") as f:
    json.dump(reconcile_data, f, indent=2, ensure_ascii=False)
print("\nSaved reconcile_data.json")
