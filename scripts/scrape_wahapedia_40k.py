#!/usr/bin/env python3
"""
Wahapedia scraper for waaahgame — Warhammer 40k 10th edition units.

Strategy:
  1. Fetch faction index page (one per faction, cached).
  2. Build name → unit_page_URL map from index.
  3. For each DB unit, look up its URL via slug matching.
  4. Fetch each unit's individual page (cached by URL slug).
  5. Parse stats/weapons/abilities/keywords from the datasheet.
  6. Store into Unit.{stats,weapons,abilities,keywords}_json.

URL patterns:
  Index:  https://wahapedia.ru/wh40k10ed/factions/<faction-slug>/
  Unit:   https://wahapedia.ru/wh40k10ed/factions/<faction-slug>/<Unit-Name-Slug>
  (Unit slugs come from the index — do NOT guess them.)

HTML structure (40k 10th ed unit page):
  div.dsOuterFrame.datasheet    — root unit container (one per page)
    div.dsH2Header              — unit name + base size, e.g. "Captain(⌀40mm)"
    div.dsCharName              — stat label (M / T / Sv / W / Ld / OC)
    div.dsCharValue             — stat value
    table.wTable                — weapon table (ranged or melee)
      div.wTable_WEAPON         — weapon type header (RANGED / MELEE WEAPONS)
      div.ct.dsHeader           — column headers (RANGE / A / BS or WS / S / AP / D)
      tr (no class, 8 tds)      — header row (first occurrence contains type label)
      tr.wTable2_long           — weapon name + keyword row (2 tds: name, keywords)
      tr (no class, 8 tds)      — stat values row (same layout as header)
    div.dsAbility               — unit ability block (text = "Name: description")
      (abilities inside dsRightСol.dsColorFrSM are unit-specific)
    div.dsLeftСolKW             — unit keywords  (e.g. INFANTRY, CHARACTER, ...)
    div.dsRightСolKW            — faction keywords (e.g. ADEPTUS ASTARTES)

Stats output (lowercase keys required by template):
  {"move": "6\"", "toughness": "4", "save": "3+", "wounds": "5",
   "leadership": "6+", "oc": "1"}

Usage:
    python scripts/scrape_wahapedia_40k.py --dry-run --faction space-marines
    python scripts/scrape_wahapedia_40k.py --faction tyranids
    python scripts/scrape_wahapedia_40k.py                          # all 5 factions
    python scripts/scrape_wahapedia_40k.py --force                  # re-scrape all
    python scripts/scrape_wahapedia_40k.py --no-cache               # bypass HTML cache
    python scripts/scrape_wahapedia_40k.py --slug hive-tyrant --dry-run
"""

import sys
import os
import time
import argparse
import logging
import re
import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import requests
from bs4 import BeautifulSoup

from app import create_app
from app.extensions import db
from app.models.game import Unit, Faction
from sqlalchemy.orm.attributes import flag_modified

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

WAHAPEDIA_BASE = "https://wahapedia.ru"
CACHE_DIR = REPO_ROOT / "scripts" / "_cache" / "wahapedia" / "_40k_indexes"
UNIT_CACHE_DIR = REPO_ROOT / "scripts" / "_cache" / "wahapedia" / "_40k_units"
REQUEST_DELAY = 1.5
REQUEST_TIMEOUT = 30
USER_AGENT = "waaahgame-scraper/1.0"
COMMIT_BATCH = 20

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Faction config and manual overrides
# ---------------------------------------------------------------------------

FACTIONS = [
    "space-marines",
    "aeldari",
    "chaos-space-marines",
    "necrons",
    "tyranids",
]

# Manual slug overrides: DB slug → Wahapedia display name (lowercase hyphenated)
# Used when the DB slug differs from the Wahapedia page name.
SLUG_OVERRIDES = {
    # space-marines — DB slug doesn't match Wahapedia name exactly
    "captain-in-power-armour":              "captain",
    "assault-intercessors":                 "assault-intercessor-squad",
    "hellblasters":                         "hellblaster-squad",
    "eradicators":                          "eradicator-squad",
    # tyranids — Wahapedia uses full variant name
    "tyranid-warriors-with-melee":          "tyranid-warriors-with-melee-bio-weapons",
    "carnifex":                             "carnifexes",
    # necrons — Wahapedia omits "Necron" prefix for some units
    "necron-overlord":                      "overlord",
    "necron-lord":                          "lord",
    "doomstalker":                          "canoptek-doomstalker",
    "cryptek":                              "technomancer",
    # aeldari — "War Walkers" is a direct match (plural stays)
    # chaos-space-marines — variant names
    "sorcerer-in-terminator-armour":        "sorcerer",
    "chaos-terminators":                    "chaos-terminator-squad",
    "chaos-cultists":                       "cultist-mob",
}

