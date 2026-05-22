#!/usr/bin/env python3
"""
Backfill wahapedia_url for aos4 units that currently have it NULL/empty.

Strategy:
  1. For each faction with missing URLs, fetch (or use cached) the faction
     index page on Wahapedia.
  2. Parse unit links from the index.
  3. Normalize names on both sides and match DB units to Wahapedia links.
  4. Write matched URLs back to the DB (idempotent — skips units already
     having a URL unless --force is given).

Usage:
    python scripts/backfill_wahapedia_urls.py
    python scripts/backfill_wahapedia_urls.py --faction stormcast-eternals
    python scripts/backfill_wahapedia_urls.py --dry-run
    python scripts/backfill_wahapedia_urls.py --no-cache
    python scripts/backfill_wahapedia_urls.py --faction skaven --dry-run
"""

import sys
import os
import re
import time
import argparse
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

import requests
from bs4 import BeautifulSoup

from app import create_app
from app.extensions import db
from app.models.game import Unit, Faction, GameSystem

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CACHE_DIR = REPO_ROOT / "scripts" / "_cache" / "wahapedia" / "_indexes"
WAHAPEDIA_BASE = "https://wahapedia.ru"
REQUEST_DELAY = 1.5
REQUEST_TIMEOUT = 30
USER_AGENT = "waaahgame-scraper/1.0"
COMMIT_BATCH = 50

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Faction slug mapping
#
# DB slug → list of Wahapedia slugs to scrape for that faction.
# For most factions the DB slug == Wahapedia slug (not listed here).
# Listed only where they differ or where one DB faction spans multiple
# Wahapedia faction pages.
# ---------------------------------------------------------------------------

FACTION_SLUG_MAP: dict[str, list[str]] = {
    # DB slug              : [wahapedia slug(s)]
    "skaventide"           : ["skaven"],
    "tzeentch-arcanites"   : ["disciples-of-tzeentch"],
    "slaanesh-sybarites"   : ["hedonites-of-slaanesh"],
    "orruk-warclans"       : ["ironjawz", "kruleboyz", "bonesplitterz"],
    # 404 factions — units found on other pages:
    "deathlords"           : ["ossiarch-bonereapers"],   # Morghast Archai/Harbinger
    "beasts-of-the-grave"  : ["soulblight-gravelords"],  # Revenant Draconith
    "monsters-of-chaos"    : ["slaves-to-darkness", "beasts-of-chaos"],
}

# ---------------------------------------------------------------------------
# HTTP / cache
# ---------------------------------------------------------------------------

def index_cache_path(wahapedia_slug: str) -> Path:
    return CACHE_DIR / f"{wahapedia_slug}.html"


def fetch_index(wahapedia_slug: str, use_cache: bool = True) -> str | None:
    path = index_cache_path(wahapedia_slug)
    if use_cache and path.exists():
        log.debug("Cache hit: %s", path)
        return path.read_text(encoding="utf-8", errors="replace")

    url = f"{WAHAPEDIA_BASE}/aos4/factions/{wahapedia_slug}/"
    log.info("Fetching index: %s", url)
    time.sleep(REQUEST_DELAY)
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

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    path.write_text(resp.text, encoding="utf-8")
    log.debug("Cached -> %s", path)
    return resp.text


# ---------------------------------------------------------------------------
# Parse index page → list of (display_name, absolute_url)
# ---------------------------------------------------------------------------

