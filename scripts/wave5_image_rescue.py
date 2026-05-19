"""
Wave 5 image rescue: 5-strategy ladder for all units with SVG placeholders
or missing images in new factions.

Strategy order:
1. Wahapedia HTML scrape
2. Lexicanum (wh.lexicanum.com / age-of-sigmar.lexicanum.com)
3. Goonhammer search
4. Warhammer Community search
5. Fandom rescrape with alt slugs

Images saved as JPEG, max 800px wide, quality 85.
Sleeps 1s between requests to same host.
"""

import sys
import os
import re
import time
import logging
import io

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

UA = 'Mozilla/5.0 (waaahgame-seed-bot)'
MIN_BYTES = 10 * 1024
MAX_BYTES = 8 * 1024 * 1024
MIN_W = 150
MIN_H = 150

AOS_FANDOM_API = 'https://ageofsigmar.fandom.com/api.php'
WHFB_FANDOM_API = 'https://warhammerfantasy.fandom.com/api.php'


def _headers(host=None):
    h = {'User-Agent': UA}
    if host:
        h['Referer'] = f'https://{host}/'
    return h


def _download_and_save(img_url, dest_path, session):
    try:
        from PIL import Image
        resp = session.get(img_url, timeout=25, stream=True, headers=_headers())
        if resp.status_code != 200:
            return False
        ct = resp.headers.get('Content-Type', '')
        if 'image' not in ct and not img_url.lower().endswith(('.jpg', '.jpeg', '.png', '.webp', '.gif')):
            return False
        raw = resp.content
        if len(raw) < MIN_BYTES or len(raw) > MAX_BYTES:
            return False
        img = Image.open(io.BytesIO(raw)).convert('RGB')
        if img.width < MIN_W or img.height < MIN_H:
            return False
        max_w = 800
        if img.width > max_w:
            ratio = max_w / img.width
            img = img.resize((max_w, int(img.height * ratio)), Image.LANCZOS)
        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, 'JPEG', quality=85, optimize=True)
        return True
    except Exception as exc:
        log.debug('Download error %s: %s', img_url, exc)
        return False


def _strategy1_wahapedia(unit_name, faction_slug, session):
    slug = unit_name.replace(' ', '-').replace(',', '').replace("'", '')
    url = f'https://wahapedia.ru/aos4/factions/{faction_slug}/{slug}'
    try:
        resp = session.get(url, timeout=15, headers=_headers('wahapedia.ru'))
        time.sleep(1)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        selectors = [
            ('class', re.compile(r'WarscrollImage|wh-img|warscroll.*img|unit.*image', re.I)),
            ('class', re.compile(r'Warscroll', re.I)),
        ]
        for attr, pattern in selectors:
            for img in soup.find_all('img', attrs={attr: pattern}):
                src = img.get('src') or img.get('data-src') or ''
                if src and not src.endswith('.svg'):
                    if src.startswith('//'):
                        src = 'https:' + src
                    elif src.startswith('/'):
                        src = 'https://wahapedia.ru' + src
                    return src
        for img in soup.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src or src.endswith('.svg') or src.endswith('.gif'):
                continue
            if any(kw in src.lower() for kw in ['logo', 'icon', 'banner', 'bg', 'background']):
                continue
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://wahapedia.ru' + src
            if src.startswith('http'):
                return src
    except Exception as exc:
        log.debug('Wahapedia strategy error %s: %s', unit_name, exc)
    return None


def _strategy2_lexicanum(unit_name, session):
    bases = [
        'https://wh.lexicanum.com/wiki/',
        'https://age-of-sigmar.lexicanum.com/wiki/',
    ]
    for base in bases:
        for slug in [unit_name.replace(' ', '_'), unit_name.replace(' ', '-')]:
            try:
                url = base + slug
                resp = session.get(url, timeout=15, headers=_headers('wh.lexicanum.com'))
                time.sleep(1)
                if resp.status_code != 200:
                    continue
                from bs4 import BeautifulSoup
                soup = BeautifulSoup(resp.text, 'html.parser')
                infobox = soup.find(class_=re.compile(r'infobox|thumb|image', re.I))
                if infobox:
                    img = infobox.find('img')
                    if img:
                        src = img.get('src') or img.get('data-src') or ''
                        if src and not src.endswith('.svg'):
                            if src.startswith('//'):
                                src = 'https:' + src
                            elif src.startswith('/'):
                                src = base.rstrip('/wiki/') + src
                            return src
            except Exception as exc:
                log.debug('Lexicanum error %s: %s', unit_name, exc)
    return None


def _strategy3_goonhammer(unit_name, session):
    try:
        q = unit_name.replace(' ', '+')
        url = f'https://www.goonhammer.com/?s={q}'
        resp = session.get(url, timeout=15, headers=_headers('www.goonhammer.com'))
        time.sleep(1)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        article_link = soup.find('a', href=re.compile(r'goonhammer\.com/'))
        if not article_link:
            return None
        art_url = article_link['href']
        resp2 = session.get(art_url, timeout=15, headers=_headers('www.goonhammer.com'))
        time.sleep(1)
        if resp2.status_code != 200:
            return None
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        for img in soup2.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src or 'logo' in src.lower() or 'icon' in src.lower():
                continue
            if any(src.lower().endswith(e) for e in ['.jpg', '.jpeg', '.png', '.webp']):
                return src
    except Exception as exc:
        log.debug('Goonhammer error %s: %s', unit_name, exc)
    return None


