"""
Investigate GW product pages and image CDN patterns.
GW product images follow predictable URL patterns based on SKU.
We need to find the right product URL for Skaven/Seraphon units.
"""

import sys
import os
import time
import requests
import json

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def check_url(url, headers, label=""):
    try:
        resp = requests.get(url, headers=headers, timeout=15, stream=True, allow_redirects=True)
        ct = resp.headers.get('content-type', 'unknown')
        cl = resp.headers.get('content-length', '?')
        # Read first 512 bytes
        content_start = b''
        for chunk in resp.iter_content(512):
            content_start = chunk
            break
        # Check if it looks like an image
        is_image = content_start[:3] in [b'\xff\xd8\xff', b'\x89PN', b'GIF'] or content_start[:4] == b'\x89PNG'
        print(f"  [{resp.status_code}] [{ct[:40]}] [{cl} bytes] is_image={is_image} {label}: {url}")
        if not is_image and resp.status_code == 200 and len(content_start) > 0:
            print(f"    content start: {content_start[:100]!r}")
        return resp.status_code == 200 and is_image
    except Exception as exc:
        print(f"  [ERR] {label}: {url} => {exc}")
        return False


def main():
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept': 'image/webp,image/apng,image/*,*/*;q=0.8',
        'Referer': 'https://www.games-workshop.com/',
    }

    print("=== GW Product Image CDN probe ===")
    print("Format: https://www.games-workshop.com/resources/catalog/product/920x950/<SKU>_<Name>.jpg")
    print()

    # Test various patterns for Stormvermin
    # SKU lookup: try the GW product page first
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        intercepted_imgs = []

        def on_response(resp):
            ctype = resp.headers.get('content-type', '')
            u = resp.url
            if 'image' in ctype or any(u.lower().endswith(ext) for ext in ['.jpg', '.png', '.webp']):
                intercepted_imgs.append({'url': u, 'status': resp.status, 'ct': ctype})

        # Check GW product page for Stormvermin
        page = context.new_page()
        page.on('response', on_response)
        print("Loading GW Stormvermin page...")
        try:
            page.goto(
                "https://www.games-workshop.com/en-US/Skaven-Stormvermin-2024",
                wait_until='domcontentloaded',
                timeout=30000
            )
            page.wait_for_timeout(4000)
        except Exception as exc:
            print(f"  [WARN] {exc}")

        print(f"  Intercepted {len(intercepted_imgs)} image responses")
        for r in intercepted_imgs[:15]:
            if r['status'] == 200 and 'catalog/product' in r['url']:
                print(f"    [OK] {r['url']}")

        # Get all product images from DOM
        product_imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img'))
                .map(img => ({
                    src: img.src || img.getAttribute('data-src') || '',
                    srcset: img.getAttribute('srcset') || '',
                    nw: img.naturalWidth, nh: img.naturalHeight,
                    alt: (img.alt || '').substring(0, 80),
                    cls: (img.className || '').substring(0, 100),
                }))
                .filter(i => i.src.length > 10)
        """)

        print(f"\n  DOM images ({len(product_imgs)}):")
        for img in product_imgs:
            if img['nw'] > 100 or 'catalog' in img['src']:
                print(f"    [{img['nw']}x{img['nh']}] {img['src']!r}")
                if img['srcset']:
                    print(f"      srcset: {img['srcset'][:200]!r}")

        # Get page URL (may have redirected)
        final_url = page.url
        print(f"\n  Final URL: {final_url}")
        page.close()

        browser.close()

    print("\n=== Direct GW image URL patterns probe ===")
    # Try some GW URL patterns we might know
    test_urls = [
        ("stormvermin-front", "https://www.games-workshop.com/resources/catalog/product/920x950/99120206005_StormverminFront.jpg"),
        ("stormvermin-nosku", "https://www.games-workshop.com/resources/catalog/product/920x950/SkavenStormvermin.jpg"),
        ("stormvermin-aos4", "https://www.games-workshop.com/resources/catalog/product/920x950/99120206005_AoS4Stormvermin.jpg"),
    ]
    for label, url in test_urls:
        check_url(url, headers, label)
        time.sleep(0.5)


if __name__ == '__main__':
    main()
