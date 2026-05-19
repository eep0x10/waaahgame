"""
Scrape unit images for Warhammer 40,000 factions from warhammer40k.fandom.com.

Falls back to styled SVG placeholder if scrape fails.

Usage:
  python scripts/scrape_40k_images.py [--faction space-marines|tyranids] [--force]
"""

import sys
import os
import re
import time
import logging
import argparse
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

WIKI_UA = (
    'waaahgame/0.2 (educational; contact: yhextt@gmail.com) '
    'python-requests/2.31 MediaWiki-API-fetch'
)

WH40K_API = 'https://warhammer40k.fandom.com/api.php'

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

MIN_IMG_W = 200
MIN_IMG_H = 200

# Aliases: unit name -> list of wiki page titles to try
WIKI_ALIASES = {
    'Captain in Power Armour': ['Space Marine Captain', 'Captain (Space Marines)'],
    'Lieutenant': ['Space Marine Lieutenant', 'Lieutenant (Space Marines)'],
    'Apothecary': ['Space Marine Apothecary', 'Apothecary (Space Marines)'],
    'Tactical Squad': ['Tactical Space Marines', 'Tactical Marine'],
    'Intercessor Squad': ['Intercessor', 'Intercessors'],
    'Assault Intercessors': ['Assault Intercessor'],
    'Hellblasters': ['Hellblaster', 'Hellblaster Squad'],
    'Eradicators': ['Eradicator', 'Eradicator Squad'],
    'Outrider Squad': ['Outrider (Space Marines)', 'Space Marine Outriders'],
    'Terminator Squad': ['Terminator (Space Marines)', 'Space Marine Terminators'],
    'Redemptor Dreadnought': ['Redemptor Dreadnought'],
    'Repulsor': ['Repulsor (vehicle)', 'Repulsor Executioner'],
    'Hive Tyrant': ['Hive Tyrant'],
    'Neurotyrant': ['Neurotyrant', 'Norn Emissary'],
    'Broodlord': ['Broodlord (Tyranids)'],
    'Termagants': ['Termagant', 'Termagants'],
    'Hormagaunts': ['Hormagaunt'],
    'Tyranid Warriors with Melee': ['Tyranid Warrior'],
    'Genestealers': ['Genestealer'],
    'Zoanthropes': ['Zoanthrope'],
    'Carnifex': ['Carnifex (Tyranids)'],
    'Trygon': ['Trygon (Tyranids)'],
    'Lictor': ['Lictor (Tyranids)'],
    'Tyrannofex': ['Tyrannofex'],
}

# Faction colour map for SVG placeholders
FACTION_COLOURS = {
    'space-marines': ('#1a3a6b', '#c8a94a', '#ffffff'),  # blue, gold, white
    'tyranids':      ('#4a0a6b', '#c84a4a', '#ffffff'),  # purple, red, white
}


# ---------------------------------------------------------------------------
# MediaWiki API helpers (mirrored from scrape_wiki_images.py)
# ---------------------------------------------------------------------------

def _get_pageimages(api_base, slug, session):
    import requests as req
    url = (
        f'{api_base}?action=query'
        f'&titles={req.utils.quote(slug)}'
        f'&prop=pageimages'
        f'&piprop=thumbnail|name'
        f'&pithumbsize=700'
        f'&format=json'
    )
    try:
        resp = session.get(url, timeout=15)
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            if page.get('missing') == '':
                return None
            thumb = page.get('thumbnail', {})
            if thumb.get('source'):
                return thumb['source']
    except Exception as exc:
        log.debug('pageimages error for %s: %s', slug, exc)
    return None


