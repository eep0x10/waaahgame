"""
lex_parse.py  —  Parse lex_dump.json → lexicanum_manifest.json
"""

import json
import re
from pathlib import Path
from bs4 import BeautifulSoup

HOST = "https://ageofsigmar.lexicanum.com"
DUMP_PATH = Path("scripts/cache/lex_dump.json")
OUT_PATH = Path("scripts/cache/lexicanum_manifest.json")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def abs_url(src: str) -> str:
    """Prefix host if relative."""
    if not src:
        return src
    if src.startswith("http"):
        return src
    return HOST + src


THUMB_RE = re.compile(
    r"^(.*)/thumb/([^/]+/[^/]+/[^/]+)/\d+px-[^/]+$"
)


def thumb_to_full(url: str) -> str:
    """Convert mediawiki thumb URL to full-resolution URL."""
    if not url:
        return url
    m = THUMB_RE.match(url)
    if m:
        return m.group(1) + "/" + m.group(2)
    return url


def slug_from_href(href: str) -> str:
    """'/wiki/Some_Unit' → 'some-unit'"""
    name = href.split("/wiki/", 1)[-1]
    return name.replace("_", "-").lower()


# ---------------------------------------------------------------------------
# 1. Parse list_html
# ---------------------------------------------------------------------------

def parse_list(list_html: str) -> dict:
    """Return dict slug → partial unit record from the list page."""
    soup = BeautifulSoup(list_html, "html.parser")
    tbl = soup.find("table", class_="wikitable")
    if tbl is None:
        raise ValueError("No wikitable found in list_html")

    rows = tbl.find_all("tr")
    units = {}

    for row in rows[1:]:  # skip header
        cells = row.find_all(["td", "th"])
        if len(cells) < 4:
            continue

        # Column order: 0=image, 1=unit, 2=faction, 3=grand_alliance, 4=warscroll
        img_cell   = cells[0]
        unit_cell  = cells[1]
        fac_cell   = cells[2]
        alliance_cell = cells[3]

        # unit link
        unit_link = unit_cell.find("a")
        if unit_link is None:
            continue
        href  = unit_link.get("href", "")
        title = unit_link.get_text(strip=True)
        if not href.startswith("/wiki/"):
            continue

        slug = slug_from_href(href)

        # factions
        factions = [a.get_text(strip=True) for a in fac_cell.find_all("a") if a.get_text(strip=True)]

        # grand alliance
        grand_alliance = alliance_cell.get_text(strip=True)

        # thumb from image cell
        img = img_cell.find("img")
        thumb_url = abs_url(img.get("src", "")) if img else ""

        units[slug] = {
            "slug": slug,
            "title": title,
            "href": href,
            "url": HOST + href,
            "factions": factions,
            "grand_alliance": grand_alliance,
            "thumb_url": thumb_url,
        }

    return units


# ---------------------------------------------------------------------------
# 2. Parse individual unit pages
# ---------------------------------------------------------------------------

def _find_infobox_image(soup: BeautifulSoup) -> str:
    """Try several selectors to find infobox/main image."""
    # table.infobox
    infobox = soup.find("table", class_="infobox")
    if infobox:
        img = infobox.find("img")
        if img:
            return abs_url(img.get("src", ""))

    # Unclassed table that looks like an infobox (first table without class)
    for tbl in soup.find_all("table"):
        if not tbl.get("class"):
            img = tbl.find("img")
            if img:
                src = img.get("src", "")
                # Skip tiny icons (< 30px wide)
                width = img.get("width")
                try:
                    if width and int(width) < 30:
                        continue
                except ValueError:
                    pass
                if src:
                    return abs_url(src)

    # .thumbinner img
    ti = soup.find(class_="thumbinner")
    if ti:
        img = ti.find("img")
        if img:
            return abs_url(img.get("src", ""))

    # .thumb img
    th = soup.find(class_="thumb")
    if th:
        img = th.find("img")
        if img:
            return abs_url(img.get("src", ""))

    # figure img
    fig = soup.find("figure")
    if fig:
        img = fig.find("img")
        if img:
            return abs_url(img.get("src", ""))

    return ""


def _parse_infobox_dict(soup: BeautifulSoup) -> dict:
    """Extract key→value from the unclassed infobox-like table."""
    result = {}

    # Try table.infobox first, then first unclassed table
    infobox = soup.find("table", class_="infobox")
    if infobox is None:
        infobox = next(
            (t for t in soup.find_all("table") if not t.get("class")), None
        )
    if infobox is None:
        return result

    for row in infobox.find_all("tr"):
        cells = row.find_all(["td", "th"])
        if len(cells) == 2:
            key   = cells[0].get_text(strip=True)
            value = cells[1].get_text(" ", strip=True)
            if key:
                result[key] = value
        # Single-cell rows (title/image) are skipped

    return result


