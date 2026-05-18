"""
Seed AoS 4ed data: GameSystem, Skaven, Seraphon factions + units.

Idempotent — upserts by slug. Units with successful Wahapedia parses get full
stats/abilities/keywords/companions. Units that fail get minimal stub data.

Warscroll pages are fetched once and cached to scripts/cache/<slug>.json.
"""

import sys
import os
import json
import time
import re
import logging

# Allow running directly (python scripts/seed_aos.py) or via Flask CLI
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

CACHE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cache')
os.makedirs(CACHE_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'waaahgame/0.2 (educational)',
    'Accept-Language': 'en-US,en;q=0.9',
}

WAHAPEDIA_BASE = 'https://wahapedia.ru/aos4/factions'


# ---------------------------------------------------------------------------
# Wahapedia parsing helpers
# ---------------------------------------------------------------------------

def _fetch_raw(url):
    """Fetch URL with retries. Returns HTML text or None."""
    try:
        import requests
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.text
        log.warning('HTTP %s for %s', resp.status_code, url)
    except Exception as exc:
        log.warning('Fetch error for %s: %s', url, exc)
    return None


def _cache_path(slug):
    return os.path.join(CACHE_DIR, f'{slug}.json')


def _load_cache(slug):
    p = _cache_path(slug)
    if os.path.exists(p):
        with open(p, 'r', encoding='utf-8') as fh:
            return json.load(fh)
    return None


def _save_cache(slug, data):
    p = _cache_path(slug)
    with open(p, 'w', encoding='utf-8') as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)


def _parse_int(text, fallback=0):
    if text is None:
        return fallback
    m = re.search(r'\d+', str(text))
    return int(m.group()) if m else fallback


def parse_warscroll(html, slug):
    """Parse a Wahapedia warscroll page into a dict with stats/weapons/abilities/keywords/companions."""
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error('beautifulsoup4 not installed')
        return {}

    soup = BeautifulSoup(html, 'html.parser')
    result = {
        'stats': {},
        'weapons': [],
        'abilities': [],
        'keywords': [],
        'companions': [],
        'wahapedia_url': '',
    }

    # --- Stats table ---
    # Wahapedia stats row: Move, Save, Control, Health (sometimes Wounds/Bravery for old format)
    # The main stats block usually sits in a table with class containing 'profile-table' or 'stats'
    # Look for table rows with stat labels
    stats_candidates = soup.find_all('div', class_=lambda c: c and ('stat' in c.lower() or 'profile' in c.lower()))
    stat_labels = ['move', 'save', 'control', 'health', 'wounds', 'bravery']
    stats = {}

    # Try structured stat tables first
    for tbl in soup.find_all('table'):
        headers = [th.get_text(strip=True).lower() for th in tbl.find_all('th')]
        if any(s in ' '.join(headers) for s in ['move', 'save', 'health', 'wounds']):
            rows = tbl.find_all('tr')
            if len(rows) >= 2:
                vals = [td.get_text(strip=True) for td in rows[-1].find_all('td')]
                for i, h in enumerate(headers):
                    if i < len(vals):
                        stats[h] = vals[i]
            break

    # Fallback: look for labelled divs/spans
    if not stats:
        for el in soup.find_all(['span', 'div', 'td']):
            txt = el.get_text(strip=True).lower()
            for lbl in stat_labels:
                if txt == lbl:
                    nxt = el.find_next_sibling()
                    if nxt:
                        stats[lbl] = nxt.get_text(strip=True)

    # Try the characteristic blocks Wahapedia uses (e.g. class="Wsc_Value")
    # Wahapedia AoS4 layout: divs with class "Wsc_statblock" containing labelled spans
    for block in soup.find_all(class_=re.compile(r'[Ww]sc_', re.I)):
        label_el = block.find(class_=re.compile(r'label|stat_name|title', re.I))
        value_el = block.find(class_=re.compile(r'value|stat_val', re.I))
        if label_el and value_el:
            lbl = label_el.get_text(strip=True).lower()
            val = value_el.get_text(strip=True)
            for s in stat_labels:
                if s in lbl:
                    stats[s] = val

    result['stats'] = stats

    # --- Weapons ---
    # Wahapedia renders weapon profiles in tables. Each weapon row has: Name, Range, Attacks, Hit, Wound, Rend, Damage
    weapons = []
    for tbl in soup.find_all('table'):
        headers_raw = [th.get_text(strip=True) for th in tbl.find_all('th')]
        headers_lower = [h.lower() for h in headers_raw]
        weapon_headers = ['attack', 'hit', 'wound', 'rend', 'damage']
        if sum(1 for wh in weapon_headers if any(wh in h for h in headers_lower)) >= 3:
            for row in tbl.find_all('tr')[1:]:
                cells = [td.get_text(strip=True) for td in row.find_all(['td', 'th'])]
                if len(cells) >= 4:
                    weapon = {}
                    for i, h in enumerate(headers_raw):
                        if i < len(cells):
                            weapon[h] = cells[i]
                    if weapon:
                        weapons.append(weapon)
    result['weapons'] = weapons

    # --- Abilities ---
    # Abilities appear as named blocks. Various Wahapedia class names: 'ability', 'Wsc_Ability', etc.
    abilities = []
    seen_abilities = set()
    ability_selectors = [
        {'class': re.compile(r'ability|Ability', re.I)},
        {'class': re.compile(r'special_rule|Special', re.I)},
    ]
    for selector in ability_selectors:
        for el in soup.find_all(['div', 'section', 'p'], attrs=selector):
            name_el = el.find(class_=re.compile(r'name|title|header', re.I)) or el.find(['h3', 'h4', 'strong', 'b'])
            body_el = el.find(class_=re.compile(r'description|text|body|rule', re.I)) or el.find('p')
            name = name_el.get_text(strip=True) if name_el else ''
            body = body_el.get_text(strip=True) if body_el else el.get_text(strip=True)
            if name and name not in seen_abilities and len(name) < 100:
                seen_abilities.add(name)
                abilities.append({'name': name, 'description': body})
    result['abilities'] = abilities

    # --- Keywords ---
    keywords = []
    for el in soup.find_all(class_=re.compile(r'keyword|faction_keyword', re.I)):
        kw = el.get_text(strip=True).upper()
        if kw and len(kw) < 64 and kw not in keywords:
            keywords.append(kw)
    # Also try text segments that look like keyword lists (all caps comma separated)
    for el in soup.find_all(['p', 'div']):
        txt = el.get_text(strip=True)
        if re.match(r'^[A-Z][A-Z\s,\-]+$', txt) and ',' in txt and len(txt) < 300:
            parts = [k.strip() for k in txt.split(',')]
            for kw in parts:
                kw = kw.upper()
                if kw and kw not in keywords and len(kw) < 64:
                    keywords.append(kw)
    result['keywords'] = keywords

    # --- Companions ---
    # Hero companion units appear in a "Companion Units" section or similar
    companions = []
    for el in soup.find_all(['p', 'div', 'section', 'li']):
        txt = el.get_text(strip=True)
        if 'companion' in txt.lower() or 'regiment' in txt.lower():
            # Try to find listed units in the vicinity
            sibling = el.find_next_sibling()
            if sibling:
                items = sibling.find_all('li') or [sibling]
                for item in items:
                    companion = item.get_text(strip=True)
                    if companion and len(companion) < 96 and companion not in companions:
                        companions.append(companion)
    result['companions'] = companions

    return result


