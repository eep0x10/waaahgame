"""Look at <p> text surrounding each <img> on WHC unboxing article — match by proximity."""
import time
import requests
from bs4 import BeautifulSoup

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

ARTICLES = [
    "https://www.warhammer-community.com/en-gb/articles/4CZm5cyV/warhammer-preview-online-unboxing-dominion/",
    "https://www.warhammer-community.com/en-gb/articles/x6bC3d5Q/how-age-of-sigmars-dominion-boxed-set-draws-on-40-years-of-warhammer-history/",
    "https://www.warhammer-community.com/en-gb/articles/dug1jadu/saturday-pre-orders-stormcast-eternals-strike-from-the-heavens/",
    "https://www.warhammer-community.com/en-gb/articles/GIVSWMAW/forge-your-own-stormhost-and-cheat-death-with-battletome-stormcast-eternals/",
]
NEEDLES = ["vindictor", "praetor", "vexillor", "apotheosis", "longstrike", "raptor"]


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
        # Find article body
        body = soup.find("article") or soup.find("main") or soup
        # Iterate elements in document order. Track current paragraph text. When we see img, attach previous text.
        elements = body.find_all(["p", "h1", "h2", "h3", "h4", "img", "figure"])
        last_text = ""
        for el in elements:
            if el.name == "img":
                src = el.get("src") or el.get("data-src") or ""
                if "assets.warhammer-community.com/articles" in src:
                    text_low = last_text.lower()
                    for n in NEEDLES:
                        if n in text_low:
                            print(f"  [{n}] {last_text[:120]!r}")
                            print(f"      {src[:220]}")
                            break
            elif el.name == "figure":
                img = el.find("img")
                if img:
                    src = img.get("src") or ""
                    cap = el.find("figcaption")
                    txt = (cap.get_text(" ", strip=True) if cap else "") or last_text
                    text_low = txt.lower()
                    for n in NEEDLES:
                        if n in text_low and "assets.warhammer-community.com/articles" in src:
                            print(f"  FIG[{n}] {txt[:120]!r}")
                            print(f"      {src[:220]}")
                            break
            else:
                txt = el.get_text(" ", strip=True)
                if txt:
                    last_text = txt
        time.sleep(0.8)


if __name__ == "__main__":
    main()
