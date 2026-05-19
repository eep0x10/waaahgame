"""
Warhammer Community has unit showcase/preview articles with high-quality images.
Also checking the WH Community search and the old/new Citadel miniature pages.

The pattern for WHC is: search for faction + unit name, find the warscroll reveal article.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def probe(page, url, label, wait_ms=5000, min_size=30000):
    print(f"\n{'='*70}")
    print(f"  {label}: {url}")
    print('='*70)

    intercepted = []

    def on_response(resp):
        u = resp.url
        ctype = resp.headers.get('content-type', '')
        if resp.status == 200 and ('image' in ctype or any(u.lower().endswith(e) for e in ['.jpg', '.jpeg', '.png', '.webp'])):
            cl = resp.headers.get('content-length', '0')
            try:
                sz = int(cl or 0)
                if sz > min_size:
                    intercepted.append({'url': u, 'size': sz, 'ct': ctype})
            except Exception:
                pass

    page.on('response', on_response)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(wait_ms)
    except Exception as exc:
        print(f"  [WARN] {exc}")

    print(f"  Title: {page.title()!r}")
    print(f"  URL: {page.url}")
    print(f"  Intercepted large images: {len(intercepted)}")
    for r in intercepted[:5]:
        print(f"    [{r['size']:,} bytes] {r['url']}")

    imgs = page.evaluate("""
        () => Array.from(document.querySelectorAll('img'))
            .filter(i => i.naturalWidth > 200 && i.naturalHeight > 200)
            .map(i => ({src: i.src, nw: i.naturalWidth, nh: i.naturalHeight, alt: (i.alt||'').substring(0,80)}))
    """)
    print(f"  Large DOM imgs: {len(imgs)}")
    for img in imgs[:5]:
        print(f"    [{img['nw']}x{img['nh']}] {img['src'][:120]!r} alt={img['alt']!r}")

    page.remove_listener('response', on_response)
    return intercepted


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # WHC search for Stormvermin
        page = context.new_page()
        probe(page, "https://www.warhammer-community.com/en-gb/?s=Stormvermin+skaven+warscroll", "WHC SEARCH")
        page.close()

        # Wahapedia faction INDEX page - maybe there's a gallery
        page = context.new_page()
        probe(page, "https://wahapedia.ru/aos4/", "WAHAPEDIA HOME", min_size=50000)
        page.close()

        # Try Miniwars.eu or Spikeybits - fan sites often have unit art
        page = context.new_page()
        r = probe(page, "https://spikeybits.com/?s=Stormvermin+AOS+warscroll", "SPIKEYBITS SEARCH", min_size=20000)
        page.close()

        # Bell of Lost Souls
        page = context.new_page()
        probe(page, "https://www.belloflostsouls.net/?s=Stormvermin+Age+of+Sigmar", "BOLS SEARCH", min_size=20000)
        page.close()

        # Age of Sigmar Community Discord forum / The Honest Wargamer
        # Actually - let's try the Warhammer Community unit showcase search
        page = context.new_page()
        probe(page, "https://www.warhammer-community.com/en-gb/search/?q=Stormvermin", "WHC SEARCH 2", min_size=20000)
        page.close()

        browser.close()

    print("\nWHC unit images discovery complete.")


if __name__ == '__main__':
    main()
