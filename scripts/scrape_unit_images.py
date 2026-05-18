"""
Scrape warscroll images from Wahapedia (Playwright headless Chromium) for seeded units.

Usage:
  python scripts/scrape_unit_images.py --faction skaven
  python scripts/scrape_unit_images.py --faction seraphon
  python scripts/scrape_unit_images.py --all
  python scripts/scrape_unit_images.py --all --force

Via Flask CLI:
  flask --app run.py scrape-images --all --force

Polite behaviour:
  - Single browser context reused across all units (no relaunch per unit)
  - 1s sleep between page loads
  - Real browser UA to avoid bot-detection
  - Referer header set on image downloads

Images saved to app/static/img/units/<faction_slug>/<unit_slug>.jpg
  (max 600px wide, JPEG q85).

NOTE: Discovery (2026-05-18) confirmed that Wahapedia warscroll pages do NOT serve
unit artwork images in any form (no <img> tags, no CSS background-images, no CDN paths).
The 'picSearch' element on each warscroll page is a Google Image Search link only.
The scraper is written to log what it found and skip gracefully. Selector constants
at the top of this file are the hook for future sources.
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

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

# User-Agent: look like a real browser so Wahapedia doesn't block headless
BROWSER_UA = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/124.0.0.0 Safari/537.36'
)

DOWNLOAD_HEADERS = {
    'User-Agent': BROWSER_UA,
    'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
}

STATIC_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    'app', 'static',
)

# ---------------------------------------------------------------------------
# Selector priority list.
# Tried against Wahapedia aos4 warscroll pages on 2026-05-18 -- all returned
# zero matches because Wahapedia serves NO unit art images on warscroll pages.
# Update these when a working source is identified.
# ---------------------------------------------------------------------------
WARSCROLL_IMG_SELECTORS = [
    # Wahapedia warscroll art selectors (confirmed absent 2026-05-18)
    "img.warscroll-pic",
    ".WarscrollPic img",
    ".warscroll-pic img",
    "img[src*='img_aos/']",
    ".warscroll-art img",
    "img[class*='warscroll']",
    "img[class*='Warscroll']",
    # Generic large-image heuristic (fallback)
    "img[src*='/img/'][width][height]",
]

# Minimum acceptable image dimensions
MIN_IMG_W = 200
MIN_IMG_H = 200

# ---------------------------------------------------------------------------
# Image rejection patterns (logos, icons, expansion badges)
# ---------------------------------------------------------------------------
_REJECT_PATTERN = re.compile(
    r'(_logo|logo_|/expansions/|/icons?/|/flags?/|favicon|sprite|picSearch'
    r'|TooltipLink|abOffensive|abDefensive|abRallying|abControl|abShooting'
    r'|abSpecial|abMovement|abDamage|Corner[0-9]|Button_|boosty|social_)',
    re.I,
)


# ---------------------------------------------------------------------------
# Playwright helpers
# ---------------------------------------------------------------------------

def _launch_browser():
    """Launch and return a Playwright sync browser + context. Caller must close."""
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        log.error(
            'playwright is not installed. '
            'Run: pip install playwright && playwright install chromium'
        )
        raise

    pw = sync_playwright().start()
    browser = pw.chromium.launch(headless=True)
    context = browser.new_context(user_agent=BROWSER_UA)
    return pw, browser, context


def _load_page(page, url, timeout_ms=30000):
    """
    Navigate to url, wait for DOM. Falls back to domcontentloaded + 3s wait
    if networkidle times out (Wahapedia keeps loading ads indefinitely).
    Returns True if page loaded, False on hard failure.
    """
    try:
        page.goto(url, wait_until='networkidle', timeout=timeout_ms)
        return True
    except Exception:
        pass

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=timeout_ms)
        page.wait_for_timeout(3000)
        return True
    except Exception as exc:
        log.warning('Page load failed for %s: %s', url, exc)
        return False


def _find_image_url_playwright(page, page_url):
    """
    Find the main warscroll/unit image in the loaded Playwright page.
    Returns (src_url, selector_used) or (None, reason).
    """
    from urllib.parse import urljoin

    # 1. Try each CSS selector in priority order
    for selector in WARSCROLL_IMG_SELECTORS:
        try:
            elements = page.query_selector_all(selector)
        except Exception:
            continue
        for el in elements:
            src = el.get_attribute('src') or el.get_attribute('data-src') or ''
            if not src:
                continue

            # Normalise to absolute URL
            if src.startswith('//'):
                src = 'https:' + src
            elif src.startswith('/'):
                src = 'https://wahapedia.ru' + src
            elif not src.startswith('http'):
                src = urljoin(page_url, src)

            if _REJECT_PATTERN.search(src):
                continue

            # Validate natural dimensions via JS
            try:
                dims = page.evaluate(
                    '(el) => ({ w: el.naturalWidth, h: el.naturalHeight })', el
                )
                if dims['w'] >= MIN_IMG_W and dims['h'] >= MIN_IMG_H:
                    return src, selector
            except Exception:
                # If JS eval fails, accept the src anyway (dimensions unknown)
                return src, selector

    # 2. Heuristic: find any large <img> not matching reject patterns
    try:
        large = page.evaluate(
            f"""
            () => {{
                const imgs = Array.from(document.querySelectorAll('img'));
                const reject = /{_REJECT_PATTERN.pattern}/i;
                for (const img of imgs) {{
                    const src = img.src || img.getAttribute('data-src') || '';
                    if (!src || reject.test(src)) continue;
                    if (img.naturalWidth >= {MIN_IMG_W} && img.naturalHeight >= {MIN_IMG_H}) {{
                        return src;
                    }}
                }}
                return null;
            }}
            """
        )
        if large:
            return large, 'heuristic:large-img'
    except Exception:
        pass

    # 3. Try og:image / twitter:image meta tags
    for meta_sel, meta_attr in [
        ('meta[property="og:image"]', 'content'),
        ('meta[name="twitter:image"]', 'content'),
    ]:
        el = page.query_selector(meta_sel)
        if el:
            src = el.get_attribute(meta_attr) or ''
            if src and not _REJECT_PATTERN.search(src):
                return src, meta_sel

    # 4. Extract picSearch diagnostic link (Google Images query)
    try:
        pic_anchor = page.query_selector('a:has(.picSearch), a > .picSearch')
        if not pic_anchor:
            # Try parent traversal
            pic_div = page.query_selector('.picSearch')
            if pic_div:
                pic_anchor = page.evaluate(
                    "(el) => el.closest('a') ? el.closest('a').href : null", pic_div
                )
        if pic_anchor and isinstance(pic_anchor, str):
            log.info('picSearch (Google Images) link: %s', pic_anchor)
        elif pic_anchor:
            href = pic_anchor.get_attribute('href') or ''
            if href:
                log.info('picSearch (Google Images) link: %s', href)
    except Exception:
        pass

    return None, 'no-selector-matched'


# ---------------------------------------------------------------------------
# Image download + resize
# ---------------------------------------------------------------------------

def _download_and_resize(img_url, dest_path, referer_url):
    """
    Download image from img_url, resize to max 600px wide, save as JPEG q85.
    Returns True on success, False on failure.
    """
    import io
    try:
        import requests
        from PIL import Image

        headers = dict(DOWNLOAD_HEADERS)
        headers['Referer'] = referer_url

        log.info('Downloading %s', img_url)
        resp = requests.get(img_url, headers=headers, timeout=20, stream=True)
        if resp.status_code != 200:
            log.warning('Image HTTP %s for %s', resp.status_code, img_url)
            return False

        content = resp.content
        img = Image.open(io.BytesIO(content)).convert('RGB')

        # Reject tiny images (icons / logos even if they slipped through selector check)
        if img.width < MIN_IMG_W or img.height < MIN_IMG_H:
            log.warning(
                'Rejecting too-small image %dx%d from %s', img.width, img.height, img_url
            )
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


# ---------------------------------------------------------------------------
# Core scrape logic
# ---------------------------------------------------------------------------

def scrape(faction=None, force=False):
    """
    Main scraping entry point. Works both inside an existing Flask app context
    (CLI) and standalone (creates its own app context).

    Returns (scraped_count, skipped_count, failed_count).
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

    log.info(
        'Starting image scrape for %d units (faction=%s, force=%s)',
        len(units), faction or 'all', force,
    )

    if not units:
        log.warning('No units found for faction=%s', faction)
        return 0, 0, 0

    scraped = 0
    skipped = 0
    failed = 0

    pw, browser, context = _launch_browser()
    page = context.new_page()

    try:
        for unit in units:
            faction_slug = unit.faction.slug
            dest_rel = f'units/{faction_slug}/{unit.slug}.jpg'
            dest_abs = os.path.join(STATIC_DIR, 'img', 'units', faction_slug, f'{unit.slug}.jpg')

            # --- Idempotency ---
            if os.path.exists(dest_abs) and not force:
                log.info('[skip] %s -- image file already exists', unit.slug)
                if not unit.image_path:
                    unit.image_path = dest_rel
                    db.session.commit()
                skipped += 1
                continue

            if not unit.wahapedia_url:
                log.warning('[skip] %s -- no wahapedia_url', unit.slug)
                failed += 1
                continue

            log.info('Processing %s  url=%s', unit.slug, unit.wahapedia_url)
            loaded = _load_page(page, unit.wahapedia_url)
            if not loaded:
                log.warning('[fail] %s -- page load failed', unit.slug)
                failed += 1
                time.sleep(1)
                continue

            img_url, selector_used = _find_image_url_playwright(page, unit.wahapedia_url)
            if not img_url:
                log.warning(
                    '[fail] %s -- no warscroll image found (reason: %s)',
                    unit.slug, selector_used,
                )
                failed += 1
                time.sleep(1)
                continue

            log.info('[found] %s -- image=%s  via=%s', unit.slug, img_url, selector_used)
            ok = _download_and_resize(img_url, dest_abs, referer_url=unit.wahapedia_url)
            if ok:
                unit.image_path = dest_rel
                unit.image_source_url = img_url
                db.session.commit()
                log.info('[scraped] %s', unit.slug)
                scraped += 1
            else:
                log.warning('[fail] %s -- image download/resize failed', unit.slug)
                failed += 1

            time.sleep(1)

    finally:
        page.close()
        browser.close()
        pw.stop()

    log.info(
        'Image scrape complete. Scraped=%d  Skipped=%d  Failed=%d',
        scraped, skipped, failed,
    )
    return scraped, skipped, failed


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------

if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Scrape unit images from Wahapedia (Playwright headless Chromium)'
    )
    parser.add_argument('--faction', default=None, help='Faction slug to scrape')
    parser.add_argument(
        '--all', action='store_true', dest='all_factions', help='Scrape all factions'
    )
    parser.add_argument(
        '--force', action='store_true', help='Re-download even if image file exists'
    )
    args = parser.parse_args()

    if not args.faction and not args.all_factions:
        parser.print_help()
        sys.exit(1)

    scrape(faction=args.faction, force=args.force)