# ---------------------------------------------------------------------------
# HTTP / cache helpers
# ---------------------------------------------------------------------------

def _slug_from_url(url: str) -> str:
    """Extract the last path component from a Wahapedia URL."""
    return url.rstrip("/").split("/")[-1]


def _unit_cache_path(faction: str, unit_url_slug: str) -> Path:
    return UNIT_CACHE_DIR / faction / f"{unit_url_slug}.html"


def _index_cache_path(faction: str) -> Path:
    return CACHE_DIR / f"{faction}.html"


def fetch_html(url: str, cache_path: Path, use_cache: bool = True) -> str | None:
    if use_cache and cache_path.exists():
        log.debug("Cache hit: %s", cache_path)
        return cache_path.read_text(encoding="utf-8", errors="replace")

    log.info("Fetching: %s", url)
    try:
        resp = requests.get(
            url,
            headers={"User-Agent": USER_AGENT},
            timeout=REQUEST_TIMEOUT,
        )
        resp.raise_for_status()
    except requests.RequestException as exc:
        log.error("HTTP error for %s: %s", url, exc)
        return None

    html = resp.text
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_text(html, encoding="utf-8")
    return html


# ---------------------------------------------------------------------------
# Index parsing: build name→URL map
# ---------------------------------------------------------------------------

def build_url_map(faction: str, html: str) -> dict[str, str]:
    """
    Parse faction index HTML and return a dict mapping normalised slug → full URL.
    Normalised slug = display name lowercased, spaces→hyphens.
    """
    soup = BeautifulSoup(html, "html.parser")
    result: dict[str, str] = {}
    for a in soup.find_all("a", class_="cnClr"):
        href = a.get("href", "")
        display = a.get_text(strip=True)
        if not href or not display:
            continue
        normalised = display.lower().replace(" ", "-")
        full_url = WAHAPEDIA_BASE + href
        # Keep first occurrence only (deduplication)
        if normalised not in result:
            result[normalised] = full_url
    log.info("[%s] URL map built: %d entries", faction, len(result))
    return result


def resolve_unit_url(db_slug: str, url_map: dict[str, str]) -> str | None:
    """
    Try to resolve a DB slug to a Wahapedia unit URL.
    Priority:
      1. Manual override in SLUG_OVERRIDES
      2. Direct key match in url_map
      3. Partial: url_map key starts with db_slug  (handles 'eradicators' → 'eradicator-squad')
      4. Partial: db_slug starts with url_map key
    """
    # 1. Manual override
    override_key = SLUG_OVERRIDES.get(db_slug, db_slug)
    if override_key in url_map:
        return url_map[override_key]

    # 2. Direct match
    if db_slug in url_map:
        return url_map[db_slug]

    # 3. url_map key starts with db_slug
    for k, v in url_map.items():
        if k.startswith(db_slug) and abs(len(k) - len(db_slug)) <= 8:
            return v

    # 4. db_slug starts with url_map key (db slug is longer)
    for k, v in url_map.items():
        if db_slug.startswith(k) and abs(len(k) - len(db_slug)) <= 8:
            return v

    return None


# ---------------------------------------------------------------------------
# Unit page parsers
# ---------------------------------------------------------------------------

def parse_stats(ds) -> dict:
    """
    Parse M/T/Sv/W/Ld/OC stats from a unit datasheet element.
    Returns dict with lowercase keys required by the w40k10 template:
      move, toughness, save, wounds, leadership, oc
    """
    stat_name_map = {
        "M":  "move",
        "T":  "toughness",
        "Sv": "save",
        "W":  "wounds",
        "Ld": "leadership",
        "OC": "oc",
    }
    names = [el.get_text(strip=True) for el in ds.find_all(class_="dsCharName")]
    values = [el.get_text(strip=True) for el in ds.find_all(class_="dsCharValue")]
    stats: dict = {}
    for name, val in zip(names, values):
        key = stat_name_map.get(name, name.lower())
        if val:
            stats[key] = val
    return stats


