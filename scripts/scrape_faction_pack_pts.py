#!/usr/bin/env python3
"""
AoS4 faction pack points-cost backfiller.

Strategy:
  1. Download faction pack PDFs (cached) — extract unit roster for cross-reference.
     NOTE: These PDFs contain warscroll rules only, NOT points costs.
  2. For each faction, fetch the wahapedia faction index to build a name→URL map.
  3. For each DB unit with points_cost=0, resolve its wahapedia URL (stored in DB
     or matched via the index), then parse Points from PitchedBattleProfile.
  4. Update DB — only overwrites pts=0 records.

Points in AoS4 are published separately (General's Handbook matched-play documents).
Wahapedia mirrors these and surfaces them in <div class="PitchedBattleProfile">.

Usage:
    python scripts/scrape_faction_pack_pts.py --faction seraphon --dry-run
    python scripts/scrape_faction_pack_pts.py --all
    python scripts/scrape_faction_pack_pts.py --all --no-cache
    python scripts/scrape_faction_pack_pts.py --validate
"""

import sys
import os
import re
import time
import sqlite3
import argparse
import logging
import urllib.request
import ssl
from pathlib import Path
from typing import Optional

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

CACHE_DIR       = REPO_ROOT / "scripts" / "_cache" / "factionpacks"
WAHA_CACHE_DIR  = REPO_ROOT / "scripts" / "_cache" / "wahapedia_pts"
DB_PATH         = REPO_ROOT / "instance" / "waaahgame.db"

