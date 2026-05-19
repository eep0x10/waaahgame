"""
Check warhammer.com for product images.
GW redirected to https://www.warhammer.com/shop/Skaven-Stormvermin-2024
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

        intercepted = []

        def on_response(resp):
            ctype = resp.headers.get('content-type', '')
            u = resp.url
            if ('image' in ctype or any(u.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp'])) and resp.status == 200:
                cl = resp.headers.get('content-length', '0')
                try:
                    if int(cl) > 10000:  # > 10KB - skip tiny stuff
                        intercepted.append({'url': u, 'size': cl, 'ct': ctype})
                except Exception:
                    pass

        page = context.new_page()
        page.on('response', on_response)

        print("Loading warhammer.com Stormvermin product page...")
        try:
            page.goto(
                "https://www.warhammer.com/shop/Skaven-Stormvermin-2024",
                wait_until='domcontentloaded',
                timeout=30000
            )
            page.wait_for_timeout(5000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"\nFinal URL: {page.url}")
        print(f"Page title: {page.title()}")

        print(f"\nIntercepted large images ({len(intercepted)}):")
        for r in intercepted:
            print(f"  [{r['size']} bytes] {r['url']}")

        print("\nDOM large images:")
        imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img'))
                .map(img => ({
                    src: img.src || img.getAttribute('data-src') || img.getAttribute('data-lazy-src') || '',
                    srcset: (img.getAttribute('srcset') || '').substring(0, 200),
                    nw: img.naturalWidth, nh: img.naturalHeight,
                    alt: (img.alt || '').substring(0, 100),
                    cls: (img.className || '').substring(0, 100),
                    id: img.id || '',
                }))
                .filter(i => i.src.length > 5)
        """)
        for img in imgs:
            print(f"  [{img['nw']}x{img['nh']}] {img['src'][:100]!r}")
            print(f"      alt={img['alt']!r}  cls={img['cls']!r}")

        # Get first 3000 chars of body HTML
        body = page.evaluate("() => document.body ? document.body.innerHTML.substring(0, 5000) : 'no body'")
        print(f"\nBody HTML snippet:\n{body[:3000]}")

        page.close()
        browser.close()


if __name__ == '__main__':
    main()
