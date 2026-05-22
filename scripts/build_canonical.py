#!/usr/bin/env python3
"""
Build canonical unit lists from cached Wahapedia HTML files.
Produces wahapedia_aos.json, wahapedia_40k.json, and canonical_reconciliation.md
"""
import re, os, json, sys
from collections import defaultdict

CACHE = "c:/Users/eep0x10/dev/waaahgame/scripts/_cache/wahapedia"
OUT = "c:/Users/eep0x10/dev/waaahgame/scripts/cache"
os.makedirs(OUT, exist_ok=True)

# ── Helpers ──────────────────────────────────────────────────────────────────

def slugify(name):
    s = name.lower().strip()
    s = re.sub(r"[''`]", "", s)
    s = re.sub(r"[^a-z0-9]+", "-", s)
    s = s.strip("-")
    return s

def extract_aos_units_from_index(faction_slug, html_path):
    """Extract unit list from a cached AoS faction index HTML."""
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    # Extract all unique unit links for THIS faction only
    pattern = re.compile(
        r'href="(/aos4/factions/' + re.escape(faction_slug) + r'/(?!warscrolls)([^"#?]+))"[^>]*>([^<]+)</a>'
    )
    seen = {}
    for m in pattern.finditer(content):
        url_path = m.group(1)
        unit_slug = m.group(2)
        unit_name = m.group(3).strip()
        # Skip anchor/fragment links and step-instructions
        if unit_slug.startswith("#") or unit_slug.startswith("Step-") or re.match(r'^\d+\.', unit_name):
            continue
        # Skip links that look like non-unit content
        if any(x in unit_slug.lower() for x in ["warscroll", "detachment", "stratagem", "rules", "ability"]):
            continue
        # Decode HTML entities
        unit_name = unit_name.replace("&amp;", "&").replace("&#39;", "'").replace("&quot;", '"')
        if unit_slug not in seen:
            seen[unit_slug] = {
                "name": unit_name,
                "slug": unit_slug,
                "source_url": f"https://wahapedia.ru{url_path}",
            }

    # Now extract role mapping: BatRole -> units below it
    # We parse sequentially by position
    roles_pos = [(m.start(), m.group(1)) for m in re.finditer(r'class="BatRole"[^>]*>([^<]+)<', content)]
    unit_pos = [(m.start(), m.group(2)) for m in
                re.compile(r'href="/aos4/factions/' + re.escape(faction_slug) + r'/(?!warscrolls)([^"]+)"[^>]*>([^<]+)</a>').finditer(content)]

    # Map each unit to closest preceding role
    role_map = {}
    for upos, uslug in unit_pos:
        # find last role before this position
        applicable = [r for (rp, r) in roles_pos if rp < upos]
        if applicable:
            role_map[uslug] = applicable[-1]

    for slug_key, data in seen.items():
        data["role"] = role_map.get(slug_key, "Unknown")

    return list(seen.values())


def extract_40k_units_from_index(faction_slug, html_path):
    """Extract unit list from a cached 40K faction index HTML."""
    with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()

    pattern = re.compile(
        r'href="(/wh40k10ed/factions/' + re.escape(faction_slug) + r'/(?!datasheets)([^"]+))"[^>]*>([^<]+)</a>'
    )
    seen = {}
    for m in pattern.finditer(content):
        url_path = m.group(1)
        unit_slug = m.group(2)
        unit_name = m.group(3).strip()
        unit_name = unit_name.replace("&amp;", "&").replace("&#39;", "'")
        if unit_slug not in seen:
            seen[unit_slug] = {
                "name": unit_name,
                "slug": unit_slug,
                "source_url": f"https://wahapedia.ru{url_path}",
                "role": "Unknown",
            }
    return list(seen.values())


# ── AoS ──────────────────────────────────────────────────────────────────────

AOS_INDEX_DIR = os.path.join(CACHE, "_indexes")
aos_data = {}
aos_factions_scraped = []
aos_factions_failed = []

