"""Probe WHC articles for unit-named CDN images."""
import re
import time
import requests

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9",
}

# WHC sitemap pulled candidate articles - relevant Dominion / Stormcast reveal era
ARTICLES = [
    "https://www.warhammer-community.com/en-gb/articles/x6bC3d5Q/how-age-of-sigmars-dominion-boxed-set-draws-on-40-years-of-warhammer-history/",
    "https://www.warhammer-community.com/en-gb/articles/4CZm5cyV/warhammer-preview-online-unboxing-dominion/",
    "https://www.warhammer-community.com/en-gb/articles/YxtGPLuz/expert-painters-take-on-the-dominion-stormcast-eternals-and-the-results-are-inspiring/",
    "https://www.warhammer-community.com/en-gb/articles/cajInRDh/feast-your-eyes-on-these-magnificent-dominion-paint-jobs-from-around-the-world/",
    "https://www.warhammer-community.com/en-gb/articles/GIVSWMAW/forge-your-own-stormhost-and-cheat-death-with-battletome-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/dug1jadu/saturday-pre-orders-stormcast-eternals-strike-from-the-heavens/",
    "https://www.warhammer-community.com/en-gb/articles/q2c2tgvd/warhammer-art-through-the-years-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/S7JGVjJG/dominion-brings-mighty-paladins-to-the-mortal-realms-none-shall-pass-the-stormcast-eternals-annihilators/",
    "https://www.warhammer-community.com/en-gb/articles/CieZgB7r/the-warriors-from-dominion-arrive-in-warcry-with-free-fighter-cards-and-a-new-campaign/",
    "https://www.warhammer-community.com/en-gb/articles/pesUrPBC/black-library-celebration-2022-meet-dominion-zephon-the-bringer-of-sorrow/",
    "https://www.warhammer-community.com/en-gb/articles/9g3WS2PK/whos-the-stronger-wizard-in-dominion-sigmars-loreseeker-and-the-kruleboyzs-bog-shaman-face-off/",
    "https://www.warhammer-community.com/en-gb/articles/JzQrkg2y/talented-painters-from-the-community-tackle-the-stormcast-eternals-of-skaventide/",
    "https://www.warhammer-community.com/en-gb/articles/beopihjl/hobbyists-from-the-warhammer-community-paint-up-a-storm-with-stormcast-eternals/",
]

NEEDLES = ["vindictor", "praetor", "vexillor", "apotheosis", "longstrike", "raptor", "banner"]

JPG_RE = re.compile(r'https://[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)', re.IGNORECASE)


def main():
    for art in ARTICLES:
        slug = art.rstrip("/").split("/")[-1][:60]
        print(f"\n=== {slug} ===")
        try:
            r = requests.get(art, headers=HEADERS, timeout=25)
        except Exception as exc:
            print(f"  ERR {exc}")
            continue
        if r.status_code != 200:
            print(f"  status {r.status_code}")
            continue
        html = r.text
        urls = JPG_RE.findall(html)
        urls = list(dict.fromkeys(urls))
        print(f"  total imgs: {len(urls)}")
        # Filter to CDN
        cdn = [u for u in urls if "assets.warhammer-community.com" in u or "assets.games-workshop" in u]
        hits = [u for u in cdn if any(n in u.lower() for n in NEEDLES)]
        print(f"  cdn: {len(cdn)}  needle-matched: {len(hits)}")
        for u in hits[:15]:
            print(f"    HIT {u[:250]}")
        # Also try to find images in body context (e.g. with alt text)
        # Look at alt text in <img> tags
        for needle in NEEDLES:
            # find <img tag with alt containing needle, capture src
            pat = re.compile(
                r'<img[^>]*alt="([^"]*' + needle + r'[^"]*)"[^>]*src="([^"]+)"|<img[^>]*src="([^"]+)"[^>]*alt="([^"]*' + needle + r'[^"]*)"',
                re.IGNORECASE,
            )
            for m in pat.finditer(html):
                alt = m.group(1) or m.group(4)
                src = m.group(2) or m.group(3)
                print(f"    ALT[{needle}] alt={alt[:60]!r} src={src[:200]}")
        time.sleep(0.7)


if __name__ == "__main__":
    main()
