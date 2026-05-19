"""
Look at actual WHC article pages for Skaven warscroll reveals.
Also check if the WHC search results have article links we can follow.
And check the official AoS site for unit images.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # -------
        print("=== 1. WHC search results for Stormvermin - extract article links ===")
        page = context.new_page()
        try:
            page.goto("https://www.warhammer-community.com/en-gb/search/?q=Stormvermin+skaven", wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        # Get all article links
        links = page.evaluate("""
            () => Array.from(document.querySelectorAll('a'))
                .map(a => ({href: a.href, text: (a.textContent || '').trim().substring(0,100)}))
                .filter(a => a.href.includes('warhammer-community.com') &&
                             !a.href.includes('#') &&
                             a.text.length > 5 &&
                             (a.text.toLowerCase().includes('stormvermin') ||
                              a.text.toLowerCase().includes('skaven') ||
                              a.href.toLowerCase().includes('stormvermin') ||
                              a.href.toLowerCase().includes('skaven')))
        """)
        print(f"  Found {len(links)} relevant links:")
        for l in links[:10]:
            print(f"    {l['text']!r}: {l['href']}")

        page.close()

        # -------
        print("\n=== 2. Check a specific WHC warscroll article ===")
        # Known WHC pattern: https://www.warhammer-community.com/en-gb/articles/SLUG/
        page = context.new_page()
        intercepted = []

        def on_response(resp):
            u = resp.url
            ctype = resp.headers.get('content-type', '')
            if resp.status == 200 and 'image' in ctype:
                cl = resp.headers.get('content-length', '0')
                try:
                    if int(cl or 0) > 20000:
                        intercepted.append({'url': u, 'size': int(cl), 'ct': ctype})
                except Exception:
                    pass

        page.on('response', on_response)
        try:
            page.goto(
                "https://www.warhammer-community.com/en-gb/articles/skaven-the-new-warscrolls-for-a-classic-chaos-force/",
                wait_until='domcontentloaded',
                timeout=30000
            )
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Title: {page.title()!r}")
        print(f"  Intercepted large images ({len(intercepted)}):")
        for r in sorted(intercepted, key=lambda x: x['size'], reverse=True)[:10]:
            print(f"    [{r['size']:,} bytes] {r['url']}")

        imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img'))
                .filter(i => i.naturalWidth > 200 && i.naturalHeight > 200)
                .map(i => ({src: i.src, nw: i.naturalWidth, nh: i.naturalHeight, alt: (i.alt||'').substring(0,80)}))
        """)
        print(f"  Large DOM imgs: {len(imgs)}")
        for img in imgs[:8]:
            print(f"    [{img['nw']}x{img['nh']}] {img['src'][:120]!r} alt={img['alt']!r}")

        page.close()

        # -------
        print("\n=== 3. Check AoS official site for faction ===")
        page = context.new_page()
        intercepted2 = []

        def on_response2(resp):
            u = resp.url
            ctype = resp.headers.get('content-type', '')
            if resp.status == 200 and 'image' in ctype:
                cl = resp.headers.get('content-length', '0')
                try:
                    if int(cl or 0) > 50000:
                        intercepted2.append({'url': u, 'size': int(cl)})
                except Exception:
                    pass

        page.on('response', on_response2)
        try:
            page.goto(
                "https://www.warhammer-community.com/en-gb/age-of-sigmar/",
                wait_until='domcontentloaded',
                timeout=30000
            )
            page.wait_for_timeout(3000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Title: {page.title()!r}")
        print(f"  Large intercepted images ({len(intercepted2)}):")
        for r in sorted(intercepted2, key=lambda x: x['size'], reverse=True)[:5]:
            print(f"    [{r['size']:,} bytes] {r['url']}")

        page.close()

        browser.close()

    print("\nWHC article discovery complete.")


if __name__ == '__main__':
    main()
