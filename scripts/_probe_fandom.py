"""Probe Fandom AoS pages for the 4 missing Stormcast units."""
import re
import requests

HEADERS = {
    "User-Agent": "waaahgame/0.6 (educational; contact: yhextt@gmail.com) python-requests/2.31"
}

TITLES = [
    "Vanguard-Raptors",
    "Vanguard-Raptors_with_Longstrike_Crossbows",
    "Longstrike_Crossbow",
    "Vindictors",
    "Vindictor",
    "Stormcast_Vindictors",
    "Praetors",
    "Praetor",
    "Knight-Praetor",
    "Stormcast_Praetors",
    "Knight-Vexillor",
    "Knight-Vexillor_with_Banner_of_Apotheosis",
    "Banner_of_Apotheosis",
    "Vexillor",
]

URL_RE = re.compile(r'https://static\.wikia\.nocookie\.net/[^\s"\'<>]+?\.(?:jpg|jpeg|png|webp)', re.I)
ALT_RE = re.compile(r'alt="([^"]*)"\s+src="(https://static\.wikia\.nocookie\.net/[^"]+?\.(?:jpg|jpeg|png|webp))', re.I)


def fetch(title):
    r = requests.get(
        "https://ageofsigmar.fandom.com/api.php",
        params={"action": "parse", "page": title, "prop": "text", "format": "json", "redirects": 1},
        headers=HEADERS, timeout=20,
    )
    j = r.json()
    if "parse" not in j:
        return None
    html = j["parse"]["text"]["*"]
    urls = URL_RE.findall(html)
    pairs = ALT_RE.findall(html)
    return j["parse"].get("title", title), urls, pairs


for t in TITLES:
    res = fetch(t)
    if res is None:
        print(f"\n--- {t}: NOT FOUND")
        continue
    title, urls, pairs = res
    print(f"\n=== {t} -> {title}  urls={len(urls)} alts={len(pairs)} ===")
    for alt, u in pairs[:8]:
        print(f"  alt={alt[:60]!r}")
        print(f"     {u[:230]}")
    seen = set(u for _, u in pairs)
    for u in urls[:8]:
        if u not in seen:
            print(f"  (no-alt) {u[:230]}")
