"""
Fetch missing Stormcast Eternals unit images from WHC og:image of confirmed articles.
Synchronous, polite. JPEG q85, max 600w. Validate >=200x200 and >=8KB.
Only saves units we have a confirmed article match for; reports the rest as unsourced.
"""

import io
import os
import sys
import time

import requests
from bs4 import BeautifulSoup
from PIL import Image

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

OUT_DIR = "/app/app/static/img/units/stormcast-eternals"
MIN_BYTES = 8000
MIN_W = 200
MIN_H = 200
MAX_W = 600
JPEG_Q = 85

# unit slug -> direct WHC article URL (og:image confirmed showing matching unit)
TARGETS = {
    "yndrasta-the-celestial-spear": "https://www.warhammer-community.com/en-gb/articles/NQcVsLZ4/think-your-boss-is-weird-new-stormcast-eternals-leader-yndrasta-collects-severed-heads/",
    "annihilators": "https://www.warhammer-community.com/en-gb/articles/S7JGVjJG/dominion-brings-mighty-paladins-to-the-mortal-realms-none-shall-pass-the-stormcast-eternals-annihilators/",
    "vindictors": "https://www.warhammer-community.com/en-gb/articles/x6bC3d5Q/dominion-40-years-of-warhammer-confined-to-a-single-box/",
}

# no confirmed article located via WHC sitemap / search
UNAVAILABLE = [
    "praetors",
    "knight-vexillor-with-banner-of-apotheosis",
    "vanguard-raptors-with-longstrike-crossbows",
]


def extract_og_image(html: str):
    soup = BeautifulSoup(html, "html.parser")
    for sel in [
        {"property": "og:image"},
        {"name": "og:image"},
        {"name": "twitter:image"},
        {"property": "twitter:image"},
    ]:
        m = soup.find("meta", attrs=sel)
        if m and m.get("content"):
            return m["content"]
    return None


def download(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=25)
        if r.status_code == 200 and len(r.content) >= MIN_BYTES:
            return r.content
        print(f"  [skip] status={r.status_code} size={len(r.content)} {url}")
    except Exception as exc:
        print(f"  [err download] {exc}")
    return None


def save_jpeg(img_bytes: bytes, out_path: str) -> bool:
    try:
        im = Image.open(io.BytesIO(img_bytes))
        im.load()
    except Exception as exc:
        print(f"  [bad image] {exc}")
        return False
    w, h = im.size
    if w < MIN_W or h < MIN_H:
        print(f"  [too small] {w}x{h}")
        return False
    if im.mode not in ("RGB", "L"):
        im = im.convert("RGB")
    if w > MAX_W:
        new_h = int(h * MAX_W / w)
        im = im.resize((MAX_W, new_h), Image.LANCZOS)
    im.save(out_path, "JPEG", quality=JPEG_Q, optimize=True)
    sz = os.path.getsize(out_path)
    print(f"  [SAVED] {out_path} {im.size[0]}x{im.size[1]} {sz:,}B")
    return True


def fetch_unit(slug: str, article_url: str) -> bool:
    print(f"\n=== {slug} ===")
    print(f"  article: {article_url}")
    try:
        r = requests.get(article_url, headers=HEADERS, timeout=25)
    except Exception as exc:
        print(f"  [err article] {exc}")
        return False
    if r.status_code != 200:
        print(f"  [bad status] {r.status_code}")
        return False
    og = extract_og_image(r.text)
    if not og:
        print(f"  [no og:image]")
        return False
    print(f"  og:image: {og}")
    time.sleep(0.7)
    blob = download(og)
    if not blob:
        return False
    out = os.path.join(OUT_DIR, f"{slug}.jpg")
    return save_jpeg(blob, out)


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = []
    failed = []
    for slug, url in TARGETS.items():
        ok = fetch_unit(slug, url)
        (saved if ok else failed).append(slug)
        time.sleep(0.8)

    print("\n" + "=" * 60)
    print(f"SAVED ({len(saved)}): {saved}")
    print(f"FAILED ({len(failed)}): {failed}")
    print(f"UNSOURCED (no confirmed article): {UNAVAILABLE}")


if __name__ == "__main__":
    main()
