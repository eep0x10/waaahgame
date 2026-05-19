"""
Investigate Games Workshop website as alternative image source.
GW has unit pages with high-quality product images.
Pattern: https://www.games-workshop.com/en-GB/search?query=Stormvermin+skaven

Also check Warhammer Community and any GW CDN patterns.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try a few GW product search pages
URLS = [
    ("gw_search_stormvermin", "https://www.games-workshop.com/en-US/search#q=Stormvermin%20skaven&t=All"),
    ("wh_community", "https://www.warhammer-community.com/en-gb/"),
]

# Also try Lexicanum / Warhammer Wiki
WIKI_URLS = [
    ("warhammer_wiki_stormvermin", "https://ageofsigmar.lexicanum.com/wiki/Stormvermin"),
    ("wahapedia_faction_page", "https://wahapedia.ru/aos4/factions/skaven/"),
]


def probe_for_images(page, url, label, min_dim=200):
    print(f"\n{'='*70}")
    print(f"  {label}: {url}")
    print('='*70)

    intercepted = []

    def on_request(req):
        u = req.url
        if any(u.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
            intercepted.append(u)

    page.on('request', on_request)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(3000)
    except Exception as exc:
        print(f"  [WARN] {exc}")

    # Check all large imgs
    large_imgs = page.evaluate(f"""
        () => {{
            const imgs = Array.from(document.querySelectorAll('img'));
            return imgs
                .map(img => ({{
                    src: img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy') || '',
                    nw: img.naturalWidth,
                    nh: img.naturalHeight,
                    cw: img.clientWidth,
                    ch: img.clientHeight,
                    cls: img.className || '',
                    alt: (img.alt || '').substring(0, 80),
                    parent: img.parentElement ? (img.parentElement.className || '') : '',
                }}))
                .filter(i => i.nw > {min_dim} || i.cw > {min_dim});
        }}
    """)
    print(f"\nLarge images ({len(large_imgs)}):")
    for img in large_imgs[:10]:
        print(f"  src={img['src']!r}")
        print(f"      cls={img['cls']!r}  alt={img['alt']!r}")
        print(f"      natural={img['nw']}x{img['nh']}  client={img['cw']}x{img['ch']}")

    print(f"\nIntercepted image requests ({len(intercepted)}):")
    # Filter to likely unit art (not logos/icons)
    for u in intercepted:
        if not any(kw in u.lower() for kw in ['logo', 'icon', 'favicon', 'sprite', 'pixel', 'tracking']):
            print(f"  {u}")

    page.remove_listener('request', on_request)
    return large_imgs


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Check wahapedia faction page (might have thumbnails)
        page = context.new_page()
        probe_for_images(page, "https://wahapedia.ru/aos4/factions/skaven/", "WAHAPEDIA FACTION PAGE")
        page.close()

        # Check Lexicanum
        page = context.new_page()
        probe_for_images(page, "https://ageofsigmar.lexicanum.com/wiki/Stormvermin", "LEXICANUM STORMVERMIN", min_dim=100)
        page.close()

        # Check Warhammer Wiki Fandom
        page = context.new_page()
        probe_for_images(page, "https://ageofsigmar.fandom.com/wiki/Stormvermin", "FANDOM WIKI STORMVERMIN", min_dim=100)
        page.close()

        browser.close()

    print("\nAlternative source discovery complete.")


if __name__ == '__main__':
    main()
