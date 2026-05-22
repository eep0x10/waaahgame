#!/usr/bin/env python3
"""
Wahapedia scraper for waaahgame — Age of Sigmar 4th edition units.

Usage:
    python scripts/scrape_wahapedia.py --slug clanrats --dry-run
    python scripts/scrape_wahapedia.py --slug clanrats
    python scripts/scrape_wahapedia.py --limit 10
    python scripts/scrape_wahapedia.py --limit 10 --force
    python scripts/scrape_wahapedia.py --no-cache --slug grey-seer

HTML structure (Wahapedia AoS4):
    div.datasheet                    — root warscroll container (one per page)
      div.wsCharLegend
        div.AoS_profile              — characteristic stats
          div.wsMove / .wsWounds / .wsSave / .wsBravery
      div.wsBody
        div.wsBodyTop
          div.wsTable                — melee (or ranged) weapons table
          div.Columns2_AoS           — abilities
        div.wsBodyBottom
          td.wsKeywordLine1          — unit-type keywords (INFANTRY, HERO, etc.)
          td.wsKeywordLine2          — faction keywords (CHAOS, SKAVEN, etc.)

Stat class → label mapping (AoS4):
    wsMove    → Move
    wsWounds  → Wounds    (Health in 4th ed parlance; Wahapedia still shows "Wounds")
    wsSave    → Save
    wsBravery → Control   (AoS4 replaced Bravery with Control)

Ability structure:
    div.BreakInsideAvoid
      td.abHeader      — timing/phase label
      div.abBody       — bold name + description text

Weapon structure (wsTable):
    tr.wsHeaderRow — table type label ("MELEE WEAPONS" / "RANGED WEAPONS") + stat headers (Atk/Hit/Wnd/Rnd/Dmg or Rng/Atk/Hit/Wnd/Rnd/Dmg)
    tr.wsDataRow.wsDataRow_short — weapon name row (with wsWeaponAbility spans for abilities)
    tr.wsDataRow.dsColorFrST    — stat values in td.wsCell
"""

import sys
import os
import time
import argparse
import logging
import re
from pathlib import Path
from copy import copy

# Bootstrap: insert repo root so `from app import create_app` works
REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import requests
from bs4 import BeautifulSoup

from app import create_app
from app.extensions import db
from app.models.game import Unit

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

CACHE_DIR = REPO_ROOT / "scripts" / "_cache" / "wahapedia"
REQUEST_DELAY = 1.5          # seconds between live HTTP requests
REQUEST_TIMEOUT = 30         # seconds per request
USER_AGENT = "waaahgame-scraper/1.0"
COMMIT_BATCH = 25

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# Stat class-name → stored key label
STAT_CLASS_MAP = {
    "wsMove": "Move",
    "wsWounds": "Wounds",
    "wsSave": "Save",
    "wsBravery": "Control",
    "wsWard": "Ward",  # present on units with a Ward save (e.g. AoS_profile_Ward)
}

# All known AoS_profile container class variants
AOS_PROFILE_CLASSES = ("AoS_profile", "AoS_profile_Ward", "AoS_profile_NoSave", "AoS_profile_Ward_RDP")


# ---------------------------------------------------------------------------
# HTTP / cache helpers
# ---------------------------------------------------------------------------

def url_to_cache_path(url: str) -> Path:
    """
    Derive a local cache path from a Wahapedia URL.

    Example:
        https://wahapedia.ru/aos4/factions/skaven/Clanrats
        -> scripts/_cache/wahapedia/skaven/Clanrats.html
    """
    # Strip scheme + host
    path_part = re.sub(r"^https?://[^/]+", "", url)
    # Drop leading /aos4/factions/
    path_part = re.sub(r"^/aos4/factions/", "", path_part)
    parts = [p for p in path_part.split("/") if p]
    if len(parts) >= 2:
        faction_slug, unit_slug = parts[0], parts[1]
    elif len(parts) == 1:
        faction_slug, unit_slug = "unknown", parts[0]
    else:
        faction_slug, unit_slug = "unknown", "unknown"
    return CACHE_DIR / faction_slug / f"{unit_slug}.html"


