"""Probe WHC articles - look at all <img> tags with alt text and nearby figcaption."""
import re
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

ARTICLES = [
    "https://www.warhammer-community.com/en-gb/articles/x6bC3d5Q/how-age-of-sigmars-dominion-boxed-set-draws-on-40-years-of-warhammer-history/",
    "https://www.warhammer-community.com/en-gb/articles/4CZm5cyV/warhammer-preview-online-unboxing-dominion/",
    "https://www.warhammer-community.com/en-gb/articles/S7JGVjJG/dominion-brings-mighty-paladins-to-the-mortal-realms-none-shall-pass-the-stormcast-eternals-annihilators/",
    "https://www.warhammer-community.com/en-gb/articles/dug1jadu/saturday-pre-orders-stormcast-eternals-strike-from-the-heavens/",
    "https://www.warhammer-community.com/en-gb/articles/GIVSWMAW/forge-your-own-stormhost-and-cheat-death-with-battletome-stormcast-eternals/",
]
NEEDLES = ["vindictor", "praetor", "vexillor", "apotheosis", "longstrike", "raptor"]


def main():
    from bs4 import BeautifulSoup

    for art in ARTICLES:
        slug = art.rstrip("/").split("/")[-1]
        print(f"\n=== {slug} ===")
        try:
            r = requests.get(art, headers=HEADERS, timeout=25)
        except Exception as exc:
            print(f"  ERR {exc}")
            continue
        if r.status_code != 200:
            print(f"  status {r.status_code}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        imgs = soup.find_all("img")
        print(f"  imgs: {len(imgs)}")
        for img in imgs:
            alt = (img.get("alt") or "").lower()
            src = img.get("src") or img.get("data-src") or ""
            for n in NEEDLES:
                if n in alt or n in src.lower():
                    print(f"    [{n}] alt={img.get('alt','')[:60]!r}")
                    print(f"        src={src[:240]}")
                    break
        # also try figcaptions
        figs = soup.find_all("figure")
        for fig in figs:
            cap = fig.find("figcaption")
            if not cap:
                continue
            text = cap.get_text(" ", strip=True).lower()
            for n in NEEDLES:
                if n in text:
                    img = fig.find("img")
                    src = img.get("src") if img else ""
                    print(f"    FIG[{n}] caption={cap.get_text(' ',strip=True)[:70]!r}")
                    print(f"        src={src[:240]}")
                    break
        time.sleep(0.7)


if __name__ == "__main__":
    main()
