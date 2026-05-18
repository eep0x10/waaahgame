"""
Scrape unit images from community wikis via MediaWiki JSON API.

Primary source: warhammerfantasy.fandom.com MediaWiki API
  - Bypasses Cloudflare (JSON API endpoint, not HTML pages)
  - Tries the canonical unit name first, then alias names
  - Uses pageimages thumbnail as first choice, imageinfo as fallback

Secondary source: falls back to search + imageinfo on miss
Final fallback: saves a Google Images search URL as image_search_url

Usage:
  python scripts/scrape_wiki_images.py --all [--force] [--source fandom|lexicanum|all]

Via Flask CLI:
  flask --app run.py scrape-images --all --force [--source all]

Polite:
  - User-Agent: waaahgame/0.2 (educational; contact: yhextt@gmail.com) + MediaWiki API
  - 0.5s sleep between API calls (JSON, not HTML - much lighter)
  - Skip units already having image_path on disk (unless --force)
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

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

WIKI_UA = (
    'waaahgame/0.2 (educational; contact: yhextt@gmail.com) '
    'python-requests/2.31 MediaWiki-API-fetch'
)

# Primary: WHFB Fandom MediaWiki API (bypasses CF, has AoS/WHFB units)
WHFB_API = 'https://warhammerfantasy.fandom.com/api.php'

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

MIN_IMG_W = 200
MIN_IMG_H = 200

# ---------------------------------------------------------------------------
# Name aliases: units that appear under a different name on the WHFB wiki
# Key = canonical AoS unit name, Value = list of wiki page titles to try
# ---------------------------------------------------------------------------
WIKI_ALIASES = {
    'Verminlord Corruptor': ['Verminlord', 'Corruptor'],
    'Verminlord Warbringer': ['Verminlord'],
    'Thanquol on Boneripper': ['Thanquol', 'Boneripper'],
    'Grey Seer': ['Grey Seers', 'Grey Seer (Skaven)'],
    'Warlock Bombardier': ['Clan Skryre', 'Warlock Engineer'],
    'Clawlord': ['Skaven Warlord', 'Warlord (Skaven)'],
    'Clanrats': ['Clanrat'],
    'Night Runners': ['Night Runner'],
    'Gutter Runners': ['Gutter Runner'],
    'Plague Monks': ['Plague Monk'],
    'Plague Censer Bearers': ['Plague Censer', 'Plague Censer Bearer'],
    'Hell Pit Abomination': ['Hell-Pit Abomination', 'Hellpit Abomination'],
    'Rat Ogors': ['Rat Ogre', 'Rat Ogor'],
    'Stormfiends': ['Stormfiend'],
    'Warplock Jezzails': ['Warplock Jezzail', 'Jezzails'],
    'Warp Lightning Cannon': ['Warp-Lightning Cannon', 'Warp Lightning Cannon (Skaven)'],
    'Slann Starmaster': ['Slann', 'Slann Mage-Priest'],
    'Saurus Astrolith Bearer': ['Saurus', 'Astrolith Bearer'],
    'Skink Starpriest': ['Skink Priest', 'Skink'],
    'Saurus Scar-Veteran on Carnosaur': ['Carnosaur', 'Saurus Scar-Veteran', 'Old Blood on Carnosaur'],
    'Saurus Warriors': ['Saurus Warrior', 'Saurus'],
    'Aggradon Lancers': ['Cold One Riders', 'Aggradon'],
    'Saurus Guard': ['Temple Guard', 'Saurus Temple Guard'],
    'Sunblood Pack': ['Sunblood', 'Saurus Sunblood'],
}


# ---------------------------------------------------------------------------
# MediaWiki API helpers
# ---------------------------------------------------------------------------

def _get_pageimages(api_base, slug, session):
    """
    Use MediaWiki pageimages prop to get the representative thumbnail URL.
    Returns image URL string or None.
    """
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
    """
    Get list of image titles on a page, then resolve to URLs via imageinfo.
    Returns (url, width, height) or None.
    """
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
                # Skip obvious non-unit images
                lc = title.lower()
                if any(kw in lc for kw in ['logo', 'icon', 'banner', 'screenshot', 'vermintide',
                                             'map', 'faction', 'symbol', 'flag', 'background']):
                    continue
                # Resolve to URL
                img_url = _resolve_imageinfo(api_base, title, session)
                if img_url:
                    return img_url
    except Exception as exc:
        log.debug('images list error for %s: %s', slug, exc)
    return None


def _resolve_imageinfo(api_base, img_title, session):
    """Resolve a File:... title to its actual CDN URL."""
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
    """opensearch for a query, return list of (title, url)."""
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
    """
    Try pageimages, then images-list for a given wiki slug.
    Returns image URL or None.
    """
    # 1. pageimages thumbnail (fastest)
    img_url = _get_pageimages(api_base, slug, session)
    if img_url:
        return img_url

    # 2. images list + imageinfo
    img_url = _get_images_list(api_base, slug, session)
    if img_url:
        return img_url

    return None


# ---------------------------------------------------------------------------
# Image download + resize
# ---------------------------------------------------------------------------

def _download_and_resize(img_url, dest_path, session):
    """
    Download, validate (min 200x200), resize to max 600px wide, save JPEG q85.
    Returns True on success.
    """
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
# Per-unit image lookup
# ---------------------------------------------------------------------------

def _find_image_for_unit(unit_name, session):
    """
    Try WHFB Fandom MediaWiki API for a unit.
    First tries canonical name, then WIKI_ALIASES entries, then opensearch.
    Returns (img_url, wiki_slug_used) or (None, None).
    """
    api = WHFB_API

    # Build list of slugs to try
    candidates = [unit_name.replace(' ', '_')]
    for alias in WIKI_ALIASES.get(unit_name, []):
        candidates.append(alias.replace(' ', '_'))

    for slug in candidates:
        img_url = _try_get_image(api, slug, session)
        time.sleep(0.3)
        if img_url:
            return img_url, slug

    # Final: opensearch
    results = _wiki_search(api, unit_name, session)
    for title, link in results[:2]:
        img_url = _try_get_image(api, title.replace(' ', '_'), session)
        time.sleep(0.3)
        if img_url:
            return img_url, title

    return None, None


# ---------------------------------------------------------------------------
# Main scrape logic
# ---------------------------------------------------------------------------

def scrape(faction=None, force=False, source='all'):
    """
    Entry point. Works inside existing Flask app context (CLI) or standalone.
    Returns (scraped, skipped, failed).
    """
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, faction=faction, force=force, source=source)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, faction=faction, force=force, source=source)


def _do_scrape(db, Faction, Unit, faction=None, force=False, source='all'):
    import requests as req

    query = Unit.query.join(Faction)
    if faction:
        query = query.filter(Faction.slug == faction)
    units = query.all()

    if not units:
        log.warning('No units found for faction=%s', faction)
        return 0, 0, 0

    log.info('Wiki image scrape: %d units (faction=%s, force=%s, source=%s)',
             len(units), faction or 'all', force, source)

    session = req.Session()
    session.headers.update({'User-Agent': WIKI_UA})

    scraped = 0
    skipped = 0
    failed = 0
    source_counts = {}

    for unit in units:
        faction_slug = unit.faction.slug
        dest_rel = 'units/{}/{}.jpg'.format(faction_slug, unit.slug)
        dest_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, '{}.jpg'.format(unit.slug))

        # Skip if image already on disk
        if os.path.exists(dest_abs) and not force:
            log.info('[SKIP] %s -- image file already exists', unit.slug)
            if not unit.image_path:
                unit.image_path = dest_rel
                db.session.commit()
            skipped += 1
            continue

        found_url = None
        used_slug = None

        if source in ('fandom', 'all'):
            found_url, used_slug = _find_image_for_unit(unit.name, session)

        if found_url:
            ok = _download_and_resize(found_url, dest_abs, session=session)
            time.sleep(0.5)
            if ok:
                unit.image_path = dest_rel
                unit.image_source_url = found_url
                db.session.commit()
                try:
                    from PIL import Image
                    im = Image.open(dest_abs)
                    dims = '{}x{}'.format(im.width, im.height)
                except Exception:
                    dims = '?x?'
                log.info('[OK] %s -> fandom:%s (%s)', unit.slug, used_slug, dims)
                scraped += 1
                source_counts['fandom'] = source_counts.get('fandom', 0) + 1
                continue

        # Save Google Images search URL as fallback
        if not unit.image_search_url:
            query_str = 'warhammer+age+of+sigmar+{}'.format(
                unit.name.replace(' ', '+')
            )
            search_url = 'https://www.google.com/search?tbm=isch&q={}'.format(query_str)
            unit.image_search_url = search_url
            db.session.commit()
        log.info('[FAIL] %s -- no image found', unit.slug)
        failed += 1

    log.info('Wiki scrape done. Scraped=%d  Skipped=%d  Failed=%d', scraped, skipped, failed)
    if source_counts:
        log.info('  Sources: %s', source_counts)

    return scraped, skipped, failed


# ---------------------------------------------------------------------------
# Expose selector list for backward-compat smoke test
# ---------------------------------------------------------------------------
WARSCROLL_IMG_SELECTORS = [
    'pageimages_thumbnail',
    'images_imageinfo',
    'opensearch_fallback',
]


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape unit images from AoS/WHFB Fandom via MediaWiki API'
    )
    parser.add_argument('--faction', default=None)
    parser.add_argument('--all', action='store_true', dest='all_factions')
    parser.add_argument('--force', action='store_true')
    parser.add_argument('--source', default='all', choices=['fandom', 'lexicanum', 'all'])
    args = parser.parse_args()

    if not args.faction and not args.all_factions:
        parser.print_help()
        sys.exit(1)

    scrape(faction=args.faction, force=args.force, source=args.source)
