"""
Check GW website product pages for unit images.
Also check if Wahapedia has a separate image CDN we can predict URLs for.
"""

import sys
import os
import time
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def probe_for_large_images(page, url, label, min_dim=150, wait_ms=4000):
    print(f"\n{'='*70}")
    print(f"  {label}: {url}")
    print('='*70)

    intercepted = []

    def on_response(resp):
        ctype = resp.headers.get('content-type', '')
        u = resp.url
        if 'image' in ctype or any(u.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            intercepted.append({'url': u, 'ct': ctype})

    page.on('response', on_response)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(wait_ms)
    except Exception as exc:
        print(f"  [WARN] {exc}")

    # Check all large imgs
    large_imgs = page.evaluate(f"""
        () => {{
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs
                .map(img => ({{
                    src: img.src || img.getAttribute('data-src') || '',
                    nw: img.naturalWidth,
                    nh: img.naturalHeight,
                    cls: (img.className || '').substring(0, 100),
                    alt: (img.alt || '').substring(0, 100),
                    parent: img.parentElement ? (img.parentElement.className || '').substring(0, 100) : '',
                }}))
                .filter(i => (i.nw > {min_dim} && i.nh > {min_dim}) || (i.src && i.src.length > 10));
        }}
    """)

    print(f"\nImages ({len(large_imgs)} total, showing filtered):")
    for img in large_imgs:
        if img['nw'] > min_dim and img['nh'] > min_dim:
            print(f"  [{img['nw']}x{img['nh']}] src={img['src']!r}")
            print(f"      alt={img['alt']!r}  cls={img['cls']!r}")

    print(f"\nIntercepted image responses ({len(intercepted)}):")
    for r in intercepted[:20]:
        u = r['url']
        if not any(kw in u.lower() for kw in ['logo', 'icon', 'favicon', 'sprite', 'pixel', 'tracking', 'analytics', 'cookie']):
            print(f"  [{r['ct'][:30]}] {u}")

    page.remove_listener('response', on_response)
    return large_imgs, intercepted


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            accept_downloads=False,
        )

        # Try GW product search for Stormvermin
        page = context.new_page()
        imgs, reqs = probe_for_large_images(
            page,
            "https://www.games-workshop.com/en-US/search#q=Stormvermin&t=All",
            "GW SEARCH STORMVERMIN",
            min_dim=200,
            wait_ms=5000,
        )
        page.close()

        # Try Age of Sigmar Fandom wiki with more time
        page = context.new_page()
        imgs, reqs = probe_for_large_images(
            page,
            "https://ageofsigmar.fandom.com/wiki/Stormvermin",
            "FANDOM STORMVERMIN (longer wait)",
            min_dim=100,
            wait_ms=6000,
        )
        page.close()

        # Wahapedia image CDN probe - try direct URL pattern
        # The old scraper expected img_aos/ path
        # Let's try some guessed URLs
        print("\n\n=== Probing Wahapedia CDN for direct image URLs ===")
        import requests

        test_urls = [
            "https://wahapedia.ru/aos4/img_aos/Stormvermin.jpg",
            "https://wahapedia.ru/aos4/img_aos/Stormvermin.png",
            "https://wahapedia.ru/aos4/img_aos/stormvermin.jpg",
            "https://wahapedia.ru/aos4/img/Stormvermin.jpg",
            "https://wahapedia.ru/img/aos4/Stormvermin.jpg",
            "https://wahapedia.ru/aos4/factions/skaven/img/Stormvermin.jpg",
            "https://wahapedia.ru/aos4/img_aos/SKN_Stormvermin.jpg",
        ]

        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Referer': 'https://wahapedia.ru/aos4/factions/skaven/Stormvermin',
        }

        for u in test_urls:
            try:
                resp = requests.head(u, headers=headers, timeout=10, allow_redirects=True)
                ct = resp.headers.get('content-type', 'unknown')
                print(f"  [{resp.status_code}] [{ct}] {u}")
            except Exception as exc:
                print(f"  [ERR] {u}: {exc}")
            time.sleep(0.3)

        browser.close()

    print("\nGW discovery complete.")


if __name__ == '__main__':
    main()
