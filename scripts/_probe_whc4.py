"""Walk DOM in document order; track running text; tag each img with nearest preceding text."""
import time
import requests
from bs4 import BeautifulSoup, NavigableString

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

ARTICLES = [
    "https://www.warhammer-community.com/en-gb/articles/4CZm5cyV/warhammer-preview-online-unboxing-dominion/",
    "https://www.warhammer-community.com/en-gb/articles/x6bC3d5Q/how-age-of-sigmars-dominion-boxed-set-draws-on-40-years-of-warhammer-history/",
    "https://www.warhammer-community.com/en-gb/articles/dug1jadu/saturday-pre-orders-stormcast-eternals-strike-from-the-heavens/",
    "https://www.warhammer-community.com/en-gb/articles/GIVSWMAW/forge-your-own-stormhost-and-cheat-death-with-battletome-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/S7JGVjJG/dominion-brings-mighty-paladins-to-the-mortal-realms-none-shall-pass-the-stormcast-eternals-annihilators/",
]
NEEDLES = ["vindictor", "praetor", "vexillor", "apotheosis", "longstrike", "raptor"]


def walk(node):
    for child in getattr(node, "children", []):
        if isinstance(child, NavigableString):
            yield ("text", str(child))
        else:
            if child.name == "img":
                yield ("img", child)
            elif child.name == "figcaption":
                yield ("cap", child.get_text(" ", strip=True))
                # also recurse for nested imgs
                yield from walk(child)
            else:
                yield from walk(child)


def main():
    for art in ARTICLES:
        slug = art.rstrip("/").split("/")[-1][:60]
        print(f"\n=== {slug} ===")
        try:
            r = requests.get(art, headers=HEADERS, timeout=25)
        except Exception as exc:
            print(f"  ERR {exc}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        running_text = ""
        text_buf_chars = 0
        hits = {n: [] for n in NEEDLES}
        for kind, item in walk(soup):
            if kind == "text":
                t = item.strip()
                if t:
                    running_text = (running_text + " " + t)[-1200:]
            elif kind == "cap":
                if item:
                    running_text = (running_text + " " + item)[-1200:]
            elif kind == "img":
                src = item.get("src") or item.get("data-src") or ""
                if "assets.warhammer-community.com/articles" not in src:
                    continue
                low = running_text.lower()
                for n in NEEDLES:
                    if n in low:
                        # Find context window around needle
                        idx = low.rfind(n)
                        ctx = running_text[max(0, idx-40):idx+80]
                        hits[n].append((ctx, src))
                        break
        for n, lst in hits.items():
            if lst:
                print(f"  -- {n} ({len(lst)}) --")
                for ctx, src in lst[:5]:
                    print(f"    ctx: ...{ctx!r}")
                    print(f"    src: {src[:230]}")
        time.sleep(0.8)


if __name__ == "__main__":
    main()