def parse_weapons(ds) -> list[dict]:
    """
    Parse weapon tables from a unit datasheet.

    Table structure (40k 10th ed):
      Row 0 (8 tds, no class): header — td[1]=type label ("RANGED/MELEE WEAPONS"),
                                td[2..7] = stat headers (RANGE, A, BS/WS, S, AP, D)
      tr.wTable2_long (2 tds): weapon name row
          td[0] = empty icon cell
          td[1] = span containing weapon name + nested kwb* spans (keyword pills)
      Row after wTable2_long (8 tds, no class): stat values
          td[0] = empty  td[1]=ignored  td[2]=Range  td[3..7]=A,BS/WS,S,AP,D

    The weapon name lives in the first <span> of td[1] in the wTable2_long row,
    with kwb* child spans that hold keyword pills (strip them for clean name;
    extract their .tt text for Keywords).

    Returns list of dicts: Name, Type, Range, A, BS (or WS for melee), S, AP, D, Keywords.
    """
    weapons: list[dict] = []

    for tbl in ds.find_all("table", class_="wTable"):
        rows = tbl.find_all("tr")
        if not rows:
            continue

        # Header row: 8 tds
        header_tds = rows[0].find_all("td")
        if len(header_tds) < 8:
            continue

        weapon_type_raw = header_tds[1].get_text(strip=True)
        if "RANGED" in weapon_type_raw.upper():
            type_label = "Ranged"
        elif "MELEE" in weapon_type_raw.upper():
            type_label = "Melee"
        else:
            type_label = weapon_type_raw.title()

        # Stat col headers from header row tds[2..7]
        stat_headers = [td.get_text(strip=True) for td in header_tds[2:8]]

        i = 1
        while i < len(rows):
            row = rows[i]
            row_cls = row.get("class", [])

            if "wTable2_long" in row_cls:
                name_tds = row.find_all("td")
                # td[0] = empty icon, td[1] = pad2626 span with name + kwb pills
                if len(name_tds) < 2:
                    i += 1
                    continue

                td1 = name_tds[1]
                # First direct span of td[1] contains name text + nested kwb spans
                name_span = td1.find("span", recursive=False)

                if name_span:
                    name_copy = BeautifulSoup(str(name_span), "html.parser")
                    # Extract keywords from kwb* spans before stripping them
                    kw_texts = []
                    for kwb in name_copy.find_all("span", class_=lambda c: c and "kwb" in c):
                        tt = kwb.find(class_="tt")
                        if tt:
                            kw_texts.append(tt.get_text(strip=True))
                        kwb.decompose()
                    weapon_name = name_copy.get_text(strip=True)
                else:
                    weapon_name = td1.get_text(strip=True)
                    kw_texts = []

                # Next row (8 tds) = stat values
                if i + 1 < len(rows):
                    stat_row = rows[i + 1]
                    stat_cls = stat_row.get("class", [])
                    if "wTable2_long" not in stat_cls:
                        stat_tds = stat_row.find_all("td")
                        # Layout: [icon, name+kw(ignored), range, A, BS/WS, S, AP, D]
                        if len(stat_tds) >= 8:
                            range_val = stat_tds[2].get_text(strip=True)
                            stat_vals = [td.get_text(strip=True) for td in stat_tds[3:8]]

                            weapon: dict = {
                                "Name": weapon_name,
                                "Type": type_label,
                                "Range": range_val,
                            }
                            for header, val in zip(stat_headers[1:], stat_vals):
                                if header:
                                    weapon[header] = val
                            if kw_texts:
                                weapon["Keywords"] = ", ".join(kw_texts)

                            weapons.append(weapon)
                            i += 2
                            continue

            i += 1

    return weapons


def parse_abilities(ds) -> list[dict]:
    """
    Parse unit abilities from dsAbility elements inside dsRightСol.

    Each dsAbility element contains text like "AbilityName: description text..."
    We skip purely decorative / shared-rules ability blocks.
    """
    abilities: list[dict] = []
    seen: set[str] = set()

    right_col = ds.find(class_="dsRightСol")
    if not right_col:
        # Fallback: search in full ds
        right_col = ds

    for el in right_col.find_all(class_="dsAbility"):
        # Check it's a direct child of dsRightСol (not nested under s10EnhWrap etc.)
        parent_cls = el.parent.get("class") or [] if el.parent else []
        grandparent_cls = el.parent.parent.get("class") or [] if el.parent and el.parent.parent else []

        # Skip enhancement/stratagem ability blocks (they're in lists)
        if any(c in ["s10EnhWrap", "dsAbility_noLine"] for c in parent_cls):
            continue
        if any(c in ["s10EnhWrap"] for c in grandparent_cls):
            continue

        text = el.get_text(separator=" ", strip=True)
        if not text:
            continue

        # Parse "Name: description" format
        # Many abilities are "CORE: Leader" or "FACTION: Oath of Moment" (categories)
        # or full text abilities
        colon_idx = text.find(":")
        if colon_idx > 0 and colon_idx < 50:
            name = text[:colon_idx].strip()
            desc = text[colon_idx + 1:].strip()
        else:
            # No clear name:desc split — use first bold element if present
            bold = el.find("b")
            if bold:
                name = bold.get_text(strip=True)
                desc = text[len(name):].strip().lstrip(":")
            else:
                # Use truncated text as name, skip
                name = text[:60].strip()
                desc = ""

        if not name or name in seen:
            continue
        seen.add(name)

        abilities.append({"name": name, "description": desc})

    return abilities


