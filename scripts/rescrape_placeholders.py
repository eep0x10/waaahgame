import sys
import os
import time
import logging
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
MIN_BYTES = 10 * 1024
MAX_BYTES = 5 * 1024 * 1024

TARGET_FACTIONS = ['stormcast-eternals', 'sylvaneth', 'nighthaunt']

EXTRA_ALIASES = {
    'annihilators': ['Annihilator (Stormcast Eternals)', 'Annihilators'],
    'knight-vexillor-with-banner-of-apotheosis': ['Knight-Vexillor', 'Vexillor (Stormcast Eternals)'],
    'lord-castellant': ['Lord-Castellant', 'Lord Castellant'],
    'lord-relictor': ['Lord-Relictor', 'Lord Relictor'],
    'praetors': ['Praetor (Stormcast Eternals)', 'Praetor'],
    'stormdrake-guard': ['Stormdrake Guard', 'Stormdrake'],
    'vanguard-raptors-with-longstrike-crossbows': ['Vanguard-Raptors with Longstrike Crossbows',
                                                    'Vanguard-Raptors', 'Vanguard Raptors'],
    'vindictors': ['Vindictor', 'Vindictors'],
    'yndrasta-the-celestial-spear': ['Yndrasta the Celestial Spear', 'Yndrasta'],
    'arch-revenant': ['Arch-Revenant', 'Arch Revenant (Sylvaneth)'],
    'revenant-seekers': ['Revenant Seeker', 'Revenant Seekers'],
    'treelord-ancient': ['Treelord Ancient', 'Tree Lord Ancient'],
    'treelord': ['Treelord', 'Tree Lord (Sylvaneth)'],
    'chainrasps': ['Chainrasp Horde', 'Chainrasp'],
    'krulghast-cruciator': ['Krulghast Cruciator', 'Krulghast'],
    'spirit-hosts': ['Spirit Host', 'Spirit Hosts (Nighthaunt)'],
    'spirit-torment': ['Spirit Torment'],
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
        log.debug('pageimages error %s: %s', slug, exc)
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
        log.debug('images list error %s: %s', slug, exc)
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
        log.debug('imageinfo error %s: %s', img_title, exc)
    return None


def _try_get_image(api_base, slug, session):
    img_url = _get_pageimages(api_base, slug, session)
    if img_url:
        return img_url
    return _get_images_list(api_base, slug, session)


def _find_image(unit_name, unit_slug, session):
    base_slug = unit_name.replace(' ', '_')
    candidates = [base_slug]
    for alias in EXTRA_ALIASES.get(unit_slug, []):
        candidates.append(alias.replace(' ', '_'))

    for api in (AOS_API, WHFB_API):
        for cand in candidates:
            img_url = _try_get_image(api, cand, session)
            time.sleep(0.3)
            if img_url:
                return img_url, cand, api
        time.sleep(0.2)

    return None, None, None


def _download_and_validate(img_url, dest_path, session):
    try:
        from PIL import Image

        resp = session.get(img_url, timeout=25, stream=True)
        if resp.status_code != 200:
            return False

        content_type = resp.headers.get('Content-Type', '')
        if not content_type.startswith('image/'):
            return False

        raw = resp.content
        if len(raw) < MIN_BYTES or len(raw) > MAX_BYTES:
            return False

        img = Image.open(io.BytesIO(raw)).convert('RGB')
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
        log.debug('Download error %s: %s', img_url, exc)
        return False


def run():
    try:
        from flask import current_app
        current_app._get_current_object()
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db
        from app.models.game import Faction, Unit
        return _do_run(db, Faction, Unit)


def _do_run(db, Faction, Unit):
    import requests as req

    svg_units = []
    for faction_slug in TARGET_FACTIONS:
        svg_dir = os.path.join(STATIC_DIR, 'img', 'units', faction_slug)
        if not os.path.isdir(svg_dir):
            continue
        for fname in os.listdir(svg_dir):
            if not fname.endswith('.svg'):
                continue
            unit_slug = fname[:-4]
            unit = (
                Unit.query.join(Faction)
                .filter(Faction.slug == faction_slug, Unit.slug == unit_slug)
                .first()
            )
            if unit:
                svg_units.append((unit, os.path.join(svg_dir, fname)))

    if not svg_units:
        log.info('No SVG placeholders found in target factions.')
        return 0, 0

    log.info('Found %d SVG placeholders to re-attempt', len(svg_units))

    session = req.Session()
    session.headers.update({'User-Agent': WIKI_UA})

    rescued = 0
    still_placeholder = 0

    for unit, svg_abs in svg_units:
        faction_slug = unit.faction.slug
        jpg_rel = 'units/{}/{}.jpg'.format(faction_slug, unit.slug)
        jpg_abs = os.path.join(STATIC_DIR, 'img', jpg_rel)

        log.info('Re-attempting: %s (%s)...', unit.name, unit.slug)
        img_url, slug_used, api_used = _find_image(unit.name, unit.slug, session)

        if img_url:
            ok = _download_and_validate(img_url, jpg_abs, session)
            if ok:
                unit.image_path = jpg_rel
                unit.image_source_url = img_url
                db.session.commit()
                os.remove(svg_abs)
                log.info('[RESCUED] %s -> jpg (slug=%s, api=%s)', unit.slug, slug_used, api_used)
                rescued += 1
                continue
            else:
                log.warning('[FAIL] %s -- image invalid/too small', unit.name)
        else:
            log.warning('[NOT FOUND] %s -- still no image on wiki', unit.name)

        still_placeholder += 1

    log.info('Placeholder rescue: %d/%d rescued. %d still SVG.',
             rescued, rescued + still_placeholder, still_placeholder)
    return rescued, still_placeholder


if __name__ == '__main__':
    rescued, remaining = run()
    print(f'\nRESULT: {rescued} rescued, {remaining} still placeholder out of {rescued + remaining} total.')