def fetch_warscroll(faction_slug, unit_wahapedia_slug, unit_slug):
    """
    Fetch and parse a Wahapedia warscroll. Returns parsed dict.
    Uses file cache to avoid re-fetching.
    """
    cached = _load_cache(unit_slug)
    if cached is not None:
        log.info('[cache hit] %s', unit_slug)
        return cached

    url = f'{WAHAPEDIA_BASE}/{faction_slug}/{unit_wahapedia_slug}'
    log.info('Fetching %s', url)
    time.sleep(0.5)
    html = _fetch_raw(url)
    if html is None:
        log.warning('No HTML for %s — stub data only', unit_slug)
        _save_cache(unit_slug, {})
        return {}

    parsed = parse_warscroll(html, unit_slug)
    parsed['wahapedia_url'] = url
    _save_cache(unit_slug, parsed)
    return parsed


# ---------------------------------------------------------------------------
# Seed data definitions
# ---------------------------------------------------------------------------

SKAVEN_UNITS = [
    # (name, pts, role, can_be_general, can_be_reinforced, wahapedia_slug, model_count)
    ('Verminlord Corruptor',         280, 'Hero',    True,  False, 'Verminlord-Corruptor',      1),
    ('Verminlord Warbringer',        280, 'Hero',    True,  False, 'Verminlord-Warbringer',     1),
    ('Thanquol on Boneripper',       330, 'Hero',    True,  False, 'Thanquol-on-Boneripper',    1),
    ('Grey Seer',                    110, 'Hero',    True,  False, 'Grey-Seer',                 1),
    ('Warlock Bombardier',            90, 'Hero',    True,  False, 'Warlock-Bombardier',        1),
    ('Master Moulder',                80, 'Hero',    True,  False, 'Master-Moulder',            1),
    ('Deathmaster',                  100, 'Hero',    True,  False, 'Deathmaster',               1),
    ('Clawlord',                      95, 'Hero',    True,  False, 'Clawlord',                  1),
    ('Plague Priest',                 80, 'Hero',    True,  False, 'Plague-Priest',             1),
    ('Stormvermin',                  110, 'Battleline', False, True, 'Stormvermin',             10),
    ('Clanrats',                     110, 'Battleline', False, True, 'Clanrats',                20),
    ('Night Runners',                130, None,      False, True, 'Night-Runners',              10),
    ('Gutter Runners',                95, None,      False, True, 'Gutter-Runners',             5),
    ('Plague Monks',                 140, None,      False, True, 'Plague-Monks',               10),
    ('Plague Censer Bearers',         75, None,      False, True, 'Plague-Censer-Bearers',      5),
    ('Hell Pit Abomination',         200, 'Behemoth', False, False, 'Hell-Pit-Abomination',     1),
    ('Rat Ogors',                     90, None,      False, True, 'Rat-Ogors',                  3),
    ('Stormfiends',                  150, None,      False, True, 'Stormfiends',                3),
    ('Warplock Jezzails',             95, None,      False, True, 'Warplock-Jezzails',          3),
    ('Warp Lightning Cannon',        120, None,      False, False, 'Warp-Lightning-Cannon',     1),
]