def parse_keywords(ds) -> list[str]:
    """
    Parse unit and faction keywords from dsLeftСolKW / dsRightСolKW.
    Returns a deduplicated list of keyword strings.
    """
    keywords: list[str] = []
    seen: set[str] = set()

    for cls in ("dsLeftСolKW", "dsRightСolKW"):
        col = ds.find(class_=cls)
        if not col:
            continue
        # Keywords are separated by commas/spaces; get_text gives us the raw text
        raw = col.get_text(separator=",", strip=True)
        # Remove "KEYWORDS:" and "FACTION KEYWORDS:" headers
        raw = re.sub(r"(?:FACTION\s+)?KEYWORDS\s*:", "", raw, flags=re.I)
        # Split and clean
        for kw in re.split(r"[,|]+", raw):
            kw = kw.strip()
            if kw and kw not in seen:
                seen.add(kw)
                keywords.append(kw)

    return keywords


def parse_unit_page(html: str) -> dict | None:
    """Parse a Wahapedia 40k unit page. Returns dict or None if no datasheet found."""
    soup = BeautifulSoup(html, "html.parser")
    ds = soup.find(class_="dsOuterFrame")
    if not ds:
        # Try fallback: any element with both 'datasheet' class
        ds = soup.find(class_="datasheet")
    if not ds:
        log.warning("No dsOuterFrame/datasheet found on page")
        return None

    return {
        "stats": parse_stats(ds),
        "weapons": parse_weapons(ds),
        "abilities": parse_abilities(ds),
        "keywords": parse_keywords(ds),
    }


# ---------------------------------------------------------------------------
# Main scrape loop
# ---------------------------------------------------------------------------