def _parse_blurb(soup: BeautifulSoup) -> str:
    """First non-empty paragraph in .mw-parser-output."""
    output = soup.find(class_="mw-parser-output")
    if output is None:
        return ""
    for p in output.find_all("p", recursive=False):
        txt = p.get_text(strip=True)
        if txt:
            return txt
    # Try non-recursive if none found at top level
    for p in output.find_all("p"):
        txt = p.get_text(strip=True)
        if txt:
            return txt
    return ""


def _parse_categories(soup: BeautifulSoup) -> list:
    """Category names from #mw-normal-catlinks."""
    catlinks = soup.find(id="mw-normal-catlinks")
    if catlinks is None:
        return []
    cats = []
    for a in catlinks.find_all("a"):
        name = a.get_text(strip=True)
        if name and name.lower() != "categories":
            cats.append(name)
    return cats


def parse_unit_page(html: str) -> dict:
    soup = BeautifulSoup(html, "html.parser")
    return {
        "infobox_image_thumb": _find_infobox_image(soup),
        "infobox": _parse_infobox_dict(soup) or None,
        "blurb": _parse_blurb(soup) or None,
        "categories": _parse_categories(soup),
    }


# ---------------------------------------------------------------------------
# 3. Main
# ---------------------------------------------------------------------------

def main():
    print("Loading dump…")
    with open(DUMP_PATH, "r", encoding="utf-8") as f:
        dump = json.load(f)

    # -- List page --
    print("Parsing list page…")
    list_units = parse_list(dump["list_html"])
    print(f"  {len(list_units)} units in list")

    # -- Unit detail pages --
    raw_units: dict = dump.get("units", {})
    print(f"Parsing {len(raw_units)} unit detail pages…")

    detail: dict[str, dict] = {}
    for href, html in raw_units.items():
        slug = slug_from_href(href)
        detail[slug] = parse_unit_page(html)

    # -- Merge --
    manifest_units: dict[str, dict] = {}

    # Start from list entries (authoritative for slug/title/factions/alliance)
    for slug, rec in list_units.items():
        d = detail.get(slug, {})
        has_detail = bool(d)

        infobox_img = d.get("infobox_image_thumb", "") if has_detail else ""
        thumb_url   = rec.get("thumb_url", "")

        # Prefer infobox image; fall back to list thumb
        best_img = infobox_img or thumb_url

        manifest_units[slug] = {
            "slug": slug,
            "title": rec["title"],
            "href": rec["href"],
            "url": rec["url"],
            "factions": rec["factions"],
            "grand_alliance": rec["grand_alliance"],
            "thumb_url": thumb_url,
            "full_image_url": thumb_to_full(best_img),
            "infobox": d.get("infobox") if has_detail else None,
            "blurb": d.get("blurb") if has_detail else None,
            "categories": d.get("categories", []) if has_detail else [],
            "has_detail": has_detail,
        }

    # Add any slugs from detail that weren't in list
    for slug, d in detail.items():
        if slug not in manifest_units:
            infobox_img = d.get("infobox_image_thumb", "")
            manifest_units[slug] = {
                "slug": slug,
                "title": slug.replace("-", " ").title(),
                "href": f"/wiki/{slug.replace('-', '_')}",
                "url": HOST + f"/wiki/{slug.replace('-', '_')}",
                "factions": [],
                "grand_alliance": "",
                "thumb_url": "",
                "full_image_url": thumb_to_full(infobox_img),
                "infobox": d.get("infobox"),
                "blurb": d.get("blurb"),
                "categories": d.get("categories", []),
                "has_detail": True,
            }

    # -- Factions index --
    factions: dict[str, list] = {}
    for slug, rec in manifest_units.items():
        for fac in rec.get("factions", []):
            factions.setdefault(fac, []).append(slug)

    # -- Stats --
    total   = len(manifest_units)
    w_detail = sum(1 for r in manifest_units.values() if r["has_detail"])
    w_image  = sum(1 for r in manifest_units.values() if r.get("full_image_url"))
    n_fac    = len(factions)

    stats = {
        "total_units": total,
        "with_detail": w_detail,
        "with_image":  w_image,
        "factions":    n_fac,
    }

    manifest = {
        "units":    manifest_units,
        "factions": factions,
        "stats":    stats,
    }

    # -- Write --
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUT_PATH, "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(f"Manifest written to {OUT_PATH}")
    print("Stats:", stats)


if __name__ == "__main__":
    main()
