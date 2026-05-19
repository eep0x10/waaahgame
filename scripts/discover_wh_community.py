"""
Test Warhammer Community and GW product pages as image sources.
These have predictable unit art at good resolution.

Also: try the Wahapedia source page for aos4 to understand what image
directory naming convention exists.
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    headers_browser = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    }

    # Probe various image CDNs with predictable patterns
    # GW product images come from: https://assets.bnetcmsus-a.akamaihd.net or
    # https://www.games-workshop.com/resources/catalog/product/920x950/<sku>_...jpg
    print("=== Probing GW CDN patterns ===")
    gw_patterns = [
        "https://www.games-workshop.com/resources/catalog/product/920x950/99120206005_Stormvermin.jpg",
        "https://www.games-workshop.com/resources/catalog/product/920x950/99120206005_StormverminFront.jpg",
    ]
    for u in gw_patterns:
        try:
            resp = requests.head(u, headers=headers_browser, timeout=10, allow_redirects=True)
            ct = resp.headers.get('content-type', 'unknown')
            sz = resp.headers.get('content-length', 'unknown')
            print(f"  [{resp.status_code}] [{ct}] [{sz} bytes] {u}")
        except Exception as exc:
            print(f"  [ERR] {u}: {exc}")
        time.sleep(0.3)

    # Try Warhammer Community search
    print("\n=== Warhammer Community article for Skaven ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Check if GW website loads properly
        page = context.new_page()
        intercepted = []

        def on_response(resp):
            ctype = resp.headers.get('content-type', '')
            u = resp.url
            if 'image' in ctype and not any(kw in u.lower() for kw in ['logo', 'icon', 'favicon', 'tracking']):
                if resp.status == 200:
                    cl = resp.headers.get('content-length', '0')
                    try:
                        if int(cl) > 5000:  # > 5KB
                            intercepted.append({'url': u, 'size': cl, 'ct': ctype})
                    except Exception:
                        intercepted.append({'url': u, 'size': '?', 'ct': ctype})

        page.on('response', on_response)

        try:
            page.goto(
                "https://www.warhammer-community.com/en-gb/search/?q=Stormvermin+skaven",
                wait_until='domcontentloaded',
                timeout=30000
            )
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"\nIntercepted images ({len(intercepted)}):")
        for r in intercepted[:10]:
            print(f"  [{r['size']} bytes] {r['url']}")

        # Try to find article images
        large = page.evaluate("""
            () => Array.from(document.querySelectorAll('img'))
                .map(img => ({
                    src: img.src || img.getAttribute('data-src') || '',
                    nw: img.naturalWidth, nh: img.naturalHeight,
                    alt: (img.alt || '').substring(0, 100),
                }))
                .filter(i => i.nw > 200 && i.nh > 200)
        """)
        print(f"\nLarge images ({len(large)}):")
        for img in large[:5]:
            print(f"  [{img['nw']}x{img['nh']}] {img['src']!r} | alt={img['alt']!r}")

        page.close()

        # Probe Wahapedia for ALL aos4 image directories
        print("\n=== Wahapedia directory probe ===")
        dirs_to_try = [
            "https://wahapedia.ru/aos4/img_aos/",
            "https://wahapedia.ru/aos4/img/aos4_units/",
            "https://wahapedia.ru/aos4/img/units/",
            "https://wahapedia.ru/aos4/factions/skaven/img/",
        ]
        for d in dirs_to_try:
            try:
                resp = requests.get(d, headers={'User-Agent': 'Mozilla/5.0', 'Referer': 'https://wahapedia.ru/'}, timeout=10)
                print(f"  [{resp.status_code}] {d} (content-type: {resp.headers.get('content-type', '?')[:40]})")
                if resp.status_code == 200:
                    print(f"    content snippet: {resp.text[:300]!r}")
            except Exception as exc:
                print(f"  [ERR] {d}: {exc}")
            time.sleep(0.3)

        browser.close()

    print("\nWH community discovery complete.")


if __name__ == '__main__':
    main()