def fetch_html(url: str, use_cache: bool = True) -> str | None:
    """
    Return HTML for *url*. Reads from disk cache when available unless
    *use_cache* is False. Writes fetched content to cache. Returns None on
    HTTP failure.
    """
    cache_path = url_to_cache_path(url)

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
    log.debug("Cached to %s", cache_path)
    return html


# ---------------------------------------------------------------------------
# Parsing helpers
# ---------------------------------------------------------------------------

def _clean_soup(html_fragment: str) -> BeautifulSoup:
    return BeautifulSoup(html_fragment, "html.parser")


def _is_in_tooltips(el) -> bool:
    """Return True if *el* is inside a div.tooltip_templates (hidden content)."""
    p = el
    while p is not None:
        cls = p.get("class") or []
        if "tooltip_templates" in cls:
            return True
        p = p.parent
    return False


def parse_stats(datasheet) -> dict:
    """
    Parse characteristic stats from an AoS_profile* div inside *datasheet*.

    Handles all known variants:
        AoS_profile          — standard units
        AoS_profile_Ward     — units with a Ward save (adds wsWard element)
        AoS_profile_NoSave   — units without an armour save

    Returns a dict like {"Move": "6\"", "Wounds": "1", "Save": "5+", "Control": "1"}
    (plus "Ward": "5+" when present).
    """
    profile = None
    for cls in AOS_PROFILE_CLASSES:
        profile = datasheet.find(class_=cls)
        if profile:
            break
    if not profile:
        return {}
    stats = {}
    for cls, label in STAT_CLASS_MAP.items():
        el = profile.find(class_=cls)
        if el:
            val = el.get_text(strip=True)
            if val:
                stats[label] = val
    return stats


def parse_weapons(datasheet) -> list[dict]:
    """
    Parse all weapon tables from *datasheet*.

    Each weapon is a dict with keys: Name, Type (MELEE WEAPONS / RANGED WEAPONS),
    plus the stat column headers (Atk, Hit, Wnd, Rnd, Dmg — ranged also has Rng).
    If the weapon has special abilities they are stored under the "Abilities" key.
    """
    weapons = []

    for tbl in datasheet.find_all(class_="wsTable"):
        # Determine table label (MELEE WEAPONS / RANGED WEAPONS)
        type_span = tbl.find("span", class_="wsDataCell_long")
        weapon_type = type_span.get_text(strip=True) if type_span else "WEAPONS"

        # Stat column headers
        stat_headers = [h.get_text(strip=True) for h in tbl.find_all(class_="wsHeaderCell")]

        rows = tbl.find_all(class_="wsDataRow")
        i = 0
        while i < len(rows):
            row = rows[i]
            row_classes = row.get("class", [])

            if "wsDataRow_short" in row_classes:
                # --- weapon name row ---
                # Grab ability text before decomposing
                ability_spans = row.find_all(class_="wsWeaponAbility")
                ability_text = ", ".join(
                    s.get_text(strip=True) for s in ability_spans if s.get_text(strip=True)
                )

                # Build a clean copy for name extraction
                name_soup = _clean_soup(str(row))
                for ab in name_soup.find_all(class_="wsWeaponAbility"):
                    ab.decompose()
                for img in name_soup.find_all("img"):
                    img.decompose()
                raw_name = name_soup.get_text(strip=True)
                # Strip trailing brackets: "Weapon Name [...]" -> "Weapon Name"
                weapon_name = re.sub(r"\s*\[.*?\]\s*$", "", raw_name).strip()

                # --- stat row (next sibling) ---
                if i + 1 < len(rows):
                    stat_row = rows[i + 1]
                    stat_cells = stat_row.find_all(class_="wsCell")
                    stats_vals = [c.get_text(strip=True) for c in stat_cells]

                    weapon: dict = {"Name": weapon_name, "Type": weapon_type}
                    for header, val in zip(stat_headers, stats_vals):
                        weapon[header] = val
                    if ability_text:
                        weapon["Abilities"] = ability_text

                    weapons.append(weapon)
                    i += 2
                    continue

            i += 1

    return weapons


