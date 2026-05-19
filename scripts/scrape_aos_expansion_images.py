"""
Scrape unit images for AoS expansion factions: Stormcast Eternals, Sylvaneth, Nighthaunt.

Tries Age of Sigmar Fandom wiki first (ageofsigmar.fandom.com), then WHFB Fandom wiki.
Generates SVG placeholders for any unit that fails.

Usage:
  python scripts/scrape_aos_expansion_images.py [--force]
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

AOS_API = 'https://ageofsigmar.fandom.com/api.php'
WHFB_API = 'https://warhammerfantasy.fandom.com/api.php'

WIKI_UA = (
    'waaahgame/0.2 (educational; contact: yhextt@gmail.com) '
    'python-requests/2.31 MediaWiki-API-fetch'
)

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

MIN_IMG_W = 200
MIN_IMG_H = 200

TARGET_FACTIONS = ['stormcast-eternals', 'sylvaneth', 'nighthaunt']

WIKI_ALIASES = {
    'Lord-Imperatant': ['Lord Imperatant', 'Stormcast Eternals'],
    'Knight-Vexillor with Banner of Apotheosis': ['Knight-Vexillor', 'Vexillor'],
    'Lord-Castellant': ['Lord Castellant', 'Castellant'],
    'Lord-Relictor': ['Lord Relictor', 'Relictor'],
    'Yndrasta, the Celestial Spear': ['Yndrasta'],
    'Liberators': ['Liberator'],
    'Vindictors': ['Vindictor'],
    'Annihilators': ['Annihilator'],
    'Praetors': ['Praetor'],
    'Vanguard-Raptors with Longstrike Crossbows': ['Vanguard-Raptors', 'Vanguard Raptors'],
    'Stormdrake Guard': ['Stormdrake'],
    'Celestar Ballista': ['Celestar_Ballista', 'Ballista'],
    'Drycha Hamadreth': ['Drycha'],
    'Treelord Ancient': ['Tree Lord Ancient', 'Treelord'],
    'Branchwych': [],
    'Arch-Revenant': ['Arch Revenant'],
    'Spirit of Durthu': ['Durthu'],
    'Dryads': ['Dryad'],
    'Tree-Revenants': ['Tree Revenants', 'Revenants'],
    'Spite-Revenants': ['Spite Revenants'],
    'Kurnoth Hunters with Greatswords': ['Kurnoth Hunters', 'Kurnoth Hunter'],
    'Kurnoth Hunters with Greatbows': ['Kurnoth Hunters', 'Kurnoth Hunter'],
    'Treelord': ['Tree Lord'],
    'Revenant Seekers': ['Revenant Seeker'],
    'Krulghast Cruciator': ['Krulghast'],
    'Spirit Torment': [],
    'Guardian of Souls': [],
    'Lord Executioner': [],
    'Knight of Shrouds': [],
    'Chainrasps': ['Chainrasp'],
    'Bladegheist Revenants': ['Bladegheist'],
    'Grimghast Reapers': ['Grimghast', 'Grimghast Reaper'],
    'Hexwraiths': ['Hexwraith'],
    'Spirit Hosts': ['Spirit Host'],
    'Glaivewraith Stalkers': ['Glaivewraith', 'Glaivewraith Stalker'],
    'Mourngul': [],
}


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
                if any(kw in lc for kw in ['logo', 'icon', 'banner', 'screenshot',
                                             'map', 'faction', 'symbol', 'flag', 'background']):
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


def _try_get_image(api_base, slug, session):
    img_url = _get_pageimages(api_base, slug, session)
    if img_url:
        return img_url
    img_url = _get_images_list(api_base, slug, session)
    if img_url:
        return img_url
    return None


def _find_image_for_unit(unit_name, session):
    candidates = [unit_name.replace(' ', '_')]
    for alias in WIKI_ALIASES.get(unit_name, []):
        candidates.append(alias.replace(' ', '_'))

    for api in (AOS_API, WHFB_API):
        for slug in candidates:
            img_url = _try_get_image(api, slug, session)
            time.sleep(0.3)
            if img_url:
                return img_url, slug
        time.sleep(0.2)

    return None, None


def _download_and_resize(img_url, dest_path, session):
    try:
        from PIL import Image
        resp = session.get(img_url, timeout=25, stream=True)
        if resp.status_code != 200:
            return False
        img = Image.open(io.BytesIO(resp.content)).convert('RGB')
        if img.width < MIN_IMG_W or img.height < MIN_IMG_H:
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


def _make_svg_placeholder(dest_path, unit_name, faction_name):
    color_map = {
        'stormcast-eternals': ('#C8A951', '#1a2a4a'),
        'sylvaneth': ('#4a7c3f', '#c8e6c0'),
        'nighthaunt': ('#4db6ac', '#0d2626'),
    }
    slug_dir = os.path.basename(os.path.dirname(dest_path))
    bg, fg = color_map.get(slug_dir, ('#444444', '#cccccc'))
    short = unit_name[:20] + ('...' if len(unit_name) > 20 else '')
    svg = f'''<svg xmlns="http://www.w3.org/2000/svg" width="300" height="300" viewBox="0 0 300 300">
  <rect width="300" height="300" fill="{bg}"/>
  <text x="150" y="130" font-family="serif" font-size="14" fill="{fg}" text-anchor="middle">{faction_name}</text>
  <text x="150" y="160" font-family="serif" font-size="12" fill="{fg}" text-anchor="middle">{short}</text>
  <text x="150" y="190" font-family="serif" font-size="10" fill="{fg}" text-anchor="middle">No image available</text>
</svg>'''
    svg_path = dest_path.replace('.jpg', '.svg')
    os.makedirs(os.path.dirname(svg_path), exist_ok=True)
    with open(svg_path, 'w', encoding='utf-8') as fh:
        fh.write(svg)
    return svg_path


def run_scrape(force=False):
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, force=force)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_scrape(db, Faction, Unit, force=force)


def _do_scrape(db, Faction, Unit, force=False):
    import requests as req

    units = (
        Unit.query.join(Faction)
        .filter(Faction.slug.in_(TARGET_FACTIONS))
        .all()
    )

    if not units:
        log.warning('No units found for expansion factions')
        return 0, 0, 0

    log.info('Scraping images for %d expansion units', len(units))

    session = req.Session()
    session.headers.update({'User-Agent': WIKI_UA})

    scraped = 0
    skipped = 0
    placeholder = 0

    for unit in units:
        faction_slug = unit.faction.slug
        dest_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit.slug}.jpg')
        dest_rel = f'units/{faction_slug}/{unit.slug}.jpg'

        if os.path.exists(dest_abs) and not force:
            log.info('[SKIP] %s -- file exists', unit.slug)
            if not unit.image_path or not unit.image_path.endswith('.jpg'):
                unit.image_path = dest_rel
                db.session.commit()
            skipped += 1
            continue

        found_url, used_slug = _find_image_for_unit(unit.name, session)

        if found_url:
            ok = _download_and_resize(found_url, dest_abs, session=session)
            time.sleep(0.5)
            if ok:
                unit.image_path = dest_rel
                unit.image_source_url = found_url
                db.session.commit()
                log.info('[OK] %s -> %s', unit.slug, used_slug)
                scraped += 1
                continue

        svg_path = _make_svg_placeholder(dest_abs, unit.name, unit.faction.name)
        svg_rel = f'units/{faction_slug}/{unit.slug}.svg'
        unit.image_path = svg_rel
        if not unit.image_search_url:
            q = unit.name.replace(' ', '+')
            unit.image_search_url = f'https://www.google.com/search?tbm=isch&q=warhammer+age+of+sigmar+{q}'
        db.session.commit()
        log.info('[PLACEHOLDER] %s -> %s', unit.slug, svg_path)
        placeholder += 1

    log.info('Done. Scraped=%d  Skipped=%d  Placeholder=%d', scraped, skipped, placeholder)
    return scraped, skipped, placeholder


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    run_scrape(force=args.force)
