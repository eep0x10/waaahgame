"""
Final source investigation:
1. Wahapedia PDF export - does it embed unit art?
2. Check if Wahapedia has img_aos images at all (maybe older units)
3. Try Wahapedia with longer waits and scroll interaction
4. Check Warhammer40k wiki (which covers AoS too sometimes)
5. Check the official Age of Sigmar app or old wahapedia images
"""

import sys
import os
import time
import requests

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Referer': 'https://wahapedia.ru/',
}


def main():
    # Probe various image paths on Wahapedia
    print("=== Wahapedia image paths probe ===")

    # From the old 40K version, Wahapedia sometimes used img_40k/
    # and warscroll PDF images embedded. Try various paths.
    test_urls = [
        # AoS4 faction unit images
        "https://wahapedia.ru/aos4/factions/skaven/img/Stormvermin.jpg",
        "https://wahapedia.ru/aos4/factions/skaven/img/stormvermin.jpg",
        "https://wahapedia.ru/aos4/factions/skaven/img_units/Stormvermin.jpg",
        "https://wahapedia.ru/aos4/img_warscrolls/Stormvermin.jpg",
        "https://wahapedia.ru/aos4/img_warscrolls/SKN_Stormvermin.jpg",

        # Check if there's an API endpoint for unit info
        "https://wahapedia.ru/aos4/factions/skaven/Stormvermin.json",

        # PDFs
        "https://wahapedia.ru/aos4/factions/skaven/Stormvermin.pdf",

        # Maybe the img is loaded via a different base path
        "https://wahapedia.ru/img/aos4/skaven/Stormvermin.jpg",
        "https://wahapedia.ru/img/aos4/Stormvermin.jpg",

        # Old AoS3 style
        "https://wahapedia.ru/age-of-sigmar3ed/img_aos/Stormvermin.jpg",

        # Maybe there's a CDN
        "https://cdn.wahapedia.ru/aos4/img_aos/Stormvermin.jpg",
        "https://static.wahapedia.ru/img/Stormvermin.jpg",
    ]

    for url in test_urls:
        try:
            resp = requests.head(url, headers=HEADERS, timeout=8, allow_redirects=True)
            ct = resp.headers.get('content-type', '?')
            cl = resp.headers.get('content-length', '?')
            status = resp.status_code
            flag = " <<< IMAGE!" if ('image' in ct and status == 200) else ""
            print(f"  [{status}] [{ct[:30]}] [{cl:>8}] {url}{flag}")
        except Exception as exc:
            print(f"  [ERR] {url}: {exc}")
        time.sleep(0.3)

    # Try the Wahapedia print version which sometimes has different assets
    print("\n=== Wahapedia print/PDF page probe ===")
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            # Simulate print media
        )

        # Intercept ALL requests to find any image requests to Wahapedia
        all_wahapedia_reqs = []

        page = context.new_page()

        def on_req(req):
            u = req.url
            if 'wahapedia' in u and any(u.lower().endswith(e) for e in ['.jpg', '.png', '.jpeg', '.webp']):
                all_wahapedia_reqs.append(u)

        page.on('request', on_req)

        # Load with scroll to trigger lazy loading
        print("Loading Stormvermin page with scrolling...")
        try:
            page.goto("https://wahapedia.ru/aos4/factions/skaven/Stormvermin", wait_until='domcontentloaded', timeout=30000)
            # Scroll through page
            for i in range(5):
                page.evaluate(f"window.scrollBy(0, {(i+1)*500})")
                page.wait_for_timeout(800)
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(2000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Wahapedia image requests: {all_wahapedia_reqs}")

        # Check all img elements with data attributes
        all_imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img, [data-src], [data-bg], [data-lazy]'))
                .map(el => ({
                    src: el.src || '',
                    dataSrc: el.getAttribute('data-src') || '',
                    dataBg: el.getAttribute('data-bg') || '',
                    dataLazy: el.getAttribute('data-lazy') || '',
                    cls: (el.className || '').substring(0, 80),
                    id: el.id || '',
                }))
                .filter(el => el.dataSrc || el.dataBg || el.dataLazy ||
                              (el.src && el.src.includes('wahapedia')))
        """)
        print(f"  DOM elements with lazy-load attrs: {len(all_imgs)}")
        for el in all_imgs[:10]:
            print(f"    src={el['src'][:80]!r}")
            print(f"      data-src={el['dataSrc']!r}  data-bg={el['dataBg']!r}")

        page.close()
        browser.close()

    print("\nFinal source investigation complete.")


if __name__ == '__main__':
    main()