def parse_abilities(datasheet) -> list[dict]:
    """
    Parse ability cards from *datasheet*.

    Returns a list of dicts with keys:
        name        — ability name (uppercased on Wahapedia, preserved)
        timing      — phase/timing string (e.g. "End of Any Turn", "Passive")
        description — cleaned effect text

    Excludes:
        - abilities inside div.tooltip_templates (hidden pop-up content)
        - the KEYWORDS pseudo-ability header
    """
    abilities = []
    seen_names: set[str] = set()

    for block in datasheet.find_all(class_="BreakInsideAvoid"):
        ab_header = block.find(class_="abHeader")
        ab_body = block.find(class_="abBody")
        if not ab_header or not ab_body:
            continue
        if _is_in_tooltips(block):
            continue

        # Skip the KEYWORDS block (uses abHeader with class abKeywordsBody)
        if ab_header.find(class_="abKeywordsBody") or "abKeywords" in " ".join(
            block.get("class", [])
        ):
            continue
        if ab_body.find(class_="abKeywords") or "abKeywords" in " ".join(
            (ab_body.parent.get("class", []) if ab_body.parent else [])
        ):
            continue

        # Timing: text of abHeader without the icon image
        hdr_copy = _clean_soup(str(ab_header))
        for img in hdr_copy.find_all("img"):
            img.decompose()
        timing = hdr_copy.get_text(strip=True)

        # Ability name: first <b> tag in ab_body (strip ShowFluff colon span)
        name_el = ab_body.find("b")
        if not name_el:
            continue
        nm_copy = _clean_soup(str(name_el))
        for sf in nm_copy.find_all(class_="ShowFluff"):
            sf.decompose()
        name = nm_copy.get_text(strip=True)

        if not name or name in seen_names:
            continue
        seen_names.add(name)

        # Description: ab_body text, minus fluff flavour text (class legend4)
        body_copy = _clean_soup(str(ab_body))
        for sf in body_copy.find_all(class_="ShowFluff"):
            if "legend4" in sf.get("class", []):
                sf.decompose()
        for span in body_copy.find_all("span"):
            span.unwrap()
        for img in body_copy.find_all("img"):
            img.decompose()
        desc = " ".join(body_copy.get_text(separator=" ").split())

        abilities.append({"name": name, "timing": timing, "description": desc})

    return abilities


def parse_keywords(datasheet) -> list[str]:
    """
    Parse keywords from wsKeywordLine1 and wsKeywordLine2 in *datasheet*.

    Keywords that include modifiers (e.g. WIZARD(1), MUSICIAN(1/20)) are
    kept as a single token by reading the outer tooltipk* span's text.
    """
    keywords: list[str] = []

    for line_cls in ("wsKeywordLine1", "wsKeywordLine2"):
        line_el = datasheet.find(class_=line_cls)
        if not line_el:
            continue
        for span in line_el.find_all(
            "span",
            class_=lambda c: c is not None and any(x.startswith("tooltipk") for x in c.split()),
        ):
            text = span.get_text(strip=True).replace(" ", "")
            if text:
                keywords.append(text)

    return keywords


def parse_page(html: str) -> dict | None:
    """
    Parse a full Wahapedia page. Returns a dict with keys:
        stats, weapons, abilities, keywords
    or None if no datasheet was found.
    """
    soup = BeautifulSoup(html, "html.parser")
    datasheet = soup.find(class_="datasheet")
    if not datasheet:
        log.warning("No div.datasheet found on page")
        return None

    return {
        "stats": parse_stats(datasheet),
        "weapons": parse_weapons(datasheet),
        "abilities": parse_abilities(datasheet),
        "keywords": parse_keywords(datasheet),
    }


# ---------------------------------------------------------------------------
# Main scraping loop
# ---------------------------------------------------------------------------

def build_query(slug: str | None, force: bool, slugs: list[str] | None = None):
    """Return a SQLAlchemy query for units to scrape."""
    q = Unit.query.filter(Unit.wahapedia_url.isnot(None))
    if slug:
        q = q.filter(Unit.slug == slug)
    if slugs:
        q = q.filter(Unit.slug.in_(slugs))
    if not force:
        # Skip units that already have weapon data
        q = q.filter(
            (Unit.weapons_json == None)
            | (Unit.weapons_json == [])
            | (Unit.weapons_json == "[]")
        )
    return q


