"""lex_refresh_cookie.py — Launch HEADED browser to obtain fresh cf_clearance + __cf_bm
cookies for ageofsigmar.lexicanum.com.

The browser opens visibly so the user can solve any Cloudflare challenge / CAPTCHA
manually. Once the page title element (h1) appears, cookies are dumped to
scripts/_cache/lex_session.json and the browser closes.

Usage (HOST machine only — needs display):
    python scripts/lex_refresh_cookie.py
"""
from __future__ import annotations

import json
import sys
import time
from pathlib import Path

try:
    from patchright.sync_api import sync_playwright, TimeoutError as PWTimeout
except ImportError:
    from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout  # type: ignore

LIST_URL = "https://ageofsigmar.lexicanum.com/wiki/List_of_units"
OUT_FILE = Path(__file__).parent / "_cache" / "lex_session.json"
PROFILE_DIR = Path(__file__).parent / "cache" / "lexicanum_profile"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"

MAX_WAIT_SECONDS = 240


def main() -> int:
    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    PROFILE_DIR.mkdir(parents=True, exist_ok=True)

    print("[lex_refresh_cookie] Launching HEADED browser. Window will open.")
    print("[lex_refresh_cookie] If a Cloudflare challenge appears, solve it manually.")
    print(f"[lex_refresh_cookie] Waiting up to {MAX_WAIT_SECONDS}s for page to load.")

    with sync_playwright() as p:
        context = p.chromium.launch_persistent_context(
            user_data_dir=str(PROFILE_DIR),
            headless=False,
            user_agent=UA,
            viewport={"width": 1366, "height": 900},
            args=["--disable-blink-features=AutomationControlled"],
        )
        page = context.pages[0] if context.pages else context.new_page()

        try:
            page.goto(LIST_URL, wait_until="domcontentloaded", timeout=60000)
        except PWTimeout:
            print("[lex_refresh_cookie] initial domcontentloaded timed out, continuing to poll")

        # Poll until #mw-content-text appears AND a Lexicanum-specific element
        # ("#firstHeading" → MediaWiki page title) exists. CF challenge sets h1 to
        # the host name; once we're through, MediaWiki renders firstHeading.
        start = time.time()
        title_text = ""
        ok = False
        while time.time() - start < MAX_WAIT_SECONDS:
            try:
                fh = page.query_selector("#firstHeading")
                if fh:
                    title_text = (fh.text_content() or "").strip()
                if title_text and page.query_selector("#mw-content-text"):
                    ok = True
                    break
                # Also accept presence of MediaWiki body class .mw-body
                if page.query_selector(".mw-body") and page.query_selector("#mw-content-text"):
                    fh2 = page.query_selector("#firstHeading")
                    if fh2:
                        title_text = (fh2.text_content() or "").strip()
                    else:
                        title_text = "(mw-body present)"
                    ok = True
                    break
            except Exception:
                pass
            time.sleep(1.5)

        if not ok:
            print(f"[lex_refresh_cookie] FAIL: MediaWiki content never loaded in {MAX_WAIT_SECONDS}s (last title={title_text!r})")
            context.close()
            return 1

        print(f"[lex_refresh_cookie] Page ready (title={title_text!r}). Reading cookies...")

        cookies = context.cookies()
        relevant = {}
        for c in cookies:
            if c.get("name") in ("cf_clearance", "__cf_bm", "cf_chl_2", "cf_chl_3"):
                relevant[c["name"]] = c["value"]

        if "cf_clearance" not in relevant:
            print(f"[lex_refresh_cookie] WARN: cf_clearance not found in cookies (got {list(relevant.keys())})")

        payload = {
            "user_agent": UA,
            "cookies": relevant,
            "all_cookies": [
                {k: v for k, v in c.items() if k in ("name", "value", "domain", "path")}
                for c in cookies if c.get("domain", "").endswith("lexicanum.com")
            ],
            "title": title_text,
            "saved_at": int(time.time()),
        }

        OUT_FILE.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"[lex_refresh_cookie] Cookie saved to {OUT_FILE}")
        print(f"[lex_refresh_cookie] Cookies captured: {list(relevant.keys())}")

        context.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
