"""
Scrape warscroll images from Wahapedia for seeded units.

Usage:
  python scripts/scrape_unit_images.py --faction skaven
  python scripts/scrape_unit_images.py --faction seraphon
  python scripts/scrape_unit_images.py --all
  python scripts/scrape_unit_images.py --all --force

Polite behaviour: User-Agent set, 0.5s sleep between requests, idempotent.
Images saved to app/static/img/units/<faction_slug>/<unit_slug>.jpg (max 600px wide, JPEG q85).
"""

import sys
import os
import time
import re
import logging
import argparse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format='%(levelname)s %(message)s')
log = logging.getLogger(__name__)

HEADERS = {
    'User-Agent': 'waaahgame/0.2 (educational)',
    'Accept': 'text/html,application/xhtml+xml',
    'Accept-Language': 'en-US,en;q=0.9',
}

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)


def _fetch_html(url):
    try:
        import requests
        resp = requests.get(url, headers=HEADERS, timeout=15)
        if resp.status_code == 200:
            return resp.text
        log.warning('HTTP %s for %s', resp.status_code, url)
    except Exception as exc:
        log.warning('Fetch error %s: %s', url, exc)
    return None


def _find_image_url(html, page_url):
    """
    Find the main warscroll/unit image in a Wahapedia warscroll page HTML.
    Wahapedia uses various img selectors; we try several in order.
    """
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log.error('beautifulsoup4 not installed')
        return None

    soup = BeautifulSoup(html, 'html.parser')

    # Selector strategies in priority order
    candidates = []

    # 1. Class containing 'warscroll' + 'pic' or 'image'
    for img in soup.find_all('img', class_=re.compile(r'warscroll.*(pic|img|image)', re.I)):
        src = img.get('src') or img.get('data-src')
        if src:
            candidates.append(src)

    # 2. Class containing 'miniature' or 'unit-image'
    for img in soup.find_all('img', class_=re.compile(r'miniature|unit.image|model', re.I)):
        src = img.get('src') or img.get('data-src')
        if src:
            candidates.append(src)

    # 3. Any img whose src contains the faction name or 'warscroll'
    for img in soup.find_all('img'):
        src = img.get('src') or img.get('data-src', '')
        if src and ('warscroll' in src.lower() or '/img/' in src.lower()):
            candidates.append(src)

    # 4. Open Graph image (og:image)
    og = soup.find('meta', property='og:image')
    if og and og.get('content'):
        candidates.append(og['content'])

    # 5. Twitter card image
    tw = soup.find('meta', attrs={'name': 'twitter:image'})
    if tw and tw.get('content'):
        candidates.append(tw['content'])

    # 6. Largest img by area heuristic (last resort — pick any img with meaningful dimensions)
    all_imgs = soup.find_all('img')
    sized = []
    for img in all_imgs:
        src = img.get('src') or img.get('data-src', '')
        if not src:
            continue
        try:
            w = int(img.get('width', 0))
            h = int(img.get('height', 0))
            if w > 100 and h > 100:
                sized.append((w * h, src))
        except (ValueError, TypeError):
            pass
    if sized:
        sized.sort(reverse=True)
        candidates.append(sized[0][1])

    # Normalise to absolute URL
    from urllib.parse import urljoin
    base_domain = 'https://wahapedia.ru'

    # URL fragments that indicate logos / faction icons — not unit art
    _REJECT_PATTERNS = re.compile(
        r'(_logo|logo_|/expansions/|/icons?/|/flags?/|favicon|sprite)',
        re.I,
    )

    seen = set()
    for src in candidates:
        if not src:
            continue
        if src.startswith('//'):
            src = 'https:' + src
        elif src.startswith('/'):
            src = base_domain + src
        elif not src.startswith('http'):
            src = urljoin(page_url, src)

        if src in seen:
            continue
        seen.add(src)

        # Skip known logo / icon patterns
        if _REJECT_PATTERNS.search(src):
            log.debug('Skipping logo/icon URL: %s', src)
            continue

        # Accept by extension
        if any(src.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            return src
        if '.' not in src.split('/')[-1]:
            # No extension but might still be an image endpoint
            return src

    return None


def _download_and_resize(img_url, dest_path):
    """Download image, resize to max 600px wide, save as JPEG q85."""
    try:
        import requests
        from PIL import Image
        import io

        log.info('Downloading %s', img_url)
        time.sleep(0.5)
        resp = requests.get(img_url, headers=HEADERS, timeout=20, stream=True)
        if resp.status_code != 200:
            log.warning('Image HTTP %s for %s', resp.status_code, img_url)
            return False

        content = resp.content
        img = Image.open(io.BytesIO(content)).convert('RGB')

        # Reject tiny images (icons / logos — not real unit art)
        MIN_DIM = 80
        if img.width < MIN_DIM or img.height < MIN_DIM:
            log.warning('Rejecting tiny image %dx%d from %s', img.width, img.height, img_url)
            return False

        max_w = 600
        if img.width > max_w:
            ratio = max_w / img.width
            new_h = int(img.height * ratio)
            img = img.resize((max_w, new_h), Image.LANCZOS)

        os.makedirs(os.path.dirname(dest_path), exist_ok=True)
        img.save(dest_path, 'JPEG', quality=85, optimize=True)
        log.info('Saved %s (%dx%d)', dest_path, img.width, img.height)
        return True

    except Exception as exc:
        log.warning('Image download/resize failed for %s: %s', img_url, exc)
        return False


def scrape(faction=None, force=False):
    """Main scraping function. faction=None means all factions.

    Works both inside an existing Flask app context (CLI) and standalone.
    """
    from app.extensions import db
    from app.models.game import Faction, Unit

    try:
        from flask import current_app
        current_app._get_current_object()
        return _do_scrape(db, Faction, Unit, faction, force)
    except RuntimeError:
        pass

    from app import create_app
    app = create_app()
    with app.app_context():
        from app.extensions import db as _db
        from app.models.game import Faction as F, Unit as U
        return _do_scrape(_db, F, U, faction, force)


def _do_scrape(db, Faction, Unit, faction=None, force=False):
    """Core scraping logic. Must be called inside an active Flask app context."""
    query = Unit.query.join(Faction)
    if faction:
        query = query.filter(Faction.slug == faction)

    units = query.all()
    log.info('Scraping images for %d units (faction=%s, force=%s)', len(units), faction or 'all', force)

    scraped = 0
    skipped = 0
    failed = 0

    for unit in units:
        # Determine dest path
        faction_slug = unit.faction.slug
        dest_rel = f'units/{faction_slug}/{unit.slug}.jpg'
        dest_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit.slug}.jpg')

        # Idempotency check
        if os.path.exists(dest_abs) and not force:
            log.info('[skip] %s -- image exists', unit.slug)
            if not unit.image_path:
                unit.image_path = dest_rel
                db.session.commit()
            skipped += 1
            continue

        if not unit.wahapedia_url:
            log.warning('[skip] %s -- no wahapedia_url', unit.slug)
            failed += 1
            continue

        # Fetch warscroll page
        log.info('Fetching warscroll page for %s', unit.slug)
        time.sleep(0.5)
        html = _fetch_html(unit.wahapedia_url)
        if not html:
            log.warning('[fail] %s -- could not fetch page', unit.slug)
            failed += 1
            continue

        img_url = _find_image_url(html, unit.wahapedia_url)
        if not img_url:
            log.warning('[fail] %s -- image not found on page', unit.slug)
            failed += 1
            continue

        ok = _download_and_resize(img_url, dest_abs)
        if ok:
            unit.image_path = dest_rel
            unit.image_source_url = img_url
            db.session.commit()
            scraped += 1
        else:
            failed += 1

    log.info('Image scrape complete. Scraped=%d, Skipped=%d, Failed=%d', scraped, skipped, failed)
    return scraped, skipped, failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Scrape unit images from Wahapedia')
    parser.add_argument('--faction', default=None, help='Faction slug to scrape')
    parser.add_argument('--all', action='store_true', dest='all_factions', help='Scrape all factions')
    parser.add_argument('--force', action='store_true', help='Re-download even if image exists')
    args = parser.parse_args()

    if not args.faction and not args.all_factions:
        parser.print_help()
        sys.exit(1)

    scrape(faction=args.faction, force=args.force)