def run(
    slug: str | None = None,
    limit: int | None = None,
    force: bool = False,
    dry_run: bool = False,
    use_cache: bool = True,
    slugs: list[str] | None = None,
):
    """Main entry point for the scrape loop."""
    counters = {
        "scraped": 0,
        "skipped_no_url": 0,
        "skipped_existing": 0,
        "parse_failed": 0,
        "http_failed": 0,
    }

    query = build_query(slug, force, slugs=slugs)
    units_to_check = query.all()

    # If not using force, also count the skipped-existing units for reporting
    if not force and not slug:
        total_with_url = Unit.query.filter(Unit.wahapedia_url.isnot(None)).count()
        total_no_url = Unit.query.filter(Unit.wahapedia_url.is_(None)).count()
        counters["skipped_no_url"] = total_no_url
        already_done = total_with_url - len(units_to_check)
        counters["skipped_existing"] = already_done

    if limit:
        units_to_check = units_to_check[:limit]

    log.info("Units to process: %d", len(units_to_check))

    pending_commit: list[Unit] = []
    last_request_time = 0.0

    for unit in units_to_check:
        log.info("Processing: %s (%s)", unit.slug, unit.wahapedia_url)

        # Politeness delay (only for live requests)
        cache_path = url_to_cache_path(unit.wahapedia_url)
        is_cached = use_cache and cache_path.exists()
        if not is_cached:
            elapsed = time.monotonic() - last_request_time
            if elapsed < REQUEST_DELAY:
                time.sleep(REQUEST_DELAY - elapsed)

        html = fetch_html(unit.wahapedia_url, use_cache=use_cache)
        if not is_cached:
            last_request_time = time.monotonic()

        if html is None:
            counters["http_failed"] += 1
            log.error("HTTP failed for %s — skipping", unit.slug)
            continue

        parsed = parse_page(html)
        if parsed is None:
            counters["parse_failed"] += 1
            log.error("Parse failed for %s — no datasheet found", unit.slug)
            continue

        if dry_run:
            import json
            print(f"\n{'='*60}")
            print(f"DRY-RUN: {unit.slug} ({unit.wahapedia_url})")
            print(f"  stats:    {json.dumps(parsed['stats'])}")
            print(f"  weapons:  {json.dumps(parsed['weapons'][:3], indent=2)}")
            print(f"  abilities (first 2):")
            for ab in parsed["abilities"][:2]:
                print(f"    [{ab['timing']}] {ab['name']}: {ab['description'][:80]}...")
            print(f"  keywords: {parsed['keywords']}")
            counters["scraped"] += 1
            continue

        # Write to model
        unit.stats_json = parsed["stats"]
        unit.weapons_json = parsed["weapons"]
        unit.abilities_json = parsed["abilities"]
        unit.keywords_json = parsed["keywords"]

        db.session.add(unit)
        pending_commit.append(unit)
        counters["scraped"] += 1

        if len(pending_commit) >= COMMIT_BATCH:
            db.session.commit()
            log.info("Committed batch of %d", len(pending_commit))
            pending_commit.clear()

    # Final commit
    if pending_commit and not dry_run:
        db.session.commit()
        log.info("Committed final batch of %d", len(pending_commit))

    print("\n" + "=" * 40)
    print("SCRAPE SUMMARY")
    print("=" * 40)
    for key, val in counters.items():
        print(f"  {key:<22}: {val}")
    print("=" * 40)


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Scrape Wahapedia warscrolls into waaahgame DB")
    parser.add_argument("--slug", help="Process a single unit by slug (e.g. clanrats)")
    parser.add_argument("--slugs", help="Comma-separated list of slugs to process (e.g. clanrats,stormvermin)")
    parser.add_argument("--limit", type=int, help="Process at most N units")
    parser.add_argument("--force", action="store_true", help="Re-scrape even if weapons_json already set")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print JSON, do not commit")
    parser.add_argument("--no-cache", action="store_true", help="Bypass HTML cache, always fetch live")
    args = parser.parse_args()

    slugs_list = [s.strip() for s in args.slugs.split(",")] if args.slugs else None

    app = create_app()
    with app.app_context():
        run(
            slug=args.slug,
            limit=args.limit,
            force=args.force,
            dry_run=args.dry_run,
            use_cache=not args.no_cache,
            slugs=slugs_list,
        )


if __name__ == "__main__":
    main()
