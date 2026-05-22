#!/usr/bin/env python3
"""
Reconcile canonical Wahapedia unit list against DB.
Produces scripts/cache/canonical_reconciliation.md
"""
import re, os, json
from collections import defaultdict

CACHE_DIR = "c:/Users/eep0x10/dev/waaahgame/scripts/cache"
WAHAPEDIA_CACHE = "c:/Users/eep0x10/dev/waaahgame/scripts/_cache/wahapedia"
OUT_MD = os.path.join(CACHE_DIR, "canonical_reconciliation.md")

# ── Load canonical data ───────────────────────────────────────────────────────

with open(os.path.join(CACHE_DIR, "wahapedia_aos.json"), encoding="utf-8") as f:
    aos_canonical = json.load(f)

with open(os.path.join(CACHE_DIR, "wahapedia_40k.json"), encoding="utf-8") as f:
    k40_canonical = json.load(f)

# ── Load DB data ──────────────────────────────────────────────────────────────

with open(os.path.join(CACHE_DIR, "db_roster.json"), encoding="utf-8") as f:
    db_data = json.load(f)

db_aos = db_data.get("aos4", {}).get("factions", {})
db_40k = db_data.get("w40k10", {}).get("factions", {})


# ── Fuzzy match helpers ───────────────────────────────────────────────────────

