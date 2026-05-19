"""
Dump page HTML after JS execution to inspect the DOM structure.
Looks for any patterns related to warscroll images.
"""

import sys
import os
import re
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

URL = "https://wahapedia.ru/aos4/factions/skaven/Stormvermin"


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        page = context.new_page()
        print(f"Loading: {URL}")

        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=30000)
            print("domcontentloaded done, waiting 5s for JS...")
            page.wait_for_timeout(5000)
        except Exception as exc:
            print(f"[WARN] {exc}")

        # Get all img srcs
        imgs = page.evaluate("""
            () => Array.from(document.querySelectorAll('img')).map(img => ({
                src: img.src,
                dataSrc: img.getAttribute('data-src'),
                cls: img.className,
                id: img.id,
                alt: img.alt,
                nw: img.naturalWidth,
                nh: img.naturalHeight,
                parentCls: img.parentElement ? img.parentElement.className : '',
                grandParentCls: (img.parentElement && img.parentElement.parentElement)
                    ? img.parentElement.parentElement.className : '',
            }))
        """)

        print(f"\nTotal imgs found: {len(imgs)}")
        print("\n=== All img tags ===")
        for img in imgs:
            print(f"  src={img['src']!r}")
            if img['dataSrc']:
                print(f"      data-src={img['dataSrc']!r}")
            print(f"      cls={img['cls']!r}  id={img['id']!r}")
            print(f"      natural={img['nw']}x{img['nh']}")
            print(f"      parent={img['parentCls']!r}  grand={img['grandParentCls']!r}")
            print()

        # Look for any background images in CSS
        print("\n=== Elements with background-image (sampled) ===")
        bg_imgs = page.evaluate("""
            () => {
                const result = [];
                const els = document.querySelectorAll('*');
                for (let el of els) {
                    const bg = window.getComputedStyle(el).backgroundImage;
                    if (bg && bg !== 'none' && bg.includes('url(')) {
                        const cls = el.className;
                        const tag = el.tagName;
                        const id_ = el.id;
                        if (!bg.includes('data:')) {
                            result.push({tag, cls, id: id_, bg});
                        }
                    }
                    if (result.length > 20) break;
                }
                return result;
            }
        """)
        for el in bg_imgs:
            print(f"  <{el['tag']}> cls={el['cls']!r} id={el['id']!r} bg={el['bg']!r}")

        # Print a snippet of the body HTML
        print("\n=== Body HTML snippet (first 5000 chars) ===")
        body_html = page.evaluate("() => document.body.innerHTML")
        print(body_html[:5000])

        # Search for 'warscroll' or 'unit' related class names in the whole page
        all_html = page.content()
        print("\n=== Lines containing 'warscroll' or 'img_aos' in page source ===")
        for line in all_html.split('\n'):
            if any(kw in line.lower() for kw in ['warscroll', 'img_aos', 'unit-art', 'miniature']):
                print(f"  {line.strip()[:200]}")

        page.close()
        browser.close()


if __name__ == '__main__':
    main()