for fname in sorted(os.listdir(AOS_INDEX_DIR)):
    if not fname.endswith(".html"):
        continue
    faction_slug = fname.replace(".html", "")
    html_path = os.path.join(AOS_INDEX_DIR, fname)
    try:
        units = extract_aos_units_from_index(faction_slug, html_path)
        if units:
            aos_data[faction_slug] = {
                "name": faction_slug.replace("-", " ").title(),
                "slug": faction_slug,
                "units": units,
                "source": "wahapedia_cached_html",
            }
            aos_factions_scraped.append(faction_slug)
            print(f"AoS {faction_slug}: {len(units)} units")
        else:
            aos_factions_failed.append(faction_slug)
            print(f"AoS {faction_slug}: NO UNITS FOUND")
    except Exception as e:
        aos_factions_failed.append(faction_slug)
        print(f"AoS {faction_slug}: ERROR {e}")

with open(os.path.join(OUT, "wahapedia_aos.json"), "w", encoding="utf-8") as f:
    json.dump(aos_data, f, indent=2, ensure_ascii=False)
print(f"\nSaved wahapedia_aos.json: {len(aos_data)} factions")


# ── 40K ──────────────────────────────────────────────────────────────────────

K40_INDEX_DIR = os.path.join(CACHE, "_40k_indexes")
k40_data = {}
k40_factions_scraped = []
k40_factions_failed = []

for fname in sorted(os.listdir(K40_INDEX_DIR)):
    if not fname.endswith(".html"):
        continue
    faction_slug = fname.replace(".html", "")
    if faction_slug in ("captain_test",):  # skip test files
        continue
    html_path = os.path.join(K40_INDEX_DIR, fname)
    try:
        units = extract_40k_units_from_index(faction_slug, html_path)
        # Fallback: try broader pattern if nothing found
        if not units:
            with open(html_path, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read()
            # Generic: any link under /wh40k10ed/
            gen = re.compile(r'href="/wh40k10ed/factions/([^/]+)/([^"]+)"[^>]*>([^<]+)</a>')
            seen2 = {}
            for m in gen.finditer(content):
                fs = m.group(1)
                us = m.group(2)
                un = m.group(3).strip()
                if "datasheets" in us or "detachments" in us or "stratagems" in us:
                    continue
                un = un.replace("&amp;", "&").replace("&#39;", "'")
                if us not in seen2:
                    seen2[us] = {"name": un, "slug": us, "source_url": f"https://wahapedia.ru/wh40k10ed/factions/{fs}/{us}", "role": "Unknown"}
            units = list(seen2.values())
        if units:
            k40_data[faction_slug] = {
                "name": faction_slug.replace("-", " ").title(),
                "slug": faction_slug,
                "units": units,
                "source": "wahapedia_cached_html",
            }
            k40_factions_scraped.append(faction_slug)
            print(f"40K {faction_slug}: {len(units)} units")
        else:
            k40_factions_failed.append(faction_slug)
            print(f"40K {faction_slug}: NO UNITS FOUND")
    except Exception as e:
        k40_factions_failed.append(faction_slug)
        print(f"40K {faction_slug}: ERROR {e}")

with open(os.path.join(OUT, "wahapedia_40k.json"), "w", encoding="utf-8") as f:
    json.dump(k40_data, f, indent=2, ensure_ascii=False)
print(f"\nSaved wahapedia_40k.json: {len(k40_data)} factions")


# ── Load DB ───────────────────────────────────────────────────────────────────
print("\nLoading DB export...")
db_export_path = "c:/Users/eep0x10/dev/waaahgame/scripts/cache/db_units_export.json"
with open(db_export_path, "r", encoding="utf-8") as f:
    db_units = json.load(f)

# db_units format — check structure
sample = db_units[0] if db_units else {}
print("DB sample keys:", list(sample.keys()))
print("DB total records:", len(db_units))
