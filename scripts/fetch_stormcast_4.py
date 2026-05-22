"""
Fetch 4 remaining Stormcast Eternals AoS 4 unit images.
URLs harvested from WHC article DOM-walk + GW catalog + Fandom.
Polite, synchronous, validates size/dims. JPEG q85 max 600w.
"""

import io
import os
import time

import requests
from PIL import Image

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
HEADERS = {
    "User-Agent": UA,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
    "Referer": "https://www.warhammer-community.com/",
}

OUT_DIR = "/app/app/static/img/units/stormcast-eternals"
MIN_BYTES = 8000
MIN_W = 200
MIN_H = 200
MAX_W = 600
JPEG_Q = 85

# slug -> ordered URL candidates (primary, fallback...)
TARGETS = {
    "vindictors": [
        "https://assets.warhammer-community.com/articles/853b442f-ec02-4c42-a025-17d2f600bb10/powxtmb0lefdembn.jpg",
        "https://www.warhammer.com/app/resources/catalog/product/920x950/99120218061_SCEVindicatorsLead.jpg",
    ],
    "praetors": [
        "https://www.warhammer.com/app/resources/catalog/product/920x950/99120218062_SCEPraetorsLead.jpg",
    ],
    "knight-vexillor-with-banner-of-apotheosis": [
        "https://assets.warhammer-community.com/articles/853b442f-ec02-4c42-a025-17d2f600bb10/lktd3vv2bnuvhnap.jpg",
    ],
    "vanguard-raptors-with-longstrike-crossbows": [
        "https://assets.warhammer-community.com/articles/d6b66106-f65b-492b-9ef0-cdfcc22ef112/redkne6glvevrtis.jpg",
        "https://static.wikia.nocookie.net/age-of-sigmar/images/4/4a/DxIaiHkwmNI.jpg",
    ],
}


def download(url: str):
    try:
        r = requests.get(url, headers=HEADERS, timeout=30)
        if r.status_code == 200 and len(r.content) >= MIN_BYTES:
            return r.content
        print(f"  [skip] status={r.status_code} size={len(r.content)} url={url[:120]}")
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


def fetch_unit(slug: str, urls: list) -> bool:
    print(f"\n=== {slug} ===")
    out = os.path.join(OUT_DIR, f"{slug}.jpg")
    for i, url in enumerate(urls):
        print(f"  try[{i}]: {url[:140]}")
        blob = download(url)
        time.sleep(0.7)
        if not blob:
            continue
        if save_jpeg(blob, out):
            return True
    return False


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    saved = []
    failed = []
    for slug, urls in TARGETS.items():
        ok = fetch_unit(slug, urls)
        (saved if ok else failed).append(slug)
        time.sleep(0.8)

    print("\n" + "=" * 60)
    print(f"SAVED ({len(saved)}): {saved}")
    print(f"FAILED ({len(failed)}): {failed}")


if __name__ == "__main__":
    main()
