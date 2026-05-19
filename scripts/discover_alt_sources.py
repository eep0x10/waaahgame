"""
Test remaining alternative image sources:
1. Warhammer Wiki (ageofsigmar.fandom.com) with cookie bypass
2. Wahapedia warscrolls.html - might have unit thumbnails
3. Try Age of Sigmar official site
4. Games Workshop search API (JSON)
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            # Accept cookies to bypass consent walls
            extra_http_headers={
                'Accept-Language': 'en-US,en;q=0.9',
            }
        )

        # ---------------------------------------------------------------
        print("\n=== 1. Fandom Wiki - Stormvermin (with longer wait + cookie bypass) ===")
        page = context.new_page()
        intercepted = []

        def collect_img(resp):
            u = resp.url
            if resp.status == 200 and any(u.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp']):
                cl = resp.headers.get('content-length', '0')
                try:
                    if int(cl) > 5000:
                        intercepted.append({'url': u, 'size': cl})
                except Exception:
                    pass

        page.on('response', collect_img)

        try:
            page.goto("https://ageofsigmar.fandom.com/wiki/Stormvermin", wait_until='domcontentloaded', timeout=30000)
            # Accept cookie consent if present
            try:
                btn = page.query_selector('button[data-tracking="accept-all"]')
                if btn:
                    btn.click()
                    page.wait_for_timeout(1000)
            except Exception:
                pass
            page.wait_for_timeout(6000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Title: {page.title()!r}")
        print(f"  URL: {page.url}")
        print(f"\n  Intercepted images ({len(intercepted)}):")
        for r in intercepted:
            print(f"    [{r['size']} bytes] {r['url']}")

        imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img, [data-src]'))
                .map(el => ({
                    src: el.src || el.getAttribute('data-src') || '',
                    nw: el.naturalWidth || 0, nh: el.naturalHeight || 0,
                    alt: (el.alt || '').substring(0, 80),
                    cls: (el.className || '').substring(0, 80),
                }))
                .filter(i => i.nw > 100 || i.nh > 100 || i.src.includes('wikia'))
        """)
        print(f"\n  DOM images matching wiki: {len(imgs)}")
        for img in imgs[:10]:
            print(f"    [{img['nw']}x{img['nh']}] {img['src'][:120]!r}")
            print(f"      alt={img['alt']!r}")

        # Try to get infobox image
        infobox = page.query_selector('.pi-image-thumbnail, .infobox img, .portable-infobox img')
        if infobox:
            src = page.evaluate("el => el.src", infobox)
            print(f"\n  Infobox img: {src!r}")
        else:
            print("\n  No infobox image found")

        # Print relevant HTML
        print("\n  Body snippet (looking for image content):")
        body = page.content()
        for line in body.split('\n'):
            if any(kw in line.lower() for kw in ['stormvermin', 'wikia', 'static', '.jpg', '.png']):
                stripped = line.strip()
                if len(stripped) > 10:
                    print(f"    {stripped[:200]}")

        page.close()

        # ---------------------------------------------------------------
        print("\n\n=== 2. GW Search API (JSON) ===")
        search_urls = [
            "https://www.games-workshop.com/en-US/search-results?q=Stormvermin+skaven&format=json",
            "https://www.games-workshop.com/api/v2/en-US/search?q=Stormvermin",
        ]
        req_headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'X-Requested-With': 'XMLHttpRequest',
        }
        for u in search_urls:
            try:
                resp = requests.get(u, headers=req_headers, timeout=10)
                print(f"  [{resp.status_code}] {u}")
                ct = resp.headers.get('content-type', '')
                print(f"    content-type: {ct}")
                if 'json' in ct:
                    data = resp.json()
                    print(f"    data keys: {list(data.keys()) if isinstance(data, dict) else type(data)}")
                elif resp.status_code == 200:
                    print(f"    snippet: {resp.text[:200]!r}")
            except Exception as exc:
                print(f"  [ERR] {u}: {exc}")
            time.sleep(0.5)

        # ---------------------------------------------------------------
        print("\n\n=== 3. Wahapedia image gallery / collated warscrolls ===")
        page = context.new_page()
        intercepted2 = []

        def collect_img2(resp):
            u = resp.url
            if resp.status == 200:
                ctype = resp.headers.get('content-type', '')
                if 'image' in ctype:
                    cl = resp.headers.get('content-length', '0')
                    intercepted2.append({'url': u, 'size': cl, 'ct': ctype})

        page.on('response', collect_img2)
        try:
            page.goto("https://wahapedia.ru/aos4/factions/skaven/warscrolls.html", wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Intercepted images ({len(intercepted2)}):")
        # Group by size
        big = [r for r in intercepted2 if int(r.get('size', 0) or 0) > 50000]
        print(f"  Large (>50KB): {len(big)}")
        for r in big[:5]:
            print(f"    [{r['size']} bytes] {r['url']}")

        page.close()
        browser.close()

    print("\nAlternative sources discovery complete.")


if __name__ == '__main__':
    main()
