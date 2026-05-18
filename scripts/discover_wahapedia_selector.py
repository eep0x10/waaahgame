"""
Discovery script: load two Wahapedia warscroll pages with Playwright,
print all <img> tags whose natural dimensions are >300x300 (or have no
dimensions in the HTML but appear after JS execution), and identify
which CSS selectors resolve to the warscroll unit art.

Usage:
  python scripts/discover_wahapedia_selector.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

URLS = [
    ("skaven",    "https://wahapedia.ru/aos4/factions/skaven/Stormvermin"),
    ("seraphon",  "https://wahapedia.ru/aos4/factions/seraphon/Saurus-Warriors"),
]

CANDIDATE_SELECTORS = [
    "img.warscroll-pic",
    ".WarscrollPic img",
    ".warscroll-pic img",
    "img[src*='img_aos/']",
    ".warscroll-art img",
    "img[class*='warscroll']",
    "img[class*='Warscroll']",
    ".warscroll img",
    ".unit-art img",
    "[class*='pic'] img",
    "[class*='Pic'] img",
    "img[src*='/img/']",
]


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="waaahgame/0.2 (educational)"
        )

        for label, url in URLS:
            print(f"\n{'='*70}")
            print(f"  {label.upper()}: {url}")
            print('='*70)

            page = context.new_page()
            try:
                page.goto(url, wait_until='networkidle', timeout=30000)
            except Exception as exc:
                print(f"  [WARN] networkidle timed out: {exc}")
                try:
                    page.goto(url, wait_until='domcontentloaded', timeout=30000)
                    page.wait_for_timeout(3000)
                except Exception as exc2:
                    print(f"  [ERROR] page load failed: {exc2}")
                    page.close()
                    continue

            print("\n--- Candidate selector probe ---")
            for sel in CANDIDATE_SELECTORS:
                try:
                    elements = page.query_selector_all(sel)
                    if elements:
                        for el in elements[:3]:
                            src = el.get_attribute('src') or el.get_attribute('data-src') or '(no src)'
                            natural_size = page.evaluate(
                                "(el) => ({ w: el.naturalWidth, h: el.naturalHeight, "
                                "cw: el.clientWidth, ch: el.clientHeight })",
                                el
                            )
                            print(f"  MATCH [{sel}] src={src!r} "
                                  f"natural={natural_size['w']}x{natural_size['h']} "
                                  f"client={natural_size['cw']}x{natural_size['ch']}")
                    else:
                        print(f"  no match: {sel}")
                except Exception as exc:
                    print(f"  error [{sel}]: {exc}")

            print("\n--- All imgs (natural size > 200x200) ---")
            try:
                large_imgs = page.evaluate("""
                    () => {
                        const imgs = Array.from(document.querySelectorAll('img'));
                        return imgs
                            .map(img => ({
                                src: img.src || img.getAttribute('data-src') || '',
                                nw: img.naturalWidth,
                                nh: img.naturalHeight,
                                cw: img.clientWidth,
                                ch: img.clientHeight,
                                cls: img.className,
                                id_: img.id,
                                alt: img.alt,
                                parentCls: img.parentElement ? img.parentElement.className : '',
                            }))
                            .filter(i => i.nw > 200 || i.cw > 200);
                    }
                """)
                if large_imgs:
                    for img in large_imgs:
                        print(f"  src={img['src']!r}")
                        print(f"      cls={img['cls']!r}  id={img['id_']!r}  alt={img['alt']!r}")
                        print(f"      parent_cls={img['parentCls']!r}")
                        print(f"      natural={img['nw']}x{img['nh']}  client={img['cw']}x{img['ch']}")
                        print()
                else:
                    print("  (no large images found after JS — page may be blocking headless)")
            except Exception as exc:
                print(f"  [ERROR] evaluating imgs: {exc}")

            print("\n--- og:image / twitter:image ---")
            try:
                og = page.query_selector('meta[property="og:image"]')
                tw = page.query_selector('meta[name="twitter:image"]')
                print(f"  og:image  = {og.get_attribute('content') if og else None}")
                print(f"  tw:image  = {tw.get_attribute('content') if tw else None}")
            except Exception as exc:
                print(f"  [ERROR] meta tags: {exc}")

            page.close()
            time.sleep(1)

        browser.close()

    print("\nDiscovery complete.")


if __name__ == '__main__':
    main()