def _get_images_list(api_base, slug, session):
    import requests as req
    url = (
        f'{api_base}?action=query'
        f'&titles={req.utils.quote(slug)}'
        f'&prop=images'
        f'&imlimit=15'
        f'&format=json'
    )
    try:
        resp = session.get(url, timeout=15)
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            if page.get('missing') == '':
                return None
            for img_entry in page.get('images', []):
                title = img_entry['title']
                if not any(title.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                    continue
                lc = title.lower()
                if any(kw in lc for kw in ['logo', 'icon', 'banner', 'screenshot', 'map',
                                             'faction', 'symbol', 'flag', 'background']):
                    continue
                img_url = _resolve_imageinfo(api_base, title, session)
                if img_url:
                    return img_url
    except Exception as exc:
        log.debug('images list error for %s: %s', slug, exc)
    return None


def _resolve_imageinfo(api_base, img_title, session):
    import requests as req
    url = (
        f'{api_base}?action=query'
        f'&titles={req.utils.quote(img_title)}'
        f'&prop=imageinfo'
        f'&iiprop=url|size'
        f'&format=json'
    )
    try:
        resp = session.get(url, timeout=15)
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            for info in page.get('imageinfo', []):
                w, h = info.get('width', 0), info.get('height', 0)
                if w >= MIN_IMG_W and h >= MIN_IMG_H:
                    return info.get('url')
    except Exception as exc:
        log.debug('imageinfo error for %s: %s', img_title, exc)
    return None


def _wiki_search(api_base, query, session, limit=3):
    import requests as req
    url = (
        f'{api_base}?action=opensearch'
        f'&search={req.utils.quote(query)}'
        f'&limit={limit}'
        f'&format=json'
    )
    try:
        resp = session.get(url, timeout=15)
        data = resp.json()
        if len(data) >= 4:
            return list(zip(data[1], data[3]))
    except Exception:
        pass
    return []


def _try_get_image(api_base, slug, session):
    img_url = _get_pageimages(api_base, slug, session)
    if img_url:
        return img_url
    img_url = _get_images_list(api_base, slug, session)
    return img_url


def _find_image_for_unit(unit_name, session):
    api = WH40K_API
    candidates = [unit_name.replace(' ', '_')]
    for alias in WIKI_ALIASES.get(unit_name, []):
        candidates.append(alias.replace(' ', '_'))

    for slug in candidates:
        img_url = _try_get_image(api, slug, session)
        time.sleep(0.4)
        if img_url:
            return img_url, slug

    results = _wiki_search(api, unit_name, session)
    for title, link in results[:2]:
        img_url = _try_get_image(api, title.replace(' ', '_'), session)
        time.sleep(0.4)
        if img_url:
            return img_url, title

    return None, None


def _download_and_resize(img_url, dest_path, session):
    try:
        from PIL import Image

        resp = session.get(img_url, timeout=25, stream=True)
        if resp.status_code != 200:
            log.debug('Image HTTP %s for %s', resp.status_code, img_url)
            return False

        img = Image.open(io.BytesIO(resp.content)).convert('RGB')
        if img.width < MIN_IMG_W or img.height < MIN_IMG_H:
            log.debug('Too small (%dx%d): %s', img.width, img.height, img_url)
            return False

        max_w = 600
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, 'JPEG', quality=85, optimize=True)
        return True

    except Exception as exc:
        log.debug('Download/resize error %s: %s', img_url, exc)
        return False


# ---------------------------------------------------------------------------
# SVG placeholder generator
# ---------------------------------------------------------------------------

def _make_svg_placeholder(unit_name, faction_slug, dest_path):
    """Generate a styled SVG placeholder when image scrape fails."""
    colours = FACTION_COLOURS.get(faction_slug, ('#2a2a2a', '#888888', '#ffffff'))
    bg, accent, text_col = colours

    # Abbreviate long names
    words = unit_name.split()
    if len(words) <= 2:
        line1 = unit_name
        line2 = ''
    else:
        half = len(words) // 2
        line1 = ' '.join(words[:half])
        line2 = ' '.join(words[half:])

    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 300 300" width="300" height="300">
  <rect width="300" height="300" fill="{bg}"/>
  <rect x="10" y="10" width="280" height="280" fill="none" stroke="{accent}" stroke-width="3"/>
  <rect x="20" y="20" width="260" height="260" fill="none" stroke="{accent}" stroke-width="1" stroke-dasharray="8,4"/>
  <!-- Faction symbol: stylised skull/aquila placeholder -->
  <circle cx="150" cy="120" r="40" fill="none" stroke="{accent}" stroke-width="2"/>
  <text x="150" y="130" font-family="serif" font-size="40" text-anchor="middle" fill="{accent}">&#9763;</text>
  <!-- Unit name -->
  <text x="150" y="190" font-family="serif" font-size="16" font-weight="bold"
        text-anchor="middle" fill="{text_col}">{line1}</text>
  {"" if not line2 else f'<text x="150" y="210" font-family="serif" font-size="16" font-weight="bold" text-anchor="middle" fill="{text_col}">{line2}</text>'}
  <text x="150" y="240" font-family="serif" font-size="11" text-anchor="middle" fill="{accent}">WH40K</text>