def parse_index(html: str, wahapedia_slug: str) -> list[tuple[str, str]]:
    """
    Returns [(display_name, absolute_url), ...] for all unit links found
    in the faction index HTML.

    Unit links match:  /aos4/factions/<slug>/<UnitName>
    Excludes: .html pages, fragment anchors, and the generic faction page.
    """
    soup = BeautifulSoup(html, "html.parser")
    prefix = f"/aos4/factions/{wahapedia_slug}/"
    seen: set[str] = set()
    results: list[tuple[str, str]] = []

    for a in soup.find_all("a", href=True):
        href: str = a["href"]
        if (
            href.startswith(prefix)
            and not href.endswith(".html")
            and "#" not in href
            and href != prefix.rstrip("/")
            and href.rstrip("/") != prefix.rstrip("/")
        ):
            # Remove trailing slash variants
            clean = href.rstrip("/")
            # Must have at least one path segment after the faction slug
            remainder = clean[len(prefix):]
            if not remainder:
                continue
            if clean not in seen:
                seen.add(clean)
                name = a.get_text(strip=True)
                url = f"{WAHAPEDIA_BASE}{clean}"
                results.append((name, url))

    return results


# ---------------------------------------------------------------------------
# Name normalisation
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    """
    Lowercase, strip punctuation (apostrophes, commas, periods), collapse
    whitespace, replace spaces/hyphens with a single space.
    """
    name = name.lower()
    # Remove possessives and punctuation
    name = re.sub(r"[''`’‘]s\b", "", name)   # Grashrak's → grashrak
    name = re.sub(r"[''`’‘]", "", name)
    name = re.sub(r"[,.\-–—]", " ", name)
    name = re.sub(r"[^a-z0-9 ]", "", name)
    name = re.sub(r"\s+", " ", name).strip()
    return name


def depluralize(name: str) -> str:
    """
    Return a version of `name` where each word has its trailing 's' stripped.
    Used for fuzzy plural matching: "Sisters of Slaughter" → "sister of slaughter".
    """
    return " ".join(w.rstrip("s") for w in name.split())


