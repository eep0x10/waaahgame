"""
Full pipeline test: WHFB Fandom API -> get images -> pick best -> get URL -> download test.
Also explore: what do all 31 units look like?
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json, time

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

BASE = 'https://warhammerfantasy.fandom.com/api.php'

def get_best_image_url(unit_name):
    """
    1. Try pageimages thumbnail (easiest, direct URL)
    2. Fall back to images list + imageinfo
    """
    slug = unit_name.replace(' ', '_')

    # Step 1: pageimages thumbnail
    url = f'{BASE}?action=query&titles={requests.utils.quote(slug)}&prop=pageimages&piprop=thumbnail|name&pithumbsize=700&format=json'
    resp = session.get(url, timeout=15)
    data = resp.json()
    pages = data.get('query', {}).get('pages', {})
    for pid, page in pages.items():
        if page.get('missing') == '':
            return None, 'page_missing'
        thumb = page.get('thumbnail', {})
        if thumb.get('source'):
            return thumb['source'], 'pageimages'

    # Step 2: get images list and resolve first jpg/png
    url2 = f'{BASE}?action=query&titles={requests.utils.quote(slug)}&prop=images&imlimit=10&format=json'
    resp2 = session.get(url2, timeout=15)
    data2 = resp2.json()
    pages2 = data2.get('query', {}).get('pages', {})
    img_titles = []
    for pid, page in pages2.items():
        if page.get('missing') == '':
            return None, 'page_missing'
        for img in page.get('images', []):
            t = img['title']
            if any(t.lower().endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.webp']):
                img_titles.append(t)

    if not img_titles:
        return None, 'no_images'

    # Pick first non-icon image
    for img_title in img_titles:
        if any(kw in img_title.lower() for kw in ['logo', 'icon', 'banner', 'web', 'screenshot', 'vermintide']):
            continue
        url3 = f'{BASE}?action=query&titles={requests.utils.quote(img_title)}&prop=imageinfo&iiprop=url|size&format=json'
        resp3 = session.get(url3, timeout=15)
        data3 = resp3.json()
        pages3 = data3.get('query', {}).get('pages', {})
        for pid, page in pages3.items():
            for info in page.get('imageinfo', []):
                w, h = info.get('width', 0), info.get('height', 0)
                if w >= 200 and h >= 200:
                    return info['url'], f'imageinfo:{img_title[:40]}'
    return None, 'no_good_image'


# Test all 31 units
ALL_UNITS = [
    # Skaven
    'Verminlord Corruptor', 'Verminlord Warbringer', 'Thanquol on Boneripper', 'Grey Seer',
    'Warlock Bombardier', 'Master Moulder', 'Deathmaster', 'Clawlord', 'Plague Priest',
    'Stormvermin', 'Clanrats', 'Night Runners', 'Gutter Runners', 'Plague Monks',
    'Plague Censer Bearers', 'Hell Pit Abomination', 'Rat Ogors', 'Stormfiends',
    'Warplock Jezzails', 'Warp Lightning Cannon',
    # Seraphon
    'Slann Starmaster', 'Saurus Astrolith Bearer', 'Skink Starpriest',
    'Saurus Scar-Veteran on Carnosaur', 'Stegadon', 'Engine of the Gods',
    'Saurus Warriors', 'Aggradon Lancers', 'Skinks', 'Saurus Guard', 'Sunblood Pack',
]

print('Checking all units on WHFB Fandom:')
found = []
not_found = []
for name in ALL_UNITS:
    img_url, reason = get_best_image_url(name)
    status = 'OK' if img_url else 'FAIL'
    print(f'  [{status}] {name}: {reason} | {img_url[:80] if img_url else ""}')
    if img_url:
        found.append((name, img_url, reason))
    else:
        not_found.append((name, reason))
    time.sleep(0.3)

print(f'\nFound: {len(found)}/{len(ALL_UNITS)}')
print(f'Not found: {[n for n, _ in not_found]}')
