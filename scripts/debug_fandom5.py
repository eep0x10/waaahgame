"""Debug: examine Fandom MediaWiki API responses fully."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

# First check if the page actually exists on the AoS fandom wiki
# Try different wiki names for AoS
wikis = [
    'ageofsigmar',
    'warhammer40k',
    'warhammer',
]

for wiki in wikis:
    url = f'https://{wiki}.fandom.com/api.php?action=query&titles=Stormvermin&prop=images&imlimit=5&format=json'
    try:
        resp = session.get(url, timeout=15)
        data = resp.json()
        print(f'[{wiki}] HTTP {resp.status_code}')
        print(f'  raw: {json.dumps(data)[:300]}')
        pages = data.get('query', {}).get('pages', {})
        for pid, page in pages.items():
            print(f'  page id={pid} title={page.get("title")} missing={page.get("missing")}')
            for img in page.get('images', []):
                print(f'    image: {img}')
    except Exception as e:
        print(f'[{wiki}] EXCEPTION: {e}')

# Try to find what pages exist for skaven units
print()
print('--- Searching for Stormvermin on ageofsigmar wiki ---')
url = 'https://ageofsigmar.fandom.com/api.php?action=opensearch&search=Stormvermin&limit=5&format=json'
resp = session.get(url, timeout=15)
print('HTTP', resp.status_code, 'body:', resp.text[:500])
