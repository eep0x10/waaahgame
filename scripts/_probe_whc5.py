"""Document-order proximity probe over MORE WHC stormcast articles for praetors + raptors."""
import time
import requests
from bs4 import BeautifulSoup, NavigableString

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
}

ARTICLES = [
    "https://www.warhammer-community.com/en-gb/articles/Z4n3LtAo/warhammer-age-of-sigmar-faction-focus-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/yrpl1os9/sunday-preview-unleash-the-ruination-chamber/",
    "https://www.warhammer-community.com/en-gb/articles/UYrsfXoP/the-stormcast-eternals-become-the-ultimate-defenders-of-the-mortal-realms-in-their-best-battletome-yet/",
    "https://www.warhammer-community.com/en-gb/articles/Pv7ewHGk/the-stormcast-eternals-hold-the-line-in-this-towering-new-warhammer-world-diorama/",
    "https://www.warhammer-community.com/en-gb/articles/vR4xF0qt/domitans-stormcoven-are-ready-to-purge-the-wyrdhollow-with-holy-bolts-of-lucent-lightning/",
    "https://www.warhammer-community.com/en-gb/articles/fbxyifn8/warhammer-heroes-series-5-stormcast-eternals-take-over/",
    "https://www.warhammer-community.com/en-gb/articles/opSYHeIA/the-stormcast-eternals-bring-immense-range-and-lots-of-gryphs-to-the-tabletop-with-these-warscrolls/",
    "https://www.warhammer-community.com/en-gb/articles/vCwmVYX5/warhammer-preview-online-dominion-celebration/",
    "https://www.warhammer-community.com/en-gb/articles/qzEjqwCx/warhammer-day-preview-lord-relictor-ionus-cryptborn-sigmars-prodigal-son/",
    "https://www.warhammer-community.com/en-gb/articles/2A64A1mI/abraxia-and-gunnar-brand-rule-the-days-before-the-skaventide-with-free-warscrolls/",
    "https://www.warhammer-community.com/en-gb/articles/lVdpQ94O/skaven-and-stormcast-clash-in-a-free-warhammer-age-of-sigmar-battle-report/",
    "https://www.warhammer-community.com/en-gb/articles/BoFGxCTp/pre-order-skaventide-and-get-one-of-these-awesome-rewards/",
    "https://www.warhammer-community.com/en-gb/articles/tP21PFUC/stormcast-eternals-in-the-new-edition-elite-versatile-champions-of-order/",
    "https://www.warhammer-community.com/en-gb/articles/eYj5ssYA/warhammer-community-staff-paint-the-stormcast-eternals-of-skaventide/",
    "https://www.warhammer-community.com/en-gb/articles/pH2l08Cs/sunday-preview-skaventide-approaches/",
    "https://www.warhammer-community.com/en-gb/articles/anIYwozY/painting-the-ruination-chamber-how-the-eavy-metal-team-brought-the-stormcast-eternals-of-skaventide-to-life/",
    "https://www.warhammer-community.com/en-gb/articles/R5GtZKQF/nova-open-preview-new-stormcast-eternals-arrive-in-a-flash-of-thunder/",
    "https://www.warhammer-community.com/en-gb/articles/lbEnXhmp/warhammer-studio-interview-designing-the-new-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/gbi5gToU/what-else-is-in-skaventide-inside-the-new-core-book-and-the-matched-play-cards/",
    "https://www.warhammer-community.com/en-gb/articles/PllTiC7s/stormcast-eternals-reinforcements-the-stormstrike-palladors-and-the-stormreach-portal/",
    "https://www.warhammer-community.com/en-gb/articles/rm4a04l2/saturday-pre-orders-warhammer-age-of-sigmar-rings-in-a-new-edition-with-skaventide/",
    "https://www.warhammer-community.com/en-gb/articles/2ycaot8q/new-stormcast-eternals-prosecutors-soar-into-battle-on-wings-of-azure-flame/",
    "https://www.warhammer-community.com/en-gb/articles/NfUQF6t9/build-all-dragon-armies-and-other-fierce-forces-with-the-new-stormcast-eternals-battletome/",
    "https://www.warhammer-community.com/en-gb/articles/q2c2tgvd/warhammer-art-through-the-years-stormcast-eternals/",
    "https://www.warhammer-community.com/en-gb/articles/4CZm5cyV/warhammer-preview-online-unboxing-dominion/",
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
                yield from walk(child)
            else:
                yield from walk(child)


def main():
    summary = {n: [] for n in NEEDLES}
    for art in ARTICLES:
        slug = art.rstrip("/").split("/")[-1][:60]
        try:
            r = requests.get(art, headers=HEADERS, timeout=25)
        except Exception as exc:
            print(f"  ERR {art}: {exc}")
            continue
        if r.status_code != 200:
            print(f"  {slug} -> {r.status_code}")
            continue
        soup = BeautifulSoup(r.text, "html.parser")
        running_text = ""
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
                        idx = low.rfind(n)
                        ctx = running_text[max(0, idx-40):idx+80]
                        summary[n].append((slug, ctx, src))
                        break
        time.sleep(0.7)

    for n in NEEDLES:
        print(f"\n========== {n} ({len(summary[n])}) ==========")
        for slug, ctx, src in summary[n][:10]:
            print(f"  art={slug}")
            print(f"  ctx={ctx!r}")
            print(f"  src={src[:220]}")


if __name__ == "__main__":
    main()