REQUEST_DELAY   = 1.2   # seconds between live HTTP requests
REQUEST_TIMEOUT = 30
USER_AGENT      = "waaahgame-pts-scraper/1.0"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Faction pack PDF URLs (pre-recon'd — do NOT change)
# ---------------------------------------------------------------------------

FACTION_PDF_URLS = {
    "stormcast-eternals":    "https://assets.warhammer-community.com/ageofsigmar_factionpacks_stormcasteternals_eng_24-cxtpmnmzx4.pdf",
    "cities-of-sigmar":      "https://assets.warhammer-community.com/ageofsigmar_factionpacks_citiesofsigmar_eng_24.09-a8wowsd8yn.pdf",
    "kharadron-overlords":   "https://assets.warhammer-community.com/ageofsigmar_factionpacks_kharadronoverlords_eng_24-xsn8wawhla.pdf",
    "fyreslayers":           "https://assets.warhammer-community.com/ageofsigmar_factionpacks_fyreslayers_eng_24-0ik42fbwys.pdf",
    "idoneth-deepkin":       "https://assets.warhammer-community.com/ageofsigmar_factionpacks_idonethdeepkin_eng_24-e2ow1vpfsl.pdf",
    "lumineth-realm-lords":  "https://assets.warhammer-community.com/ageofsigmar_factionpacks_luminethrealmlords_eng_0426_23-gl4t2coe6c.pdf",
    "daughters-of-khaine":   "https://assets.warhammer-community.com/ageofsigmar_factionpacks_daughtersofkhaine_eng_24-lbuuurqyya.pdf",
    "seraphon":              "https://assets.warhammer-community.com/ageofsigmar_factionpacks_seraphon_eng_0426_23-lblbppxtmu.pdf",
    "sylvaneth":             "https://assets.warhammer-community.com/ageofsigmar_factionpacks_sylvaneth_eng_0426_23.10.24.pdf",
    "blades-of-khorne":      "https://assets.warhammer-community.com/ageofsigmar_factionpacks_bladesofkhorne_eng_24.09-rqgu0wrwts.pdf",
    "disciples-of-tzeentch": "https://assets.warhammer-community.com/eng_aos_disciples_of_tzeentch_dec24-omwrlol7xs-vlsfbnk2sl.pdf",
    "hedonites-of-slaanesh": "https://assets.warhammer-community.com/ageofsigmar_factionpacks_hedonitesofslaanesh_eng_0426_23-5wpuifijva.pdf",
    "maggotkin-of-nurgle":   "https://assets.warhammer-community.com/ageofsigmar_factionpacks_maggotkinofnurgle_eng_0426_23-e5yyyo8qpm.pdf",
    "slaves-to-darkness":    "https://assets.warhammer-community.com/ageofsigmar_factionpacks_slavestodarkness_eng_24-vbyjuu4xia.pdf",
    "flesh-eater-courts":    "https://assets.warhammer-community.com/ageofsigmar_factionpacks_flesheatercourts_eng_24-cadfqbyvmd.pdf",
    "nighthaunt":            "https://assets.warhammer-community.com/rules-downloads/age-of-sigmar/nighthaunt-v2---sept-2024/ageofsigmar_factionpacks_nighthaunt_eng_30.09.16.pdf",
    "soulblight-gravelords": "https://assets.warhammer-community.com/ageofsigmar_factionpacks_soulblightgravelords_eng_0426_23.10-eni5hl0kgn.pdf",
    "ossiarch-bonereapers":  "https://assets.warhammer-community.com/ageofsigmar_factionpacks_ossiarchbonereapers_eng_27-hfliyxyry7.pdf",
    "gloomspite-gitz":       "https://assets.warhammer-community.com/ageofsigmar_factionpacks_gloomspitegitz_eng_24-ft6e0gu1ko.pdf",
    "orruk-warclans":        "https://assets.warhammer-community.com/ageofsigmar_factionpacks_orrukwarclans_eng_24-ru8wsnahal.pdf",
    "ogor-mawtribes":        "https://assets.warhammer-community.com/ageofsigmar_factionpacks_ogormawtribes_eng_24-isl4vxudti.pdf",
    "sons-of-behemat":       "https://assets.warhammer-community.com/ageofsigmar_factionpacks_sonsofbehemat_eng_24.09-luoyijb7ok.pdf",
}

# Factions with NO faction pack PDF (no points update possible from PDF route)
PDF_GAPS = [
    "beasts-of-chaos",      # No separate AoS4 faction pack
    "beasts-of-the-grave",  # Sub-faction of Soulblight
    "deathlords",           # Sub-faction / no separate pack
    "monsters-of-chaos",    # No separate AoS4 faction pack
    "skaven",               # DB fragment; skaventide is the canonical faction
    "skaventide",           # Points covered by earlier hardcoded work; no PDF
    "slaanesh-sybarites",   # Sub-faction of Hedonites
    "tzeentch-arcanites",   # Sub-faction of Disciples
]

WAHAPEDIA_BASE = "https://wahapedia.ru/aos4/factions"

# ---------------------------------------------------------------------------
# Subfaction → parent faction routing
# Units belonging to subfactions live under the parent faction on Wahapedia.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Manual name corrections: DB name → Wahapedia name (for typos/hard renames)
# ---------------------------------------------------------------------------

DB_NAME_CORRECTIONS: dict[str, str] = {
    # DB has 'Isharaan' (two a's); Wahapedia spells it 'Isharann' (double n)
    "Isharaan Soulrender": "Isharann Soulrender",
    # AoS4 rename: 'Fury' → 'Chaos Furies' on Wahapedia (plural page)
    "Fury": "Chaos Furies",
    # AoS4 rename: 'Bat Swarm' → 'Fell Bats' on Wahapedia
    "Bat Swarm": "Fell Bats",
    # Gloomspite Gobbapalooza sub-members: each DB unit maps to the parent Gobbapalooza page
    "Boggleye":    "Gobbapalooza",
    "Brewgit":     "Gobbapalooza",
    "Scaremonger": "Gobbapalooza",
    "Shroomancer": "Gobbapalooza",
    "Spiker":      "Gobbapalooza",
}

# ---------------------------------------------------------------------------
# Subfaction → parent faction routing
# Units belonging to subfactions live under the parent faction on Wahapedia.
# ---------------------------------------------------------------------------

SUBFACTION_WAHA_SLUG: dict[str, str] = {
    "slaanesh-sybarites":  "hedonites-of-slaanesh",
    "tzeentch-arcanites":  "disciples-of-tzeentch",
    "beasts-of-the-grave": "soulblight-gravelords",
    "deathlords":          "ossiarch-bonereapers",
    "monsters-of-chaos":   "beasts-of-chaos",
    # skaventide units live under wahapedia 'skaven' slug
    "skaventide":          "skaven",
}

# ---------------------------------------------------------------------------
# SSL context
# ---------------------------------------------------------------------------

_ssl_ctx = ssl.create_default_context()
_ssl_ctx.check_hostname = False
_ssl_ctx.verify_mode = ssl.CERT_NONE


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def normalise(name: str) -> str:
    """Lowercase, strip punctuation/articles, collapse spaces."""
    n = name.lower()
    n = re.sub(r"[^a-z0-9 ]", " ", n)
    n = re.sub(r"\s+", " ", n).strip()
    # Strip trailing 's' to handle singular/plural mismatch
    return n


def norm_dedup(name: str) -> str:
    """Extra-aggressive normalisation for dedup matching: strip trailing s."""
    n = normalise(name).rstrip("s")
    return n.strip()


def http_get(url: str, cache_path: Optional[Path] = None, no_cache: bool = False) -> Optional[bytes]:
    """Fetch URL with optional file cache. Returns bytes or None on error."""
    if cache_path and cache_path.exists() and not no_cache:
        return cache_path.read_bytes()
    try:
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
        resp = urllib.request.urlopen(req, context=_ssl_ctx, timeout=REQUEST_TIMEOUT)
        data = resp.read()
        if cache_path:
            cache_path.parent.mkdir(parents=True, exist_ok=True)
            cache_path.write_bytes(data)
        return data
    except Exception as e:
        log.debug(f"HTTP {url}: {e}")
        return None


# ---------------------------------------------------------------------------
# Wahapedia faction index
# ---------------------------------------------------------------------------

def fetch_waha_faction_index(faction_slug: str, no_cache: bool = False) -> dict[str, str]:
    """
    Fetch the wahapedia faction index page and return a dict of:
        normalised_unit_name -> full_wahapedia_url

    Also returns a secondary dict with dedup-normalised keys for fuzzy matching.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        return {}

    url = f"{WAHAPEDIA_BASE}/{faction_slug}/"
    cache_path = WAHA_CACHE_DIR / faction_slug / "_index.html"
    data = http_get(url, cache_path, no_cache=no_cache)
    if not data:
        log.warning(f"Could not fetch wahapedia index for {faction_slug}")
        return {}

    html = data.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    index: dict[str, str] = {}
    pattern = re.compile(rf"/aos4/factions/{re.escape(faction_slug)}/([^/#?]+)$")

    for a in soup.find_all("a", href=pattern):
        href = a.get("href", "")
        text = a.get_text(strip=True)
        if not text or href.endswith("/"):
            continue
        full_url = f"https://wahapedia.ru{href}"
        index[normalise(text)] = full_url
        # Also store dedup-stripped version
        nd = norm_dedup(text)
        if nd not in index:
            index[nd] = full_url

    log.debug(f"[{faction_slug}] Wahapedia index: {len(index)} entries")
    return index


def _name_variants(unit_name: str) -> list[str]:
    """
    Generate candidate name strings to look up in the Wahapedia index.
    Returns variants in priority order (most specific first).

    Handles:
      - Original name
      - Strip trailing " of <words>" (e.g. "Daemonette of Slaanesh" → "Daemonette")
      - Strip leading faction-prefix word (e.g. "Fyreslayer Doomseeker" → "Doomseeker")
      - Strip leading "Legion " prefix
      - Strip leading "Chaos " prefix
      - Pluralisation: +s, +es, f→ves, fe→ves, y→ies, irregular (wolf→wolves)
      - Combinations of suffix-strip + plural
    """
    variants: list[str] = []

    def _add(v: str) -> None:
        v = v.strip()
        if v and v not in variants:
            variants.append(v)

    def _plurals(base: str) -> list[str]:
        results = []
        bl = base.lower()
        if bl.endswith("wolf"):
            results.append(base[:-4] + "wolves")
            results.append(base[:-4] + "Wolves")
        if bl.endswith("fe"):
            results.append(base[:-2] + "ves")
        if bl.endswith("f") and not bl.endswith("ff"):
            results.append(base[:-1] + "ves")
        if bl.endswith("y") and len(base) > 1 and base[-2].lower() not in "aeiou":
            results.append(base[:-1] + "ies")
        if bl.endswith("s") or bl.endswith("x") or bl.endswith("z") or bl.endswith("ch") or bl.endswith("sh"):
            results.append(base + "es")
        # Default: just add s
        results.append(base + "s")
        return results

    # Base
    _add(unit_name)

    # Strip " of <words>" trailing suffix
    stripped_of = re.sub(r"\s+of\s+\S+.*$", "", unit_name, flags=re.IGNORECASE).strip()
    if stripped_of != unit_name:
        _add(stripped_of)

    # Strip leading single-word faction prefix ("Fyreslayer Doomseeker" → "Doomseeker",
    # "Chaos Gorebeast Chariot" → "Gorebeast Chariot",
    # "Legion Black Coach" → "Black Coach",
    # "Isharaan Soulrender" vs "Isharann Soulrender" handled by normalise fuzzy)
    parts = unit_name.split()
    if len(parts) >= 2:
        without_first = " ".join(parts[1:])
        _add(without_first)

    # Strip leading two-word prefix (e.g. "Chaos Gorebeast Chariot" → already done above,
    # but also "Chaos Warhound" → already covered)

    # All pluralised variants of the above
    for base in list(variants):
        for p in _plurals(base):
            _add(p)

    return variants


def resolve_waha_url(unit_name: str, stored_url: Optional[str],
                     faction_slug: str, waha_index: dict[str, str]) -> Optional[str]:
    """
    Determine the best wahapedia URL for a unit.
    Priority:
      1. Stored DB URL (already validated during earlier scrape)
      2. Exact normalised-name match in index (with expanded variants)
      3. Dedup (singular/plural) match
      4. Prefix/contains match (unit name is contained in a waha name)
    """
    # 1. Use stored URL if present
    if stored_url and stored_url.strip():
        return stored_url.strip()

    # Apply manual name corrections (DB typos / hard renames)
    unit_name = DB_NAME_CORRECTIONS.get(unit_name, unit_name)

    n = normalise(unit_name)
    nd = norm_dedup(unit_name)

    # 2. Try all name variants (normalised)
    for variant in _name_variants(unit_name):
        nv = normalise(variant)
        if nv in waha_index:
            return waha_index[nv]
        # Also dedup version
        nvd = norm_dedup(variant)
        if nvd in waha_index:
            return waha_index[nvd]

    # 3. Dedup match on original
    if nd in waha_index:
        return waha_index[nd]

    # 4. Prefix/contains match — db name (or a variant) is contained in a waha name
    all_norms = [normalise(v) for v in _name_variants(unit_name)]
    all_norms_d = [norm_dedup(v) for v in _name_variants(unit_name)]
    for waha_name, waha_url in waha_index.items():
        # Original normalised name or its dedup form
        if n in waha_name or waha_name.startswith(nd):
            return waha_url
        # Any variant normalised/deduped form
        for nv in all_norms:
            if nv and nv in waha_name:
                return waha_url
        for nvd in all_norms_d:
            if nvd and waha_name.startswith(nvd):
                return waha_url

    return None


# ---------------------------------------------------------------------------
# Wahapedia points extraction
# ---------------------------------------------------------------------------

def _waha_cache_path(waha_url: str) -> Path:
    m = re.search(r"wahapedia\.ru/aos4/factions/([^/]+)/([^/?#]+)", waha_url)
    if m:
        return WAHA_CACHE_DIR / m.group(1) / f"{m.group(2)}.html"
    slug = re.sub(r"[^a-z0-9]", "_", waha_url.lower())[-80:]
    return WAHA_CACHE_DIR / f"{slug}.html"


def fetch_pts_from_wahapedia(waha_url: str, no_cache: bool = False) -> Optional[int]:
    """
    Fetch wahapedia unit page and return Points from PitchedBattleProfile.
    Returns int or None.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error("beautifulsoup4 not installed")
        return None

    cache_path = _waha_cache_path(waha_url)
    data = http_get(waha_url, cache_path, no_cache=no_cache)
    if not data:
        return None

    html = data.decode("utf-8", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    pbps = soup.find_all(class_="PitchedBattleProfile")
    if not pbps:
        return None

    for pbp in pbps:
        m = re.search(r"Points\s*:\s*(\d+)", pbp.get_text(" ", strip=True))
        if m:
            return int(m.group(1))
    return None


# ---------------------------------------------------------------------------
# PDF download & warscroll name extraction
# ---------------------------------------------------------------------------

_WARSCROLL_SKIP = frozenset({
    "WARSCROLL", "MOVE", "CONTROL", "MELEE", "WEAPONS", "RANGED", "SAVE",
    "FACTION", "PACK", "SPEARHEAD", "BATTLE", "PROFILE", "TRAITS",
    "September", "October", "November", "December", "2024", "2023",
    "HTLAEH", "H", "T", "S", "A", "E", "V", "L", "•",
    # faction name tokens
    "STORMCAST", "ETERNALS", "SERAPHON", "KHORNE", "BLADES", "OF", "THE",
    "CITIES", "SIGMAR", "KHARADRON", "OVERLORDS", "FYRESLAYERS",
    "IDONETH", "DEEPKIN", "LUMINETH", "REALM", "LORDS",
    "DAUGHTERS", "KHAINE", "SYLVANETH", "DISCIPLES", "TZEENTCH",
    "HEDONITES", "SLAANESH", "MAGGOTKIN", "NURGLE", "SLAVES", "DARKNESS",
    "FLESH", "EATER", "COURTS", "NIGHTHAUNT", "SOULBLIGHT", "GRAVELORDS",
    "OSSIARCH", "BONEREAPERS", "GLOOMSPITE", "GITZ", "ORRUK", "WARCLANS",
    "OGOR", "MAWTRIBES", "SONS", "BEHEMAT", "ORDER", "CHAOS", "DEATH",
    "DESTRUCTION",
    # weapon table headers
    "Atk", "Hit", "Wnd", "Rnd", "Dmg", "Rng", "Ability",
})


def download_pdf(faction_slug: str, no_cache: bool = False) -> Optional[Path]:
    url = FACTION_PDF_URLS.get(faction_slug)
    if not url:
        return None
    pdf_path = CACHE_DIR / f"{faction_slug}.pdf"
    if pdf_path.exists() and not no_cache:
        log.info(f"  [PDF] cached {pdf_path.name} ({pdf_path.stat().st_size:,} bytes)")
        return pdf_path
    log.info(f"  [PDF] downloading {faction_slug}")
    data = http_get(url, pdf_path, no_cache=no_cache)
    if data:
        log.info(f"  [PDF] saved {pdf_path.name} ({len(data):,} bytes)")
        return pdf_path
    log.warning(f"  [PDF] download FAILED for {faction_slug}")
    return None


def extract_warscroll_names(pdf_path: Path) -> list[str]:
    """
    Extract unit names from main warscroll pages of a faction pack PDF.
    NOTE: PDFs contain rules only — no points costs.
    This is used only for cross-reference / unmatched-name reporting.

    Uses fast text-only extraction (no word layout) for performance.
    """
    try:
        import pdfplumber
    except ImportError:
        return []

    names = []
    seen: set[str] = set()

    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages:
                # Use fast text extraction only (no layout analysis)
                text = page.extract_text() or ""
                if "WARSCROLL" not in text or "SPEARHEAD" in text:
                    continue
                if not re.search(r"\b(20[0-9]{2}|September|October|November|December)\b", text):
                    continue

                lines = text.split("\n")
                # The unit name is typically in the first ~10 lines, after the
                # '• FACTION WARSCROLL •' line, as ALL-CAPS text
                for line in lines[:15]:
                    stripped = line.strip()
                    # Skip the warscroll banner line and short/empty lines
                    if "WARSCROLL" in stripped or len(stripped) < 3:
                        continue
                    # Skip lines that are purely stats (numbers, save values, etc.)
                    if re.match(r'^[\d"+\-\s]+$', stripped):
                        continue
                    # Skip known non-name lines
                    if stripped in ("MOVE", "CONTROL", "SAVE", "MELEE WEAPONS",
                                    "RANGED WEAPONS", "KEYWORDS"):
                        continue
                    # Look for ALL-CAPS lines (unit names are ALL-CAPS)
                    if stripped.isupper() and len(stripped) >= 3:
                        # Filter out single-letter stat keys and common skips
                        toks = [t for t in stripped.split()
                                if t not in _WARSCROLL_SKIP and len(t) > 1]
                        if toks:
                            candidate = " ".join(toks[:6])
                            if candidate.upper() not in seen:
                                seen.add(candidate.upper())
                                names.append(candidate)
                            break
    except Exception as e:
        log.warning(f"  [PDF] parse error: {e}")

    return names


# ---------------------------------------------------------------------------
# DB helpers
# ---------------------------------------------------------------------------

def get_db() -> sqlite3.Connection:
    """Open DB with generous lock timeout. Retries on initial lock."""
    for attempt in range(10):
        try:
            conn = sqlite3.connect(str(DB_PATH), timeout=60)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 9:
                log.debug(f"DB locked on open, retry {attempt+1}/10...")
                time.sleep(2)
            else:
                raise
    raise RuntimeError("Could not open DB after 10 attempts")


def get_faction_units(faction_slug: str) -> list[dict]:
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT u.id, u.name, u.slug, u.points_cost, u.wahapedia_url
        FROM units u
        JOIN factions f ON u.faction_id = f.id
        WHERE f.slug = ?
          AND f.game_system_id = (SELECT id FROM game_systems WHERE code = 'aos4' LIMIT 1)
        ORDER BY u.name
    """, (faction_slug,))
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return rows


def update_pts(conn: sqlite3.Connection, unit_id: int, pts: int) -> None:
    import time as _time
    for attempt in range(5):
        try:
            conn.execute(
                "UPDATE units SET points_cost = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (pts, unit_id),
            )
            return
        except sqlite3.OperationalError as e:
            if "locked" in str(e).lower() and attempt < 4:
                _time.sleep(2 ** attempt)
            else:
                raise


# ---------------------------------------------------------------------------
# Per-faction pipeline
# ---------------------------------------------------------------------------

def process_faction(faction_slug: str, dry_run: bool = False, no_cache: bool = False,
                    with_pdf: bool = False) -> dict:
    log.info(f"\n{'='*60}")
    log.info(f"FACTION: {faction_slug}")
    log.info(f"{'='*60}")

    result = {
        "faction": faction_slug,
        "pdf_ok": False,
        "pdf_names": [],
        "db_total": 0,
        "already_set": 0,
        "updated": 0,
        "waha_not_found": 0,
        "unmatched_pdf": [],
        "updated_list": [],
        "not_found_list": [],
    }

    # -- DB units --
    db_units = get_faction_units(faction_slug)
    if not db_units:
        log.warning(f"  Faction '{faction_slug}' not in DB — skipping")
        return result
    result["db_total"] = len(db_units)
    log.info(f"  DB units: {len(db_units)}")

    # -- PDF download & name extraction (optional, for cross-reference only) --
    if with_pdf:
        pdf_path = download_pdf(faction_slug, no_cache=no_cache)
        if pdf_path:
            result["pdf_ok"] = True
            result["pdf_names"] = extract_warscroll_names(pdf_path)
            log.info(f"  PDF warscroll names: {len(result['pdf_names'])}")
        time.sleep(0.5)
    else:
        # Still note whether PDF URL exists (for reporting)
        result["pdf_ok"] = faction_slug in FACTION_PDF_URLS

    # -- Wahapedia index --
    # For subfactions, also fetch the parent faction index so unit lookups hit the right pages.
    waha_slug = SUBFACTION_WAHA_SLUG.get(faction_slug, faction_slug)
    log.info(f"  Fetching wahapedia index (slug={waha_slug})...")
    waha_index = fetch_waha_faction_index(waha_slug, no_cache=no_cache)
    if waha_slug != faction_slug:
        log.info(f"  [subfaction] using parent index '{waha_slug}' ({len(waha_index)} entries)")
    log.info(f"  Wahapedia index entries: {len(waha_index)}")
    time.sleep(REQUEST_DELAY)

    # -- Cross-ref PDF names vs DB --
    if result["pdf_names"] and db_units:
        db_norms = {normalise(u["name"]) for u in db_units}
        for pname in result["pdf_names"]:
            pn = normalise(pname)
            pd = norm_dedup(pname)
            if pn not in db_norms and pd + "s" not in db_norms and pd not in db_norms:
                # Check partial match
                if not any(pn in dn or dn in pn for dn in db_norms):
                    result["unmatched_pdf"].append(pname)

    # -- Fetch points for zero-pts units --
    conn = get_db()
    try:
        for unit in db_units:
            if unit["points_cost"] != 0:
                result["already_set"] += 1
                continue

            # Resolve wahapedia URL
            waha_url = resolve_waha_url(
                unit["name"], unit.get("wahapedia_url"), faction_slug, waha_index
            )

            if not waha_url:
                log.warning(f"  NO URL: '{unit['name']}' — no stored URL, no index match")
                result["waha_not_found"] += 1
                result["not_found_list"].append(unit["name"])
                continue

            # Fetch points
            time.sleep(REQUEST_DELAY)
            pts = fetch_pts_from_wahapedia(waha_url, no_cache=no_cache)

            if pts is None:
                log.warning(f"  NO PTS: '{unit['name']}' @ {waha_url}")
                result["waha_not_found"] += 1
                result["not_found_list"].append(unit["name"])
                continue

            log.info(f"  {unit['name']}: {pts} pts")
            result["updated"] += 1
            result["updated_list"].append({"name": unit["name"], "pts": pts, "url": waha_url})

            if not dry_run:
                update_pts(conn, unit["id"], pts)

        if not dry_run:
            for attempt in range(5):
                try:
                    conn.commit()
                    break
                except sqlite3.OperationalError as e:
                    if "locked" in str(e).lower() and attempt < 4:
                        log.warning(f"  Commit locked, retrying ({attempt+1}/5)...")
                        time.sleep(2 ** attempt)
                    else:
                        raise
            log.info(f"  Committed {result['updated']} updates to DB")
        else:
            log.info(f"  [DRY-RUN] Would update {result['updated']} units")

    except Exception as e:
        log.error(f"  Exception: {e}")
        conn.rollback()
        raise
    finally:
        conn.close()

    return result


# ---------------------------------------------------------------------------
# Validation report
# ---------------------------------------------------------------------------

def run_validation():
    conn = get_db()
    cur = conn.cursor()
    cur.execute("""
        SELECT f.slug, COUNT(u.id) as total,
               SUM(CASE WHEN u.points_cost = 0 THEN 1 ELSE 0 END) as zero,
               SUM(CASE WHEN u.points_cost > 0 THEN 1 ELSE 0 END) as has_pts
        FROM factions f
        JOIN units u ON u.faction_id = f.id
        WHERE f.game_system_id = (SELECT id FROM game_systems WHERE code = 'aos4' LIMIT 1)
        GROUP BY f.id, f.slug
        ORDER BY f.slug
    """)
    rows = cur.fetchall()
    conn.close()

    print("\n" + "=" * 68)
    print("AOS4 UNIT POINTS COVERAGE")
    print("=" * 68)
    print(f"{'Faction Slug':<35} {'Total':>6} {'HasPts':>7} {'Zero':>6} {'Cov%':>6}")
    print("-" * 68)
    total_all = total_has = total_zero = 0
    for row in rows:
        slug, total, zero, has_pts = row
        pct = (has_pts / total * 100) if total else 0
        flag = " *" if zero > 0 else ""
        print(f"{slug:<35} {total:>6} {has_pts:>7} {zero:>6} {pct:>5.0f}%{flag}")
        total_all += total; total_has += has_pts; total_zero += zero
    print("-" * 68)
    pct = (total_has / total_all * 100) if total_all else 0
    print(f"{'TOTAL':<35} {total_all:>6} {total_has:>7} {total_zero:>6} {pct:>5.0f}%")
    print("  * = still has units with pts=0")
    print()


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Backfill AoS4 unit points costs")
    grp = parser.add_mutually_exclusive_group()
    grp.add_argument("--faction", metavar="SLUG", help="Process single faction")
    grp.add_argument("--all",      action="store_true", help="Process all 22 PDF factions")
    grp.add_argument("--validate", action="store_true", help="Print coverage stats only")

    parser.add_argument("--dry-run",    action="store_true", help="No DB writes")
    parser.add_argument("--no-cache",   action="store_true", help="Re-download everything")
    parser.add_argument("--with-pdf",   action="store_true",
                        help="Also download PDFs and extract warscroll names for cross-reference "
                             "(slow — adds ~1.5s/page; disabled by default)")
    parser.add_argument("--debug",      action="store_true", help="Verbose logging")
    args = parser.parse_args()

    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)

    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    WAHA_CACHE_DIR.mkdir(parents=True, exist_ok=True)

    if args.validate:
        run_validation()
        return

    if not args.faction and not args.all:
        parser.print_help()
        return

    if args.all:
        # Include PDF factions + subfactions/no-PDF factions that have DB units
        factions = list(FACTION_PDF_URLS.keys()) + list(SUBFACTION_WAHA_SLUG.keys())
        # Deduplicate (preserve order)
        seen_slugs: set[str] = set()
        factions_deduped = []
        for f in factions:
            if f not in seen_slugs:
                seen_slugs.add(f)
                factions_deduped.append(f)
        factions = factions_deduped
    else:
        factions = [args.faction]

    log.info(f"Processing {len(factions)} faction(s). dry_run={args.dry_run}")
    log.info(f"No PDF available for: {', '.join(PDF_GAPS)}")

    summaries = []
    for slug in factions:
        if slug == "sons-of-behemat":
            log.warning("sons-of-behemat: PDF exists but NOT in DB — skipping DB update")
        s = process_faction(slug, dry_run=args.dry_run, no_cache=args.no_cache,
                            with_pdf=args.with_pdf)
        summaries.append(s)

    # ---- Summary table ----
    print("\n" + "=" * 80)
    print(f"CROSS-FACTION SUMMARY{' [DRY-RUN]' if args.dry_run else ''}")
    print("=" * 80)
    print(f"{'Faction':<35} {'DB':>4} {'AlreadySet':>11} {'Updated':>8} {'NoData':>7}")
    print("-" * 80)

    total_upd = total_already = total_nodata = 0
    for s in summaries:
        print(f"{s['faction']:<35} {s['db_total']:>4} {s['already_set']:>11} "
              f"{s['updated']:>8} {s['waha_not_found']:>7}")
        total_upd     += s["updated"]
        total_already += s["already_set"]
        total_nodata  += s["waha_not_found"]
    print("-" * 80)
    print(f"{'TOTAL':<35} {'':>4} {total_already:>11} {total_upd:>8} {total_nodata:>7}")

    # ---- Unmatched PDF names ----
    print("\nUNMATCHED PDF WARSCROLL NAMES (in PDF but no DB unit matches):")
    any_unmatched = False
    for s in summaries:
        if s["unmatched_pdf"]:
            any_unmatched = True
            print(f"  {s['faction']}:")
            for n in s["unmatched_pdf"][:15]:
                print(f"    - {n!r}")
    if not any_unmatched:
        print("  (none)")

    # ---- Units with no points data ----
    print("\nUNITS WITH NO WAHAPEDIA DATA (likely removed/renamed in AoS4):")
    any_missing = False
    for s in summaries:
        if s["not_found_list"]:
            any_missing = True
            print(f"  {s['faction']}:")
            for n in s["not_found_list"]:
                print(f"    - {n!r}")
    if not any_missing:
        print("  (none)")

    # ---- Final coverage ----
    if not args.dry_run:
        run_validation()


if __name__ == "__main__":
    main()