def slug_from_display(name: str) -> str:
    """Convert display name to URL-slug style (hyphen-separated, title-cased)."""
    # Strip special chars, hyphenate
    s = re.sub(r"[''`]", "", name)
    s = re.sub(r"[^a-zA-Z0-9 \-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    return s


# ---------------------------------------------------------------------------
# Match Wahapedia display names → DB units
# ---------------------------------------------------------------------------

def build_matches(
    waha_units: list[tuple[str, str]],
    db_units: list,
) -> dict[int, str]:
    """
    Returns {unit.id: wahapedia_url} for the best matches.

    Matching strategy (in order of preference):
      1. Exact normalised name match.
      2. DB unit name is a prefix of Wahapedia name (e.g. "Gutter Runner" ↔
         "Gutter Runners").
      3. Wahapedia name is a prefix of DB unit name.

    Ambiguous matches (multiple DB units map to the same Wahapedia URL) are
    logged but the first match wins — log is enough for manual review.
    """
    # Build lookup: normalised_name → list[(unit, original_waha_url)]
    waha_by_norm: dict[str, list[tuple[str, str]]] = {}
    for display, url in waha_units:
        n = normalise(display)
        waha_by_norm.setdefault(n, []).append((display, url))

    db_norm: dict[int, str] = {u.id: normalise(u.name) for u in db_units}

    matched: dict[int, str] = {}
    ambiguous: list[str] = []

    for unit in db_units:
        unorm = db_norm[unit.id]

        # 1. Exact match
        if unorm in waha_by_norm:
            candidates = waha_by_norm[unorm]
            if len(candidates) > 1:
                ambiguous.append(f"{unit.name} → {[c[1] for c in candidates]}")
            matched[unit.id] = candidates[0][1]
            continue

        # 2. Prefix match (plural etc.) — "Gutter Runner" ↔ "Gutter Runners"
        prefix_hits = [
            (d, url) for n, cands in waha_by_norm.items()
            for d, url in cands
            if unorm.startswith(n) or n.startswith(unorm)
        ]
        if len(prefix_hits) == 1:
            matched[unit.id] = prefix_hits[0][1]
            continue
        if len(prefix_hits) > 1:
            # Pick the closest-length Wahapedia match
            best = min(prefix_hits, key=lambda x: abs(len(normalise(x[0])) - len(unorm)))
            matched[unit.id] = best[1]
            ambiguous.append(f"multi-prefix {unit.name} → picked {best[1]}")
            continue

        # 3. Word-boundary suffix match — "Concussor" ↔ "Dracothian Guard Concussors"
        #    The DB name (normalised, maybe with trailing 's' stripped) must appear
        #    as a whole-word suffix in the Wahapedia name.
        unorm_singular = unorm.rstrip("s")  # rough de-pluralise
        suffix_hits = []
        for n, cands in waha_by_norm.items():
            # Check if DB name (or singular) is the last word(s) of Wahapedia name
            if n.endswith(" " + unorm) or n.endswith(" " + unorm + "s") or \
               n.endswith(" " + unorm_singular) or n.endswith(" " + unorm_singular + "s"):
                suffix_hits.extend(cands)
            # Also check if Waha name ends with unorm when split by spaces
            n_words = n.split()
            u_words = unorm.split()
            if len(n_words) >= len(u_words) and n_words[-len(u_words):] == u_words:
                # Already caught above if exact, but handles multi-word DB names
                if (n, cands) not in [(x, y) for x, y in [(d, u) for d, u in suffix_hits]]:
                    pass  # deduplicate below
        # Deduplicate suffix_hits by URL
        seen_urls: set[str] = set()
        deduped: list[tuple[str, str]] = []
        for d, url in suffix_hits:
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append((d, url))
        suffix_hits = deduped

        if len(suffix_hits) == 1:
            matched[unit.id] = suffix_hits[0][1]
            continue
        if len(suffix_hits) > 1:
            best = min(suffix_hits, key=lambda x: abs(len(normalise(x[0])) - len(unorm)))
            matched[unit.id] = best[1]
            ambiguous.append(f"multi-suffix {unit.name} → picked {best[1]}")
            continue

        # 4. Depluralize both sides and compare — handles "Sister of Slaughter" ↔
        #    "Sisters of Slaughter" where pluralisation is mid-name.
        unorm_dep = depluralize(unorm)
        dep_hits: list[tuple[str, str]] = []
        for n, cands in waha_by_norm.items():
            n_dep = depluralize(n)
            if unorm_dep == n_dep:
                dep_hits.extend(cands)
        # Deduplicate
        seen_urls = set()
        deduped = []
        for d, url in dep_hits:
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append((d, url))
        dep_hits = deduped

        if len(dep_hits) == 1:
            matched[unit.id] = dep_hits[0][1]
            continue
        if len(dep_hits) > 1:
            best = min(dep_hits, key=lambda x: abs(len(normalise(x[0])) - len(unorm)))
            matched[unit.id] = best[1]
            ambiguous.append(f"multi-deplural {unit.name} → picked {best[1]}")
            continue

        # 5. Substring match — DB name appears anywhere in Wahapedia name (last resort)
        #    Only use when there is exactly one candidate.
        sub_hits = [
            (d, url) for n, cands in waha_by_norm.items()
            for d, url in cands
            if unorm in n or unorm_singular in n
        ]
        # Deduplicate by URL
        seen_urls = set()
        deduped = []
        for d, url in sub_hits:
            if url not in seen_urls:
                seen_urls.add(url)
                deduped.append((d, url))
        sub_hits = deduped

        if len(sub_hits) == 1:
            matched[unit.id] = sub_hits[0][1]
            continue
        # More than 1 sub_hit → too ambiguous, skip

    if ambiguous:
        for msg in ambiguous:
            log.warning("Ambiguous: %s", msg)

    return matched


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(description="Backfill wahapedia_url for aos4 units.")
    p.add_argument("--faction", help="Process only this DB faction slug.")
    p.add_argument("--dry-run", action="store_true", help="Do not write to DB.")
    p.add_argument("--no-cache", action="store_true", help="Force fresh HTTP fetch.")
    p.add_argument("--force", action="store_true",
                   help="Overwrite units that already have a wahapedia_url.")
    p.add_argument("--verbose", action="store_true")
    return p.parse_args()


def main():
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    app = create_app()
    with app.app_context():
        aos4 = GameSystem.query.filter_by(code="aos4").first()
        if not aos4:
            log.error("aos4 GameSystem not found.")
            sys.exit(1)

        # Load all factions (optionally filtered)
        q = Faction.query.filter_by(game_system_id=aos4.id)
        if args.faction:
            q = q.filter_by(slug=args.faction)
        factions = q.all()

        if not factions:
            log.error("No factions found (faction filter: %s).", args.faction)
            sys.exit(1)

        total_matched = 0
        total_skipped = 0
        total_ambiguous = 0
        total_unmatched_db = 0   # DB unit with no Wahapedia match
        total_written = 0

        for faction in sorted(factions, key=lambda f: f.slug):
            # Units missing URL (unless --force)
            if args.force:
                db_units = Unit.query.filter_by(faction_id=faction.id).all()
            else:
                db_units = Unit.query.filter_by(faction_id=faction.id).filter(
                    (Unit.wahapedia_url == None) | (Unit.wahapedia_url == "")
                ).all()

            if not db_units:
                log.debug("Faction %s: no units need URLs, skipping.", faction.slug)
                continue

            log.info("=== Faction: %s (%d units need URLs) ===", faction.slug, len(db_units))

            # Determine which Wahapedia slug(s) to scrape
            waha_slugs = FACTION_SLUG_MAP.get(faction.slug, [faction.slug])

            # Collect all unit links across all mapped Wahapedia pages
            all_waha_units: list[tuple[str, str]] = []
            for waha_slug in waha_slugs:
                html = fetch_index(waha_slug, use_cache=not args.no_cache)
                if html is None:
                    log.warning("Could not fetch index for wahapedia slug '%s'", waha_slug)
                    continue
                units_on_page = parse_index(html, waha_slug)
                log.info("  Wahapedia slug '%s': %d unit links found", waha_slug, len(units_on_page))
                all_waha_units.extend(units_on_page)

            if not all_waha_units:
                log.warning("Faction %s: no Wahapedia unit links found.", faction.slug)
                total_unmatched_db += len(db_units)
                continue

            # Match
            match_map = build_matches(all_waha_units, db_units)

            matched_count = len(match_map)
            unmatched_count = len(db_units) - matched_count
            total_matched += matched_count
            total_unmatched_db += unmatched_count

            if unmatched_count:
                unmatched_units = [u for u in db_units if u.id not in match_map]
                log.warning(
                    "  Unmatched DB units (%d): %s",
                    unmatched_count,
                    [u.name for u in unmatched_units],
                )

            log.info(
                "  Match results: %d matched, %d unmatched",
                matched_count,
                unmatched_count,
            )

            if args.dry_run:
                for unit in db_units:
                    if unit.id in match_map:
                        log.info("  [DRY] %s -> %s", unit.name, match_map[unit.id])
                    else:
                        log.info("  [DRY] NO MATCH: %s", unit.name)
                continue

            # Write
            written = 0
            for i, unit in enumerate(db_units):
                if unit.id in match_map:
                    unit.wahapedia_url = match_map[unit.id]
                    written += 1
                    if (i + 1) % COMMIT_BATCH == 0:
                        db.session.commit()
                        log.info("  Committed batch (%d so far).", written)

            if written:
                db.session.commit()

            total_written += written
            log.info("  Wrote %d URLs for faction %s.", written, faction.slug)

        # Summary
        log.info("=" * 60)
        log.info("SUMMARY")
        log.info("  Factions processed : %d", len(factions))
        log.info("  URLs matched       : %d", total_matched)
        log.info("  DB units unmatched : %d", total_unmatched_db)
        if not args.dry_run:
            log.info("  URLs written to DB : %d", total_written)
        else:
            log.info("  (dry-run — nothing written)")
        log.info("=" * 60)


if __name__ == "__main__":
    main()
