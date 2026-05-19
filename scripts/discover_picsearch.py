"""
Investigate the picSearch element behavior on Wahapedia.
Also tries to extract unit art from network requests intercepted during page load.
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

URL = "https://wahapedia.ru/aos4/factions/skaven/Stormvermin"


def main():
    from playwright.sync_api import sync_playwright

    intercepted_images = []

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        context = browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Intercept network requests to capture any image requests
        page = context.new_page()

        def on_request(request):
            url = request.url
            if any(ext in url.lower() for ext in ['.jpg', '.jpeg', '.png', '.webp', '.gif']):
                # Only capture non-tiny things
                intercepted_images.append(url)

        page.on('request', on_request)

        print(f"Loading: {URL}")
        try:
            page.goto(URL, wait_until='domcontentloaded', timeout=30000)
            page.wait_for_timeout(5000)
        except Exception as exc:
            print(f"[WARN] {exc}")

        print(f"\n--- All image requests intercepted ({len(intercepted_images)}) ---")
        for u in intercepted_images:
            print(f"  {u}")

        # Inspect picSearch HTML
        print("\n--- picSearch element details ---")
        pic_search_els = page.query_selector_all('.picSearch, [class*="picSearch"], .tooltip.picSearch')
        print(f"Found {len(pic_search_els)} picSearch elements")
        for el in pic_search_els[:3]:
            outer = el.evaluate("el => el.outerHTML")
            print(f"  outerHTML: {outer[:500]!r}")

        # Check the JS source for picSearch function
        print("\n--- Searching page scripts for 'picSearch' ---")
        script_content = page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script'));
                const results = [];
                for (const s of scripts) {
                    const src = s.src;
                    const txt = s.textContent;
                    if (txt && txt.includes('picSearch')) {
                        results.push({ type: 'inline', snippet: txt.substring(txt.indexOf('picSearch') - 50, txt.indexOf('picSearch') + 300) });
                    }
                    if (src && src.includes('picSearch')) {
                        results.push({ type: 'src', src: src });
                    }
                }
                return results;
            }
        """)
        for r in script_content:
            print(f"  [{r['type']}] {r.get('snippet', r.get('src', ''))!r}")

        # Search all script text for image URL patterns
        print("\n--- Searching inline scripts for unit image URLs ---")
        img_refs = page.evaluate("""
            () => {
                const scripts = Array.from(document.querySelectorAll('script'));
                const results = [];
                const re = /https?:\/\/[^\s"'<>]+\.(?:jpg|jpeg|png|webp)/gi;
                for (const s of scripts) {
                    const txt = s.textContent || '';
                    const matches = txt.match(re);
                    if (matches) {
                        for (const m of matches) {
                            results.push(m);
                        }
                    }
                }
                // Also check data attributes
                for (const el of document.querySelectorAll('[data-img],[data-image],[data-src],[data-url]')) {
                    const v = el.dataset.img || el.dataset.image || el.dataset.src || el.dataset.url;
                    if (v) results.push(v);
                }
                return results;
            }
        """)
        print(f"Found {len(img_refs)} image URL refs in scripts/data attrs:")
        for u in img_refs[:20]:
            print(f"  {u}")

        # Check what the page title says (unit name)
        title = page.title()
        print(f"\n--- Page title: {title!r} ---")

        # Check the full picSearch onclick/tooltip content
        print("\n--- Full picSearch tooltip/onclick ---")
        pic_el = page.query_selector('.picSearch')
        if pic_el:
            outer = pic_el.evaluate("el => el.outerHTML")
            print(f"  outerHTML: {outer[:1000]!r}")
            # Get nearby anchor elements
            parent_html = pic_el.evaluate("el => el.parentElement ? el.parentElement.outerHTML : 'no parent'")
            print(f"  parent outerHTML: {parent_html[:1000]!r}")

        page.close()
        browser.close()

    print("\nPicSearch investigation complete.")


if __name__ == '__main__':
    main()
