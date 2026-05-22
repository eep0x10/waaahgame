"""Crawl ageofsigmar.lexicanum.com via playwright to collect unit pages + main image URLs.

Stage 1: list_of_units page → per-faction sections → unit page URLs (saved to manifest_units.json)
Stage 2: each unit page → main infobox image URL (added to manifest)
Stage 3: download all images (separate step: lexicanum_download.py)

Usage:
    python scripts/lexicanum_crawl.py --stage links
    python scripts/lexicanum_crawl.py --stage images
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

from patchright.sync_api import sync_playwright, TimeoutError as PWTimeout

BASE = "https://ageofsigmar.lexicanum.com"
LIST_URL = f"{BASE}/wiki/List_of_units"
MANIFEST = Path(__file__).parent / "cache" / "lexicanum_manifest.json"
DELAY = 2.0  # polite delay between page navigations

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

CF_CLEARANCE = "y.Lm86XmyGBRLrjEYFfytqMBrFDTbGmGCDt8_OG7730-1779197359-1.2.1.1-qiigLHLoMlBf4PNf7mJJuCwgsj.YH4hhJtI0EkPIn2470YJWQnoal6JZjIpN.brfL2uEkHLuaI.1vQoZVhLyASMWptIKPHE65tdK7rs0_MU80EgDjLbl8yEU2nL7a0W2HFfxe9D3Mo9qb_ydrTHugTkwcvpK0kNSArN_2.7GLDX7Xzuvm31MZNGi4QGhW22S7rOt7j1Y7H_ZUUl1q5FinCXCkwGWQV18k6AlXKS5Z4202Rxtept5AKKpw90TyH.UBEyXXvly20QJmsL8mHTE5XfZ4H6hW305va53jjSaEd39b.J2eKxpdshO3EullaO3JezAL2sG57yE_v.YZTqcSTZYuh0L3GITJUILr7gcsc7ouV72ZwUErqP_8VX2ukdSRuTbx3MnsPNn0GXh5EUYDh8D6N.iL6aYPDXHVApuIV8"


def load_manifest() -> dict:
    if MANIFEST.exists():
        return json.loads(MANIFEST.read_text(encoding="utf-8"))
    return {"factions": {}, "units": {}}


def save_manifest(m: dict) -> None:
    MANIFEST.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST.write_text(json.dumps(m, indent=2, ensure_ascii=False), encoding="utf-8")


def slug_from_href(href: str) -> str:
    # /wiki/Foo_Bar → foo-bar
    name = href.rsplit("/", 1)[-1]
    name = unquote(name).replace("_", " ").strip()
    return re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")


def stage_links(page) -> dict:
    print(f"[stage_links] fetching {LIST_URL}", flush=True)
    page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
    print("[stage_links] Waiting for #mw-content-text (cookie should bypass CF)...", flush=True)
    page.wait_for_selector("#mw-content-text", timeout=30000)

    # Lexicanum List_of_units organizes by faction headings (h2/h3) with subsequent ul of unit links.
    # Strategy: walk every h2/h3 then collect anchor links until next heading.
    data = page.evaluate(
        """
        () => {
          const content = document.querySelector('#mw-content-text') || document.querySelector('.mw-parser-output');
          if (!content) return {factions: {}, _err: 'no content'};
          // Walk top-level children of mw-parser-output
          const root = content.querySelector('.mw-parser-output') || content;
          const factions = {};
          let current = null;
          for (const el of root.children) {
            const tag = el.tagName;
            if (tag === 'H2' || tag === 'H3') {
              const span = el.querySelector('.mw-headline');
              const name = (span ? span.textContent : el.textContent).trim();
              if (!name) continue;
              if (['Contents','See also','References','External links','Notes','Sources'].includes(name)) {
                current = null;
                continue;
              }
              current = name;
              if (!factions[current]) factions[current] = [];
            } else if (current && (tag === 'UL' || tag === 'DIV' || tag === 'P')) {
              const links = el.querySelectorAll('a[href^="/wiki/"]');
              links.forEach(a => {
                const href = a.getAttribute('href');
                if (!href) return;
                if (href.includes(':')) return; // skip File:, Category:, etc.
                if (href.endsWith('redlink=1')) return;
                if (a.classList.contains('new')) return; // missing page
                const title = a.getAttribute('title') || a.textContent.trim();
                factions[current].push({href, title});
              });
            }
          }
          return {factions};
        }
        """
    )

    if "_err" in data:
        raise RuntimeError(f"crawl failed: {data['_err']}")

    factions = data["factions"]
    # Deduplicate per faction
    units_index: dict[str, dict] = {}
    cleaned = {}
    for fname, items in factions.items():
        seen = set()
        out = []
        for it in items:
            h = it["href"]
            if h in seen:
                continue
            seen.add(h)
            slug = slug_from_href(h)
            out.append({"href": h, "title": it["title"], "slug": slug, "faction": fname})
            units_index[slug] = {
                "href": h,
                "title": it["title"],
                "faction": fname,
                "url": urljoin(BASE, h),
            }
        if out:
            cleaned[fname] = out

    print(f"[stage_links] factions: {len(cleaned)}, units: {len(units_index)}", flush=True)
    return {"factions": cleaned, "units": units_index}


def extract_main_image(page) -> str | None:
    """Find the main image on a unit page: prefer infobox image, fall back to first content img."""
    return page.evaluate(
        """
        () => {
          const root = document.querySelector('.mw-parser-output') || document.body;
          // Try infobox image first (table.infobox img, or first thumb)
          const candidates = [
            'table.infobox img',
            'table.infoboxtable img',
            '.thumbinner img',
            '.thumb img',
            'figure img',
            'img.thumbimage',
          ];
          for (const sel of candidates) {
            const img = root.querySelector(sel);
            if (img && img.src && !img.src.includes('data:image')) {
              // Prefer full file from File: link if parent <a> exists
              const parent = img.closest('a');
              if (parent && parent.href && parent.href.includes('/wiki/File:')) {
                return {thumb: img.src, file_href: parent.href, alt: img.alt || ''};
              }
              return {thumb: img.src, file_href: null, alt: img.alt || ''};
            }
          }
          return null;
        }
        """
    )


def stage_images(page, manifest: dict) -> dict:
    units = manifest.get("units", {})
    if not units:
        raise RuntimeError("no units in manifest — run stage links first")

    todo = [(s, u) for s, u in units.items() if "image" not in u]
    print(f"[stage_images] {len(todo)} of {len(units)} units need image lookup", flush=True)

    for i, (slug, u) in enumerate(todo, 1):
        try:
            page.goto(u["url"], wait_until="domcontentloaded", timeout=45000)
            page.wait_for_selector("#mw-content-text", timeout=15000)
            img = extract_main_image(page)
            if img:
                u["image"] = img
                # If we have file_href, resolve to full-res via separate page later (cheaper: just save the thumb URL — many sites have 'orig' upload path)
                # Lexicanum thumbs follow pattern /mediawiki/images/thumb/<a>/<b>/<file>/<NNNpx-file>
                # Full original is at /mediawiki/images/<a>/<b>/<file>
                thumb = img["thumb"]
                m = re.match(r"(.*)/thumb/([^/]+/[^/]+/[^/]+)/\d+px-[^/]+$", thumb)
                if m:
                    u["image"]["full"] = f"{m.group(1)}/{m.group(2)}"
                else:
                    u["image"]["full"] = thumb
            else:
                u["image"] = None
            if i % 10 == 0 or i == len(todo):
                print(f"[stage_images] {i}/{len(todo)} ({slug})", flush=True)
                save_manifest(manifest)
        except PWTimeout:
            print(f"[stage_images] TIMEOUT {slug}", flush=True)
            u["image"] = {"error": "timeout"}
        except Exception as e:
            print(f"[stage_images] FAIL {slug}: {e}", flush=True)
            u["image"] = {"error": str(e)}
        time.sleep(DELAY)

    save_manifest(manifest)
    return manifest


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--stage", choices=["links", "images", "both"], default="both")
    ap.add_argument("--headed", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="limit unit pages crawled (testing)")
    args = ap.parse_args()

    manifest = load_manifest()

    profile_dir = Path(__file__).parent / "cache" / "lexicanum_profile"
    profile_dir.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(profile_dir),
            headless=not args.headed,
            user_agent=UA,
            viewport={"width": 1366, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        # Inject cf_clearance cookie before any navigation (bypass CF challenge)
        context.add_cookies([{
            "name": "cf_clearance",
            "value": CF_CLEARANCE,
            "domain": ".lexicanum.com",
            "path": "/",
            "httpOnly": True,
            "secure": True,
            "sameSite": "None",
        }])

        page = context.pages[0] if context.pages else context.new_page()

        if args.stage in ("links", "both"):
            result = stage_links(page)
            # Merge: keep prior images if any
            for slug, u in result["units"].items():
                if slug in manifest.get("units", {}):
                    prior = manifest["units"][slug]
                    if "image" in prior:
                        u["image"] = prior["image"]
            manifest["factions"] = result["factions"]
            manifest["units"] = result["units"]
            save_manifest(manifest)
            print(f"[main] manifest saved: {MANIFEST}", flush=True)

        if args.stage in ("images", "both"):
            if args.limit:
                kept = dict(list(manifest["units"].items())[: args.limit])
                test_manifest = {"factions": manifest["factions"], "units": kept}
                stage_images(page, test_manifest)
                # write back the subset's images into full manifest
                for k, v in test_manifest["units"].items():
                    manifest["units"][k] = v
                save_manifest(manifest)
            else:
                stage_images(page, manifest)

        context.close()


if __name__ == "__main__":
    main()