def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[''`',\.]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s


def expand_keys(name, slug=None):
    """Return set of match keys for a unit name/slug (handles plural/singular, spaces/hyphens)."""
    keys = set()
    fuzz = slugify(name)
    keys.add(fuzz)
    # strip trailing s (Aetherwings -> Aetherwing)
    if fuzz.endswith("s"):
        keys.add(fuzz[:-1])
    # add trailing s
    keys.add(fuzz + "s")
    if slug:
        sl = slug.lower()
        keys.add(sl)
        if sl.endswith("s"):
            keys.add(sl[:-1])
        keys.add(sl + "s")
    return keys


def reconcile_faction(canon_units, db_units, faction_slug):
    """
    Returns dict with:
      matched: count
      missing_from_db: list of canonical units not in DB
      extra_in_db: list of DB units not in canonical
    """
    # Build expanded key sets
    canon_key_map = {}  # key -> canonical unit name (for dedup)
    for u in canon_units:
        for k in expand_keys(u["name"], u["slug"]):
            canon_key_map[k] = u["name"]

    db_key_map = {}
    for u in db_units:
        for k in expand_keys(u["name"], u["slug"]):
            db_key_map[k] = u["name"]

    matched = 0
    missing_from_db = []
    extra_in_db = []

    # Deduplicate canonical units by slug
    seen_canon = set()
    for u in canon_units:
        key = u["slug"]
        if key in seen_canon:
            continue
        seen_canon.add(key)
        # Check if any of its keys appear in db_key_map
        hit = any(k in db_key_map for k in expand_keys(u["name"], u["slug"]))
        if hit:
            matched += 1
        else:
            missing_from_db.append(u["name"])

    # Deduplicate DB units by slug
    seen_db = set()
    for u in db_units:
        key = u["slug"]
        if key in seen_db:
            continue
        seen_db.add(key)
        hit = any(k in canon_key_map for k in expand_keys(u["name"], u["slug"]))
        if not hit:
            extra_in_db.append(u["name"])

    return {
        "matched": matched,
        "missing_from_db": sorted(missing_from_db),
        "extra_in_db": sorted(extra_in_db),
        "canon_total": len(seen_canon),
        "db_total": len(seen_db),
    }


# ── AoS reconciliation ────────────────────────────────────────────────────────

print("=== AoS Reconciliation ===")

# DB factions present
db_aos_factions = set(db_aos.keys())

# Canonical factions from Wahapedia cache
canon_aos_factions = set(aos_canonical.keys())

# DB has extra factions not in canonical cache
# Map known DB faction splits to canonical
# e.g., skaventide/skaven, orruk-warclans/(ironjawz+kruleboyz), tzeentch-arcanites/disciples-of-tzeentch etc.
FACTION_MAP_AOS = {
    # DB slug -> canonical slug (or None if split/unmappable)
    "skaventide": "skaven",                          # DB uses split; canonical merged
    "tzeentch-arcanites": "disciples-of-tzeentch",  # merged
    "slaanesh-sybarites": "hedonites-of-slaanesh",  # merged/part of
    "orruk-warclans": "ironjawz",                   # orruk-warclans spans ironjawz+kruleboyz
    "monsters-of-chaos": "beasts-of-chaos",         # subfaction
    "beasts-of-the-grave": "soulblight-gravelords", # subfaction
    "deathlords": "soulblight-gravelords",           # subfaction
    # lumineth-realm-lords: no canonical cache — listed under DB-only
}

# Factions in DB but not in canonical (no mapping)
db_only_factions = db_aos_factions - canon_aos_factions - set(FACTION_MAP_AOS.keys())
canon_only_factions = canon_aos_factions - db_aos_factions

print(f"Canonical factions (Wahapedia cache): {len(canon_aos_factions)}")
print(f"DB factions: {len(db_aos_factions)}")

# Per-faction reconciliation
aos_faction_results = {}

for canon_slug, canon_data in sorted(aos_canonical.items()):
    # Find corresponding DB factions (direct match or reverse map)
    db_units = []
    # direct match
    if canon_slug in db_aos:
        db_units.extend(db_aos[canon_slug]["units"])
    # check if any DB faction maps to this canonical
    for db_slug, mapped in FACTION_MAP_AOS.items():
        if mapped == canon_slug and db_slug in db_aos:
            db_units.extend(db_aos[db_slug]["units"])
    # Special: orruk-warclans also maps to kruleboyz
    if canon_slug == "kruleboyz" and "orruk-warclans" in db_aos:
        db_units.extend(db_aos["orruk-warclans"]["units"])

    result = reconcile_faction(canon_data["units"], db_units, canon_slug)
    aos_faction_results[canon_slug] = result
    gap = result["canon_total"] - result["matched"]
    print(f"  {canon_slug}: canon={result['canon_total']}, db={result['db_total']}, matched={result['matched']}, missing={len(result['missing_from_db'])}, extra={len(result['extra_in_db'])}")

# ── 40K reconciliation ────────────────────────────────────────────────────────

print("\n=== 40K Reconciliation ===")

# DB 40K has "space-marines" but canonical has "space-marines" too
# DB has "space-marines" faction name "Adeptus Astartes"
FACTION_MAP_40K = {
    "space-marines": "space-marines",
}

k40_faction_results = {}

for canon_slug, canon_data in sorted(k40_canonical.items()):
    db_units = []
    if canon_slug in db_40k:
        db_units.extend(db_40k[canon_slug]["units"])

    result = reconcile_faction(canon_data["units"], db_units, canon_slug)
    k40_faction_results[canon_slug] = result
    print(f"  {canon_slug}: canon={result['canon_total']}, db={result['db_total']}, matched={result['matched']}, missing={len(result['missing_from_db'])}, extra={len(result['extra_in_db'])}")


# ── Summary stats ─────────────────────────────────────────────────────────────

aos_canon_total = sum(r["canon_total"] for r in aos_faction_results.values())
aos_db_total = sum(len(db_aos[s]["units"]) for s in db_aos)
aos_matched = sum(r["matched"] for r in aos_faction_results.values())
aos_missing = sum(len(r["missing_from_db"]) for r in aos_faction_results.values())
aos_extra = sum(len(r["extra_in_db"]) for r in aos_faction_results.values())

k40_canon_total = sum(r["canon_total"] for r in k40_faction_results.values())
k40_db_total = sum(len(db_40k[s]["units"]) for s in db_40k)
k40_matched = sum(r["matched"] for r in k40_faction_results.values())
k40_missing = sum(len(r["missing_from_db"]) for r in k40_faction_results.values())
k40_extra = sum(len(r["extra_in_db"]) for r in k40_faction_results.values())

print(f"\nAoS totals: canonical={aos_canon_total}, db={aos_db_total}, matched={aos_matched}, missing={aos_missing}, extra_in_db={aos_extra}")
print(f"40K totals: canonical={k40_canon_total}, db={k40_db_total}, matched={k40_matched}, missing={k40_missing}, extra_in_db={k40_extra}")


# ── Build Markdown report ─────────────────────────────────────────────────────

# Top 5 biggest gaps per system
top5_aos = sorted(aos_faction_results.items(), key=lambda x: len(x[1]["missing_from_db"]), reverse=True)[:5]
top5_40k = sorted(k40_faction_results.items(), key=lambda x: len(x[1]["missing_from_db"]), reverse=True)[:5]

lines = []

lines.append("# Canonical Roster Reconciliation")
lines.append("")
lines.append("**Source:** Wahapedia (`wahapedia.ru`) cached HTML files (fetched previously, stored in `scripts/_cache/wahapedia/`)")
lines.append("**Date of analysis:** 2026-05-21")
lines.append("")
lines.append("> **Note on 53 phantom pairs:** Previously identified 53 phantom image pairs (units where image matched wrong unit) are a known issue from the prior audit (`audit_lex_vs_db_v2.md`). Those are image-alignment problems, not unit-existence problems, and are tracked separately.")
lines.append("")

# ── AoS section ──

lines.append("---")
lines.append("")
lines.append("## Age of Sigmar (4th Edition, Skaventide 2024)")
lines.append("")
lines.append(f"| | Count |")
lines.append(f"|---|---|")
lines.append(f"| Canonical factions (Wahapedia cache) | {len(canon_aos_factions)} |")
lines.append(f"| DB factions | {len(db_aos_factions)} |")
lines.append(f"| Canonical units (total) | {aos_canon_total} |")
lines.append(f"| DB units (total) | {aos_db_total} |")
lines.append(f"| Matched (DB has the unit) | {aos_matched} |")
lines.append(f"| **Missing from DB** (in canonical, not in DB) | **{aos_missing}** |")
lines.append(f"| Extra in DB (not in canonical) | {aos_extra} |")
lines.append("")

# Faction mapping notes
lines.append("### DB Faction → Canonical Faction Mapping Notes")
lines.append("")
lines.append("The DB has some factions that are sub-factions or renamed in the canonical list:")
lines.append("")
for db_s, canon_s in FACTION_MAP_AOS.items():
    db_cnt = db_aos[db_s]["unit_count"] if db_s in db_aos else 0
    lines.append(f"- `{db_s}` (DB: {db_cnt} units) → mapped to `{canon_s or 'UNMAPPED'}`")
lines.append("")

# DB-only factions
if db_only_factions:
    lines.append("### DB Factions with NO canonical equivalent found")
    lines.append("")
    for s in sorted(db_only_factions):
        lines.append(f"- `{s}` ({db_aos[s]['unit_count']} units in DB)")
    lines.append("")

# Canon-only factions
if canon_only_factions:
    lines.append("### Canonical Factions NOT in DB")
    lines.append("")
    for s in sorted(canon_only_factions):
        cnt = len(aos_canonical[s]["units"])
        lines.append(f"- `{s}` ({cnt} canonical units — entire faction missing from DB)")
    lines.append("")

lines.append("### Top 5 AoS Factions by Gap Size (Missing from DB)")
lines.append("")
lines.append("| Faction | Canonical | DB | Matched | Missing | Extra in DB |")
lines.append("|---|---|---|---|---|---|")
for slug, r in top5_aos:
    lines.append(f"| {slug} | {r['canon_total']} | {r['db_total']} | {r['matched']} | {len(r['missing_from_db'])} | {len(r['extra_in_db'])} |")
lines.append("")

lines.append("### Per-Faction Detail (AoS)")
lines.append("")
for slug, r in sorted(aos_faction_results.items()):
    missing_cnt = len(r["missing_from_db"])
    extra_cnt = len(r["extra_in_db"])
    lines.append(f"#### {slug}")
    lines.append(f"- Canon: {r['canon_total']} | DB: {r['db_total']} | Matched: {r['matched']} | Missing: {missing_cnt} | Extra: {extra_cnt}")
    if r["missing_from_db"]:
        lines.append(f"- **Missing from DB ({missing_cnt}):**")
        for u in r["missing_from_db"]:
            lines.append(f"  - {u}")
    if r["extra_in_db"]:
        lines.append(f"- **Extra in DB ({extra_cnt})** (not in Wahapedia canonical):")
        for u in r["extra_in_db"]:
            lines.append(f"  - {u}")
    lines.append("")


# ── 40K section ──

lines.append("---")
lines.append("")
lines.append("## Warhammer 40,000 (10th Edition)")
lines.append("")
lines.append(f"| | Count |")
lines.append(f"|---|---|")
lines.append(f"| Canonical factions (Wahapedia cache) | {len(k40_canonical)} |")
lines.append(f"| DB factions | {len(db_40k)} |")
lines.append(f"| Canonical units (total) | {k40_canon_total} |")
lines.append(f"| DB units (total) | {k40_db_total} |")
lines.append(f"| Matched | {k40_matched} |")
lines.append(f"| **Missing from DB** | **{k40_missing}** |")
lines.append(f"| Extra in DB | {k40_extra} |")
lines.append("")

lines.append("> **Coverage gap:** Wahapedia cache only has 5 of ~25+ 40K factions. The missing factions need fresh scraping.")
lines.append("")

lines.append("### Top 5 40K Factions by Gap Size")
lines.append("")
lines.append("| Faction | Canonical | DB | Matched | Missing | Extra in DB |")
lines.append("|---|---|---|---|---|---|")
for slug, r in top5_40k:
    lines.append(f"| {slug} | {r['canon_total']} | {r['db_total']} | {r['matched']} | {len(r['missing_from_db'])} | {len(r['extra_in_db'])} |")
lines.append("")

lines.append("### Per-Faction Detail (40K)")
lines.append("")
for slug, r in sorted(k40_faction_results.items()):
    missing_cnt = len(r["missing_from_db"])
    extra_cnt = len(r["extra_in_db"])
    lines.append(f"#### {slug}")
    lines.append(f"- Canon: {r['canon_total']} | DB: {r['db_total']} | Matched: {r['matched']} | Missing: {missing_cnt} | Extra: {extra_cnt}")
    if r["missing_from_db"]:
        lines.append(f"- **Missing from DB ({missing_cnt}):**")
        for u in r["missing_from_db"][:30]:
            lines.append(f"  - {u}")
        if missing_cnt > 30:
            lines.append(f"  - ... and {missing_cnt - 30} more")
    if r["extra_in_db"]:
        lines.append(f"- **Extra in DB ({extra_cnt}):**")
        for u in r["extra_in_db"]:
            lines.append(f"  - {u}")
    lines.append("")


# ── Coverage notes ──

lines.append("---")
lines.append("")
lines.append("## Coverage & Confidence")
lines.append("")
lines.append("### AoS Coverage")
lines.append(f"- **24 of 25 known factions** from cached Wahapedia HTML parsed successfully")
lines.append(f"- Cache date unknown but HTML filenames match AoS 4th edition structure (post-Skaventide 2024)")
lines.append(f"- Confidence: HIGH for the 24 cached factions")
lines.append(f"- **Missing from cache: `lumineth-realm-lords`** — no HTML cached, so that faction has no canonical list (DB has 10 units for it)")
lines.append(f"  - Note: Bonesplitterz, Ironjawz, Kruleboyz are listed separately by Wahapedia but the DB uses `orruk-warclans` as the merged faction")
lines.append("")
lines.append("### 40K Coverage")
lines.append(f"- **5 of ~25-30 factions** in Wahapedia cache")
lines.append(f"- Missing factions: Adeptus Mechanicus, Adepta Sororitas, Death Guard, Drukhari, Grey Knights, Harlequins, Imperial Guard, Leagues of Votann, Orks, T'au Empire, World Eaters, Thousand Sons, and others")
lines.append(f"- Wahapedia 403'd when re-scraped — cache is the only source available without a scraping session")
lines.append(f"- Confidence for 40K: LOW (5 factions only, non-representative)")
lines.append("")
lines.append("### Factions Where Scraping Failed")
lines.append("- **Wahapedia live site:** HTTP 403 for all requests (bot protection active)")
lines.append("- **All AoS factions:** covered by local cache")
lines.append("- **40K — uncached factions (need scraping):** Adeptus Mechanicus, Adepta Sororitas, Custodes, Death Guard, Drukhari, Grey Knights, Imperial Guard (Astra Militarum), Leagues of Votann, Orks, T'au Empire, Thousand Sons, World Eaters, Chaos Daemons, Genestealer Cults, Harlequins/Corsairs, Imperial Knights, Chaos Knights, Dark Angels, Space Wolves, Blood Angels, Black Templars, Salamanders, Deathwatch, and potentially more")
lines.append("")

with open(OUT_MD, "w", encoding="utf-8") as f:
    f.write("\n".join(lines))

print(f"\nReport saved to: {OUT_MD}")
