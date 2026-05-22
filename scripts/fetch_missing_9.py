"""
Fetch 9 specific missing unit images from community Fandom wikis.

Lexicanum is CF-blocked (cf_clearance expired), so we use Fandom MediaWiki
API across three wikis:
  - ageofsigmar.fandom.com
  - warhammerfantasy.fandom.com (older Vampire Counts / Be'lakor coverage)
  - warhammer40k.fandom.com (Be'lakor crossover)

Per target we curate explicit page-title aliases AND a keyword filter:
the image's File: title MUST contain at least one of the keywords. This
prevents pageimages from returning logos / disambiguation thumbnails /
totally-unrelated header art (which the naive scrape produced last run).

Each image is downloaded, validated (>= 200x200, > 5KB), resized to
600px wide max, saved as JPEG q85.
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path
from urllib.parse import quote

import requests
from PIL import Image

UA = 'waaahgame/0.2 (educational; contact: yhextt@gmail.com) python-requests/2.31'

ROOT = Path(__file__).resolve().parent.parent
STATIC_IMG = ROOT / 'app' / 'static' / 'img'

WIKIS = {
    'aos':  'https://ageofsigmar.fandom.com/api.php',
    'whfb': 'https://warhammerfantasy.fandom.com/api.php',
    'wh40k': 'https://warhammer40k.fandom.com/api.php',
}

MIN_W = 200
MIN_H = 200
MIN_BYTES = 5 * 1024
MAX_W = 600
DELAY = 0.5

# Image-title rejects (logos / placeholders / off-topic)
GLOBAL_BAD = (
    'logo', 'icon', 'symbol', 'flag', 'background', 'screenshot',
    'placeholder', 'wiki.png', 'navbar', 'header_', '_banner_small',
    'commons-logo', 'creative_commons', 'site-logo', 'discord',
    'spoilers', 'vermintide', 'total_war', 'darkoath',
)


# Each target: (faction_slug, display_name, output_filename, wiki_attempts)
# Each wiki_attempt is a dict:
#   - wiki: 'aos' | 'whfb' | 'wh40k'
#   - titles: list of explicit page-titles to query (in priority order)
#   - keywords: list of substrings required in the File: title (case-insensitive,
#               at least one must match). Use ['*'] to accept any (then GLOBAL_BAD only).
TARGETS = [
    {
        'faction': 'stormcast-eternals',
        'name': 'Knight-Vexillor with Banner of Apotheosis',
        'fname': 'knight-vexillor-with-banner-of-apotheosis',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Knight-Vexillor_with_Banner_of_Apotheosis',
                                       'Knight-Vexillor', 'Banner_of_Apotheosis'],
             'keywords': ['vexillor', 'apotheosis']},
            {'wiki': 'whfb', 'titles': ['Knight-Vexillor'],
             'keywords': ['vexillor', 'apotheosis']},
        ],
    },
    {
        'faction': 'stormcast-eternals',
        'name': 'Yndrasta, the Celestial Spear',
        'fname': 'yndrasta-the-celestial-spear',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Yndrasta', 'Yndrasta,_the_Celestial_Spear',
                                       'Yndrasta_the_Celestial_Spear'],
             'keywords': ['yndrasta']},
            {'wiki': 'whfb', 'titles': ['Yndrasta'],
             'keywords': ['yndrasta']},
        ],
    },
    {
        'faction': 'stormcast-eternals',
        'name': 'Vindictors',
        'fname': 'vindictors',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Vindictors', 'Vindictor'],
             'keywords': ['vindictor']},
            {'wiki': 'whfb', 'titles': ['Vindictors', 'Vindictor', 'Stormcast_Eternals'],
             'keywords': ['vindictor']},
        ],
    },
    {
        'faction': 'stormcast-eternals',
        'name': 'Annihilators',
        'fname': 'annihilators',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Annihilators', 'Annihilator',
                                       'Annihilators_with_Meteoric_Hammers'],
             'keywords': ['annihilator']},
            {'wiki': 'whfb', 'titles': ['Annihilators', 'Stormcast_Eternals'],
             'keywords': ['annihilator']},
        ],
    },
    {
        'faction': 'stormcast-eternals',
        'name': 'Praetors',
        'fname': 'praetors',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Praetors', 'Praetor', 'Stormcast_Praetors'],
             'keywords': ['praetor']},
            {'wiki': 'whfb', 'titles': ['Praetors', 'Stormcast_Eternals'],
             'keywords': ['praetor']},
        ],
    },
    {
        'faction': 'stormcast-eternals',
        'name': 'Vanguard-Raptors with Longstrike Crossbows',
        'fname': 'vanguard-raptors-with-longstrike-crossbows',
        'attempts': [
            {'wiki': 'aos', 'titles': ['Vanguard-Raptors_with_Longstrike_Crossbows',
                                       'Vanguard-Raptors',
                                       'Vanguard-Raptor_with_Longstrike_Crossbow',
                                       'Vanguard-Raptor'],
             'keywords': ['raptor', 'longstrike']},
            {'wiki': 'whfb', 'titles': ['Vanguard-Raptors', 'Vanguard-Raptor'],
             'keywords': ['raptor', 'longstrike']},
        ],
    },
    {
        'faction': 'slaves-to-darkness',
        'name': "Be'lakor, the Dark Master",
        'fname': 'be-lakor-the-dark-master',
        'attempts': [
            {'wiki': 'whfb', 'titles': ["Be'lakor", 'Be%27lakor'],
             'keywords': ["be'lakor", 'belakor', "be'larkor", "be'lakor1", "be'lakor2"]},
            {'wiki': 'aos', 'titles': ["Be'lakor", "Be'lakor,_the_Dark_Master"],
             'keywords': ["be'lakor", 'belakor', 'dark_master']},
            {'wiki': 'wh40k', 'titles': ["Be'lakor"],
             'keywords': ["be'lakor", 'belakor']},
        ],
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Skeleton Warriors',
        'fname': 'skeleton-warriors',
        'attempts': [
            {'wiki': 'whfb', 'titles': ['Skeleton_Warriors_(Vampire_Counts)',
                                       'Skeleton_Warriors'],
             # exclude tomb kings and total war / online renders; prefer canonical art
             'keywords': ['skeleton_warrior', 'skeleton warriors command',
                          'skeleton warriors units']},
            {'wiki': 'aos', 'titles': ['Skeleton_Warriors',
                                       'Deathrattle_Skeletons'],
             'keywords': ['skeleton']},
        ],
    },
    {
        'faction': 'soulblight-gravelords',
        'name': 'Black Knights',
        'fname': 'black-knights',
        'attempts': [
            {'wiki': 'whfb', 'titles': ['Black_Knights'],
             'keywords': ['black_knight', 'black knights', 'wh_main_vmp_black_knights']},
            {'wiki': 'aos', 'titles': ['Black_Knights'],
             'keywords': ['black_knight', 'black knights']},
        ],
    },
]


# ---------- MediaWiki helpers ----------

def mw_images_list(api: str, title: str, session: requests.Session) -> list[str]:
    """Return list of File: titles attached to a page."""
    url = (f'{api}?action=query&titles={quote(title)}&prop=images'
           f'&imlimit=40&format=json')
    try:
        r = session.get(url, timeout=15)
        data = r.json()
    except Exception:
        return []
    out: list[str] = []
    for _, page in data.get('query', {}).get('pages', {}).items():
        if page.get('missing') == '':
            return []
        for img in page.get('images', []):
            t = img.get('title', '')
            if t:
                out.append(t)
    return out


def mw_imageinfo(api: str, file_title: str, session: requests.Session) -> tuple[str | None, int, int]:
    url = (f'{api}?action=query&titles={quote(file_title)}&prop=imageinfo'
           f'&iiprop=url|size&format=json')
    try:
        r = session.get(url, timeout=15)
        data = r.json()
    except Exception:
        return None, 0, 0
    for _, page in data.get('query', {}).get('pages', {}).items():
        for info in page.get('imageinfo', []):
            return info.get('url'), info.get('width', 0), info.get('height', 0)
    return None, 0, 0


def passes_filter(file_title: str, keywords: list[str]) -> bool:
    lc = file_title.lower()
    if any(b in lc for b in GLOBAL_BAD):
        return False
    if not any(lc.endswith(ext) for ext in ('.jpg', '.jpeg', '.png', '.webp')):
        return False
    if keywords == ['*']:
        return True
    return any(k.lower() in lc for k in keywords)


def pick_image(api: str, titles: list[str], keywords: list[str],
               session: requests.Session) -> tuple[str | None, str, str]:
    """For each page title, list images, filter, resolve first match.

    Returns (url, source_descr, file_title) or (None,'','').
    """
    for title in titles:
        files = mw_images_list(api, title, session)
        time.sleep(DELAY)
        if not files:
            continue
        for ft in files:
            if not passes_filter(ft, keywords):
                continue
            url, w, h = mw_imageinfo(api, ft, session)
            time.sleep(DELAY)
            if url and w >= MIN_W and h >= MIN_H:
                return url, f'{title}', ft
    return None, '', ''


# ---------- Download / validate / save ----------

def download_validate_save(img_url: str, dest_abs: Path,
                           session: requests.Session) -> tuple[bool, str]:
    try:
        r = session.get(img_url, timeout=25)
        if r.status_code != 200:
            return False, f'HTTP {r.status_code}'
        if len(r.content) < MIN_BYTES:
            return False, f'small {len(r.content)}B'
        img = Image.open(io.BytesIO(r.content)).convert('RGB')
        if img.width < MIN_W or img.height < MIN_H:
            return False, f'dims {img.width}x{img.height}'
        if img.width > MAX_W:
            ratio = MAX_W / img.width
            img = img.resize((MAX_W, int(img.height * ratio)), Image.LANCZOS)
        dest_abs.parent.mkdir(parents=True, exist_ok=True)
        img.save(dest_abs, 'JPEG', quality=85, optimize=True)
        return True, f'{img.width}x{img.height}'
    except Exception as exc:
        return False, f'err {exc!r}'


def process_target(t: dict, session: requests.Session) -> tuple[bool, str, str]:
    faction = t['faction']
    fname = t['fname']
    dest_abs = STATIC_IMG / 'units' / faction / f'{fname}.jpg'
    if dest_abs.exists():
        return True, str(dest_abs), 'already exists'

    last = 'no source matched'
    for attempt in t['attempts']:
        wiki_key = attempt['wiki']
        api = WIKIS[wiki_key]
        url, page_title, file_title = pick_image(
            api, attempt['titles'], attempt['keywords'], session)
        if not url:
            continue
        ok, info = download_validate_save(url, dest_abs, session)
        time.sleep(DELAY)
        if ok:
            return True, str(dest_abs), (
                f'{wiki_key}:{page_title} <- {file_title} {info} ({url})'
            )
        last = f'{wiki_key}:{page_title} <- {file_title} dl-failed {info}'
    return False, str(dest_abs), last


def main():
    session = requests.Session()
    session.headers.update({'User-Agent': UA})

    ok_n = 0
    fail_n = 0
    for t in TARGETS:
        try:
            ok, path, info = process_target(t, session)
        except Exception as exc:
            ok, path, info = False, '', f'exception {exc!r}'
        if ok:
            ok_n += 1
            print(f'OK   {path} | {info}', flush=True)
        else:
            fail_n += 1
            print(f"FAIL {t['name']} ({t['faction']}) | {info}", flush=True)
    print(f'--- done: ok={ok_n} fail={fail_n} ---')
    return 0 if fail_n == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