SERAPHON_UNITS = [
    ('Slann Starmaster',             260, 'Hero',     True,  False, 'Slann-Starmaster',             1),
    ('Saurus Astrolith Bearer',      120, 'Hero',     True,  False, 'Saurus-Astrolith-Bearer',      1),
    ('Skink Starpriest',              90, 'Hero',     True,  False, 'Skink-Starpriest',             1),
    ('Saurus Scar-Veteran on Carnosaur', 200, 'Hero', True,  False, 'Saurus-Scar-Veteran-on-Carnosaur', 1),
    ('Stegadon',                     150, 'Behemoth', False, False, 'Stegadon',                     1),
    ('Engine of the Gods',           150, 'Hero',     True,  False, 'Engine-of-the-Gods',           1),
    ('Saurus Warriors',              140, 'Battleline', False, True, 'Saurus-Warriors',             10),
    ('Aggradon Lancers',             200, None,       False, True, 'Aggradon-Lancers',               3),
    ('Skinks',                        80, 'Battleline', False, True, 'Skinks',                      10),
    ('Saurus Guard',                 110, None,       False, True, 'Saurus-Guard',                   5),
    ('Sunblood Pack',                150, None,       False, True, 'Sunblood-Pack',                  5),
]

SKAVEN_BLURB = (
    "From the writhing dark beneath the Mortal Realms, the Skaven emerge in chittering hordes — "
    "a seething tide of ratmen bound together by treachery, ambition, and an insatiable hunger to devour "
    "all that the other races have built. Each of the great Clans brings its own fell gifts to the Skaventide: "
    "Verminus warriors armed with rusted blades, Pestilens priests spreading divine plague, Skryre engineers "
    "wielding warpstone-powered armaments, Eshin assassins slipping through shadows, and Moulder flesh-shapers "
    "unleashing abominations stitched from nightmare and sinew. "
    "Beneath the banner of the Great Horned Rat, all skaven are united in one sacred purpose: the Great Gnaw, "
    "the consuming of creation itself."
)

SERAPHON_BLURB = (
    "Ageless architects of celestial order, the Seraphon descend from the stars upon beams of blazing starlight "
    "to prosecute the Great Plan — a cosmic design to unmake Chaos and restore the symmetry of creation. "
    "Ancient Slann Starmasters contemplate the movements of celestial bodies from atop great temple-ships, "
    "directing their cold-blooded warriors across the Mortal Realms with godlike precision. "
    "From the armoured ranks of Saurus Warriors to the swift Skink scouts and the thunderous charge of "
    "Carnosaurs, the Seraphon wage war as a sacred rite — each battle another step in a plan conceived "
    "before time itself had a name."
)


def _slug(name):
    """Convert unit name to a URL-safe slug."""
    s = name.lower()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    s = s.strip('-')
    return s


def seed():
    """Main seed function. Works both from Flask CLI (existing app context) and standalone.

    When invoked from the Flask CLI, Flask already has an app context active.
    When run standalone (python scripts/seed_aos.py), we create our own.
    """
    from app.extensions import db
    from app.models.game import GameSystem, Faction, Unit

    try:
        from flask import current_app
        current_app._get_current_object()  # raises RuntimeError if no context active
        # Already inside an app context — just run
        return _do_seed(db, GameSystem, Faction, Unit)
    except RuntimeError:
        pass

    # No app context — create one
    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db as _db
        from app.models.game import GameSystem as GS, Faction as F, Unit as U
        return _do_seed(_db, GS, F, U)


