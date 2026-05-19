"""
Expand coverage: try alternative page names + warhammer wiki search fallback.
Also try the main warhammer wiki fandom (which includes AoS content).
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json, time

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

WHFB_BASE = 'https://warhammerfantasy.fandom.com/api.php'
W40K_BASE = 'https://warhammer40k.fandom.com/api.php'

# Units that failed - try alternative names
ALT_NAMES = {
    'Verminlord Corruptor': ['Verminlord', 'Corruptor'],
    'Verminlord Warbringer': ['Verminlord'],
    'Thanquol on Boneripper': ['Thanquol', 'Boneripper'],
    'Grey Seer': ['Grey Seer (Skaven)', 'Skaven Grey Seer'],
    'Warlock Bombardier': ['Warlock Engineer', 'Skaven Warlock'],
    'Clawlord': ['Warlord (Skaven)', 'Skaven Warlord'],
    'Clanrats': ['Clanrat'],
    'Night Runners': ['Night Runner'],
    'Gutter Runners': ['Gutter Runner'],
    'Plague Monks': ['Plague Monk'],
    'Plague Censer Bearers': ['Plague Censer Bearer', 'Plague Monks'],
    'Hell Pit Abomination': ['Hellpit Abomination'],
    'Rat Ogors': ['Rat Ogre', 'Rat Ogor'],
    'Stormfiends': ['Stormfiend'],
    'Warplock Jezzails': ['Warplock Jezzail', 'Jezzails'],
    'Warp Lightning Cannon': ['Warp Lightning Cannon (Skaven)'],
    'Slann Starmaster': ['Slann', 'Slann Mage-Priest'],
    'Saurus Astrolith Bearer': ['Saurus', 'Astrolith Bearer'],
    'Skink Starpriest': ['Skink Priest', 'Skink'],
    'Saurus Scar-Veteran on Carnosaur': ['Carnosaur', 'Saurus Scar-Veteran', 'Old Blood on Carnosaur'],
    'Saurus Warriors': ['Saurus Warrior', 'Saurus'],
    'Aggradon Lancers': ['Aggradon', 'Cold One Riders'],
    'Saurus Guard': ['Temple Guard', 'Saurus Temple Guard'],
    'Sunblood Pack': ['Sunblood', 'Saurus Sunblood'],
}

def get_pageimages(api_base, slug):
    url = f'{api_base}?action=query&titles={requests.utils.quote(slug)}&prop=pageimages&piprop=thumbnail|name&pithumbsize=700&format=json'
    try:
        resp = session.get(url, timeout=12)
        data = resp.json()
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            if page.get('missing') == '':
                return None
            thumb = page.get('thumbnail', {})
            if thumb.get('source'):
                return thumb['source']
    except Exception:
        pass
    return None

def search_wiki(api_base, query):
    """Use opensearch to find matching articles."""
    url = f'{api_base}?action=opensearch&search={requests.utils.quote(query)}&limit=3&format=json'
    try:
        resp = session.get(url, timeout=12)
        data = resp.json()
        if len(data) >= 4:
            return list(zip(data[1], data[3]))  # (title, url) pairs
    except Exception:
        pass
    return []

print('Trying alternative names for missing units:')
found_extra = []
for orig_name, alts in ALT_NAMES.items():
    found = False
    for alt in alts:
        img_url = get_pageimages(WHFB_BASE, alt.replace(' ', '_'))
        if img_url:
            print(f'  [OK] {orig_name} -> {alt}: {img_url[:80]}')
            found_extra.append((orig_name, alt, img_url, 'whfb'))
            found = True
            break
        time.sleep(0.2)
    if not found:
        # Try search
        results = search_wiki(WHFB_BASE, orig_name)
        if results:
            for title, link in results[:2]:
                img_url = get_pageimages(WHFB_BASE, title.replace(' ', '_'))
                if img_url:
                    print(f'  [OK-search] {orig_name} -> "{title}": {img_url[:80]}')
                    found_extra.append((orig_name, title, img_url, 'whfb_search'))
                    found = True
                    break
                time.sleep(0.2)
    if not found:
        print(f'  [FAIL] {orig_name}')

print(f'\nExtra found: {len(found_extra)}')
