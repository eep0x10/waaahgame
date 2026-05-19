"""
Deep-dive into Wahapedia page structure looking for unit art.
Checks background-images on ALL elements (not just 20), and looks at
the picSearch element specifically. Also checks the unit listing page
which may have thumbnails.
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WARSCROLL_URL = "https://wahapedia.ru/aos4/factions/skaven/Stormvermin"
FACTION_URL = "https://wahapedia.ru/aos4/factions/skaven/"
WARSCROLLS_URL = "https://wahapedia.ru/aos4/factions/skaven/warscrolls.html"


def probe_page(page, url, label):
    print(f"\n{'='*70}")
    print(f"  {label}: {url}")
    print('='*70)

    try:
        page.goto(url, wait_until='domcontentloaded', timeout=30000)
        page.wait_for_timeout(4000)
    except Exception as exc:
        print(f"  [WARN] {exc}")

    # All background-image urls
    bg_imgs = page.evaluate("""
        () => {
            const result = new Set();
            for (const el of document.querySelectorAll('*')) {
                const bg = window.getComputedStyle(el).backgroundImage;
                if (bg && bg !== 'none' && bg.includes('url(') && !bg.includes('data:')) {
                    const matches = bg.match(/url\(["']?([^"')]+)["']?\)/g);
                    if (matches) {
                        for (const m of matches) {
                            const u = m.replace(/url\(["']?|["']?\)$/g, '');
                            if (!u.includes('data:')) result.add(u);
                        }
                    }
                }
            }
            return Array.from(result);
        }
    """)
    print(f"\n--- All background-image URLs ({len(bg_imgs)}) ---")
    for u in bg_imgs:
        # Highlight anything that looks like unit art
        flag = " <<<<" if any(kw in u.lower() for kw in ['unit', 'warscroll', 'miniature', 'pic', 'model', 'thumb']) else ""
        print(f"  {u}{flag}")

    # Check picSearch element
    print("\n--- picSearch element ---")
    pic_search = page.query_selector('.picSearch')
    if pic_search:
        bg = page.evaluate("(el) => window.getComputedStyle(el).backgroundImage", pic_search)
        href = pic_search.get_attribute('href') or pic_search.get_attribute('onclick') or "(none)"
        print(f"  bg={bg!r}")
        print(f"  href/onclick={href!r}")
        inner = pic_search.inner_html()
        print(f"  innerHTML={inner[:300]!r}")
    else:
        print("  (not found)")

    # Check datasheet area more carefully
    print("\n--- datasheet div area ---")
    ds = page.query_selector('.datasheet')
    if ds:
        html = ds.inner_html()
        # Find all src and data-src in there
        srcs = re.findall(r'(?:src|data-src)=["\']([^"\']+)["\']', html)
        print(f"  imgs in .datasheet: {srcs}")
        bgs = re.findall(r'background(?:-image)?:[^;]*url\(["\']?([^"\')\s]+)["\']?\)', html)
        print(f"  bg imgs in .datasheet: {bgs}")
    else:
        print("  (not found)")

    # Print all class names on divs that exist in the page
    print("\n--- Unique div class names containing 'pic', 'img', 'art', 'unit', 'model', 'photo' ---")
    cls_names = page.evaluate("""
        () => {
            const seen = new Set();
            for (const el of document.querySelectorAll('[class]')) {
                for (const c of el.className.split(' ')) {
                    if (/pic|img|art|unit|model|photo|thumb|warscroll/i.test(c)) {
                        seen.add(c);
                    }
                }
            }
            return Array.from(seen);
        }
    """)
    print(f"  {cls_names}")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        probe_page(page, WARSCROLL_URL, "WARSCROLL")
        page.close()

        page = context.new_page()
        probe_page(page, WARSCROLLS_URL, "WARSCROLLS LIST")
        page.close()

        browser.close()

    print("\nDeep discovery complete.")


if __name__ == '__main__':
    main()