def _strategy4_whc(unit_name, session):
    try:
        q = unit_name.replace(' ', '+')
        url = f'https://www.warhammer-community.com/?s={q}'
        resp = session.get(url, timeout=15, headers=_headers('www.warhammer-community.com'))
        time.sleep(1)
        if resp.status_code != 200:
            return None
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(resp.text, 'html.parser')
        article = soup.find('article')
        if not article:
            return None
        link = article.find('a', href=True)
        if not link:
            return None
        art_url = link['href']
        resp2 = session.get(art_url, timeout=15, headers=_headers('www.warhammer-community.com'))
        time.sleep(1)
        if resp2.status_code != 200:
            return None
        soup2 = BeautifulSoup(resp2.text, 'html.parser')
        for img in soup2.find_all('img'):
            src = img.get('src') or img.get('data-src') or ''
            if not src or 'logo' in src.lower():
                continue
            if any(src.lower().endswith(e) for e in ['.jpg', '.jpeg', '.png', '.webp']):
                return src
    except Exception as exc:
        log.debug('WHC error %s: %s', unit_name, exc)
    return None


def _strategy5_fandom(unit_name, session):
    base_slug = unit_name.replace(' ', '_')
    alts = [
        base_slug,
        base_slug + '_Warscroll',
        base_slug + '_(unit)',
        unit_name.replace(' ', '-'),
        unit_name.split(',')[0].strip().replace(' ', '_'),
    ]
    for api in (AOS_FANDOM_API, WHFB_FANDOM_API):
        for slug in alts:
            try:
                import requests as req
                url = (
                    f'{api}?action=query'
                    f'&titles={req.utils.quote(slug)}'
                    f'&prop=pageimages'
                    f'&piprop=thumbnail|name'
                    f'&pithumbsize=700'
                    f'&format=json'
                )
                resp = session.get(url, timeout=15, headers=_headers())
                time.sleep(0.5)
                data = resp.json()
                pages = data.get('query', {}).get('pages', {})
                for pid, page in pages.items():
                    if page.get('missing') == '':
                        continue
                    thumb = page.get('thumbnail', {})
                    if thumb.get('source'):
                        return thumb['source']
            except Exception as exc:
                log.debug('Fandom alt error %s %s: %s', slug, api, exc)
    return None


def _find_image(unit_name, faction_slug, session):
    strategies = [
        ('wahapedia', lambda: _strategy1_wahapedia(unit_name, faction_slug, session)),
        ('lexicanum', lambda: _strategy2_lexicanum(unit_name, session)),
        ('goonhammer', lambda: _strategy3_goonhammer(unit_name, session)),
        ('whc', lambda: _strategy4_whc(unit_name, session)),
        ('fandom_alt', lambda: _strategy5_fandom(unit_name, session)),
    ]
    for name, fn in strategies:
        try:
            url = fn()
            if url:
                log.debug('Strategy %s found url for %s', name, unit_name)
                return url, name
        except Exception as exc:
            log.debug('Strategy %s exception for %s: %s', name, unit_name, exc)
    return None, None


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

    target_units = []

    for unit in Unit.query.join(Faction).filter(Faction.code.like('%-%-%-%-') | Faction.code.notlike('%')).all():
        pass

    all_units = Unit.query.join(Faction).all()
    for unit in all_units:
        if not unit.image_path or unit.image_path.endswith('.svg'):
            target_units.append(unit)
        elif unit.image_path.endswith('.jpg'):
            abs_path = os.path.join(STATIC_DIR, unit.image_path.lstrip('img/').lstrip('/'))
            full_path = os.path.join(STATIC_DIR, 'img', unit.image_path.replace('img/', '', 1).lstrip('/'))
            if not os.path.exists(full_path):
                target_units.append(unit)

    log.info('Units needing images: %d', len(target_units))

    session = req.Session()
    session.headers.update({'User-Agent': UA})

    stats = {'wahapedia': 0, 'lexicanum': 0, 'goonhammer': 0, 'whc': 0, 'fandom_alt': 0}
    rescued = 0
    still_placeholder = 0

    for unit in target_units:
        faction_slug = unit.faction.slug
        unit_slug = unit.slug
        jpg_rel = f'units/{faction_slug}/{unit_slug}.jpg'
        jpg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.jpg')

        log.info('Rescuing: %s (%s)...', unit.name, faction_slug)

        img_url, strategy = _find_image(unit.name, faction_slug, session)

        if img_url:
            ok = _download_and_save(img_url, jpg_abs, session)
            if ok:
                old_path = unit.image_path
                unit.image_path = jpg_rel
                db.session.commit()
                if old_path and old_path.endswith('.svg'):
                    svg_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit_slug}.svg')
                    if os.path.exists(svg_abs):
                        os.remove(svg_abs)
                log.info('[RESCUED] %s via %s', unit.slug, strategy)
                stats[strategy] = stats.get(strategy, 0) + 1
                rescued += 1
                continue
            else:
                log.warning('[IMG_INVALID] %s -- url=%s', unit.name, img_url)
        else:
            log.warning('[NOT_FOUND] %s -- no image found', unit.name)

        still_placeholder += 1

    total = rescued + still_placeholder
    log.info('Rescue complete: %d/%d rescued. Per strategy: %s',
             rescued, total, stats)
    return rescued, still_placeholder, stats


if __name__ == '__main__':
    rescued, remaining, stats = run()
    print(f'\nRESCUED: {rescued}, STILL_PLACEHOLDER: {remaining}')
    for s, n in stats.items():
        if n:
            print(f'  {s}: {n}')