def _do_seed(db, GameSystem, Faction, Unit):
    """Core seeding logic. Must be called inside an active Flask app context."""

    # --- GameSystem ---
    gs = GameSystem.query.filter_by(code='aos4').first()
    if not gs:
        gs = GameSystem(
            code='aos4',
            name='Age of Sigmar',
            edition='4th Edition (Skaventide 2024)',
            ruleset_label='GHB 2025-26 + April 2026 Battlescroll',
        )
        db.session.add(gs)
        db.session.flush()
        log.info('Created GameSystem aos4')
    else:
        log.info('GameSystem aos4 already exists')

    # --- Factions ---
    def upsert_faction(code, name, alliance, blurb):
        f = Faction.query.filter_by(slug=code).first()
        if not f:
            f = Faction(
                game_system_id=gs.id,
                code=code,
                slug=code,
                name=name,
                grand_alliance=alliance,
                blurb=blurb,
            )
            db.session.add(f)
            db.session.flush()
            log.info('Created Faction %s', code)
        else:
            f.blurb = blurb
            log.info('Faction %s already exists — updated blurb', code)
        return f

    skaven = upsert_faction('skaven', 'Skaven', 'Chaos', SKAVEN_BLURB)
    seraphon = upsert_faction('seraphon', 'Seraphon', 'Order', SERAPHON_BLURB)

    # --- Units ---
    def upsert_units(faction_obj, units_list, faction_wahapedia_slug):
        seeded_full = 0
        seeded_stub = 0
        for row in units_list:
            name, pts, role, hero, reinforceable, waha_slug, count = row
            unit_slug = _slug(name)

            # Fetch warscroll data (cached)
            warscroll = fetch_warscroll(faction_wahapedia_slug, waha_slug, unit_slug)
            has_data = bool(warscroll.get('stats') or warscroll.get('keywords') or warscroll.get('weapons'))

            u = Unit.query.filter_by(slug=unit_slug).first()
            # SVG placeholder paths for units with no scraped image
            _svg_placeholders = {
                'aggradon-lancers': 'units/seraphon/aggradon-lancers.svg',
                'sunblood-pack': 'units/seraphon/sunblood-pack.svg',
            }

            if not u:
                u = Unit(
                    faction_id=faction_obj.id,
                    slug=unit_slug,
                    name=name,
                    points_cost=pts,
                    unit_role=role,
                    can_be_general=hero,
                    can_be_reinforced=reinforceable,
                    model_count=count,
                    stats_json=warscroll.get('stats', {}),
                    weapons_json=warscroll.get('weapons', []),
                    abilities_json=warscroll.get('abilities', []),
                    keywords_json=warscroll.get('keywords', []),
                    companions_json=warscroll.get('companions', []),
                    wahapedia_url=warscroll.get('wahapedia_url', f'{WAHAPEDIA_BASE}/{faction_wahapedia_slug}/{waha_slug}'),
                    image_path=_svg_placeholders.get(unit_slug),
                )
                db.session.add(u)
                log.info('[+] %s (full=%s)', name, has_data)
            else:
                u.points_cost = pts
                u.unit_role = role
                u.model_count = count
                if has_data:
                    u.stats_json = warscroll.get('stats', u.stats_json)
                    u.weapons_json = warscroll.get('weapons', u.weapons_json)
                    u.abilities_json = warscroll.get('abilities', u.abilities_json)
                    u.keywords_json = warscroll.get('keywords', u.keywords_json)
                    u.companions_json = warscroll.get('companions', u.companions_json)
                if not u.wahapedia_url:
                    u.wahapedia_url = f'{WAHAPEDIA_BASE}/{faction_wahapedia_slug}/{waha_slug}'
                if not u.image_path and unit_slug in _svg_placeholders:
                    u.image_path = _svg_placeholders[unit_slug]
                log.info('[~] %s updated (full=%s)', name, has_data)

            if has_data:
                seeded_full += 1
            else:
                seeded_stub += 1

        db.session.commit()
        return seeded_full, seeded_stub

    log.info('=== Seeding Skaven (%d units) ===', len(SKAVEN_UNITS))
    sk_full, sk_stub = upsert_units(skaven, SKAVEN_UNITS, 'skaven')

    log.info('=== Seeding Seraphon (%d units) ===', len(SERAPHON_UNITS))
    sr_full, sr_stub = upsert_units(seraphon, SERAPHON_UNITS, 'seraphon')

    log.info('Done. Skaven: %d full / %d stub. Seraphon: %d full / %d stub.',
             sk_full, sk_stub, sr_full, sr_stub)

    return {
        'skaven_full': sk_full, 'skaven_stub': sk_stub,
        'seraphon_full': sr_full, 'seraphon_stub': sr_stub,
    }


if __name__ == '__main__':
    seed()