def scrape_faction(
    faction_slug: str,
    use_cache: bool,
    dry_run: bool,
    force: bool,
    unit_slug_filter: str | None,
) -> dict:
    """Scrape a single faction. Returns per-faction counters."""
    counters = {
        "scraped": 0,
        "skipped_existing": 0,
        "unmatched_db_unit": 0,      # DB unit with no Wahapedia URL found
        "unmatched_wahapedia_unit": 0,  # (reserved, not used directly)
        "http_failed": 0,
        "parse_failed": 0,
    }

    # 1. Fetch / load faction index
    index_url = f"{WAHAPEDIA_BASE}/wh40k10ed/factions/{faction_slug}/"
    index_cache = _index_cache_path(faction_slug)
    html_index = fetch_html(index_url, index_cache, use_cache=use_cache)
    if html_index is None:
        log.error("[%s] Could not fetch index — skipping faction", faction_slug)
        counters["http_failed"] += 1
        return counters

    url_map = build_url_map(faction_slug, html_index)

    # 2. Load DB units for this faction
    faction_obj = Faction.query.filter_by(slug=faction_slug).first()
    if not faction_obj:
        log.error("[%s] Faction not found in DB", faction_slug)
        return counters

    db_units = Unit.query.filter_by(faction_id=faction_obj.id).all()
    if unit_slug_filter:
        db_units = [u for u in db_units if u.slug == unit_slug_filter]

    log.info("[%s] Processing %d DB units", faction_slug, len(db_units))

    last_fetch_time = 0.0
    pending_commit: list[Unit] = []

    for unit in db_units:
        # Skip if already populated and not forcing
        if not force and unit.weapons_json:
            counters["skipped_existing"] += 1
            continue

        # Resolve URL
        unit_url = resolve_unit_url(unit.slug, url_map)
        if unit_url is None:
            log.warning("[%s] No Wahapedia URL found for DB slug: %s", faction_slug, unit.slug)
            counters["unmatched_db_unit"] += 1
            continue

        # URL slug for caching
        url_slug = _slug_from_url(unit_url)
        unit_cache = _unit_cache_path(faction_slug, url_slug)

        # Politeness delay for live fetches
        is_cached = use_cache and unit_cache.exists()
        if not is_cached:
            elapsed = time.monotonic() - last_fetch_time
            if elapsed < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - elapsed)

        html = fetch_html(unit_url, unit_cache, use_cache=use_cache)
        if not is_cached:
            last_fetch_time = time.monotonic()

        if html is None:
            log.error("[%s] HTTP failed for %s (%s)", faction_slug, unit.slug, unit_url)
            counters["http_failed"] += 1
            continue

        parsed = parse_unit_page(html)
        if parsed is None:
            log.error("[%s] Parse failed for %s", faction_slug, unit.slug)
            counters["parse_failed"] += 1
            continue

        log.info("[%s] %s → stats=%s, weapons=%d, abilities=%d, keywords=%d",
                 faction_slug, unit.slug,
                 parsed["stats"],
                 len(parsed["weapons"]),
                 len(parsed["abilities"]),
                 len(parsed["keywords"]))

        if dry_run:
            print(f"\n{'='*60}")
            print(f"DRY-RUN [{faction_slug}]: {unit.slug}")
            print(f"  wahapedia_url: {unit_url}")
            print(f"  stats: {json.dumps(parsed['stats'])}")
            print(f"  weapons (first 2):")
            for w in parsed["weapons"][:2]:
                print(f"    {json.dumps(w)}")
            print(f"  abilities (first 2):")
            for ab in parsed["abilities"][:2]:
                print(f"    {json.dumps(ab)}")
            print(f"  keywords (first 5): {parsed['keywords'][:5]}")
            counters["scraped"] += 1
            continue

        # Persist — flag_modified required for SQLAlchemy to detect JSON column mutations
        unit.wahapedia_url = unit_url
        unit.stats_json = parsed["stats"]
        unit.weapons_json = parsed["weapons"]
        unit.abilities_json = parsed["abilities"]
        unit.keywords_json = parsed["keywords"]
        flag_modified(unit, "stats_json")
        flag_modified(unit, "weapons_json")
        flag_modified(unit, "abilities_json")
        flag_modified(unit, "keywords_json")

        db.session.add(unit)
        pending_commit.append(unit)
        counters["scraped"] += 1

        if len(pending_commit) >= COMMIT_BATCH:
            db.session.commit()
            log.info("[%s] Committed batch of %d", faction_slug, len(pending_commit))
            pending_commit.clear()

    if pending_commit and not dry_run:
        db.session.commit()
        log.info("[%s] Committed final batch of %d", faction_slug, len(pending_commit))
        pending_commit.clear()

    return counters


def run(
    factions: list[str] | None = None,
    unit_slug: str | None = None,
    force: bool = False,
    dry_run: bool = False,
    use_cache: bool = True,
):
    target_factions = factions or FACTIONS
    all_counters: dict[str, dict] = {}

    for faction in target_factions:
        log.info("=== Faction: %s ===", faction)
        c = scrape_faction(faction, use_cache, dry_run, force, unit_slug)
        all_counters[faction] = c

    # Summary
    print("\n" + "=" * 60)
    print("SCRAPE SUMMARY — w40k10")
    print("=" * 60)
    totals = {k: 0 for k in next(iter(all_counters.values()))}
    for faction, c in all_counters.items():
        print(f"\n  [{faction}]")
        for key, val in c.items():
            print(f"    {key:<28}: {val}")
            totals[key] += val
    print(f"\n  [TOTAL]")
    for key, val in totals.items():
        print(f"    {key:<28}: {val}")
    print("=" * 60)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape Wahapedia 40k 10th edition unit data into waaahgame DB"
    )
    parser.add_argument("--faction", help="Process a single faction slug")
    parser.add_argument("--slug", help="Process a single DB unit slug")
    parser.add_argument("--force", action="store_true",
                        help="Re-scrape even if weapons_json already set")
    parser.add_argument("--dry-run", action="store_true",
                        help="Parse and print JSON — do not commit to DB")
    parser.add_argument("--no-cache", action="store_true",
                        help="Bypass HTML cache, always fetch live")
    args = parser.parse_args()

    factions = [args.faction] if args.faction else None

    app = create_app()
    with app.app_context():
        run(
            factions=factions,
            unit_slug=args.slug,
            force=args.force,
            dry_run=args.dry_run,
            use_cache=not args.no_cache,
        )


if __name__ == "__main__":
    main()