</svg>"""

    os.makedirs(os.path.dirname(dest_path), exist_ok=True)
    with open(dest_path, 'w', encoding='utf-8') as fh:
        fh.write(svg)
    log.info('[SVG] Placeholder created: %s', dest_path)
    return True


# ---------------------------------------------------------------------------
# Main scrape logic
# ---------------------------------------------------------------------------

def scrape(faction=None, force=False):
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, faction=faction, force=force)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, faction=faction, force=force)


def _do_scrape(db, Faction, Unit, faction=None, force=False):
    import requests as req

    # Only 40k factions
    query = Unit.query.join(Faction).filter(
        Faction.slug.in_(['space-marines', 'tyranids'])
    )
    if faction:
        query = query.filter(Faction.slug == faction)
    units = query.all()

    if not units:
        log.warning('No 40k units found (faction=%s)', faction)
        return 0, 0, 0

    log.info('40k image scrape: %d units (faction=%s, force=%s)', len(units), faction or 'all', force)

    session = req.Session()
    session.headers.update({'User-Agent': WIKI_UA})

    scraped = 0
    skipped = 0
    failed_svg = 0

    for unit in units:
        faction_slug = unit.faction.slug
        jpg_rel = 'units/{}/{}.jpg'.format(faction_slug, unit.slug)
        svg_rel = 'units/{}/{}.svg'.format(faction_slug, unit.slug)
        jpg_abs = os.path.join(STATIC_DIR, 'img', jpg_rel)
        svg_abs = os.path.join(STATIC_DIR, 'img', svg_rel)

        # Skip if already have image on disk
        if not force:
            if os.path.exists(jpg_abs):
                log.info('[SKIP] %s -- jpg exists', unit.slug)
                if not unit.image_path:
                    unit.image_path = jpg_rel
                skipped += 1
                continue
            if os.path.exists(svg_abs):
                log.info('[SKIP] %s -- svg exists', unit.slug)
                if not unit.image_path:
                    unit.image_path = svg_rel
                skipped += 1
                continue

        # Try wiki scrape
        log.info('Scraping image for %s...', unit.name)
        img_url, slug_used = _find_image_for_unit(unit.name, session)

        if img_url:
            ok = _download_and_resize(img_url, jpg_abs, session)
            if ok:
                unit.image_path = jpg_rel
                unit.image_source_url = img_url
                log.info('[OK] %s -> %s (wiki: %s)', unit.name, jpg_rel, slug_used)
                scraped += 1
                db.session.commit()
                continue
            else:
                log.warning('[IMG FAIL] %s -- download/resize failed, using SVG', unit.name)
        else:
            log.warning('[NOT FOUND] %s -- no wiki image found, using SVG', unit.name)

        # Fallback: SVG placeholder
        _make_svg_placeholder(unit.name, faction_slug, svg_abs)
        unit.image_path = svg_rel
        failed_svg += 1
        db.session.commit()

    db.session.commit()
    log.info('Done. Scraped: %d, Skipped: %d, SVG placeholders: %d', scraped, skipped, failed_svg)
    return scraped, skipped, failed_svg


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--faction', default=None, help='space-marines or tyranids')
    parser.add_argument('--force', action='store_true', help='Re-scrape even if image exists')
    args = parser.parse_args()
    scrape(faction=args.faction, force=args.force)
