"""Find correct wiki + check image availability via API."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

units = ['Stormvermin', 'Hell_Pit_Abomination', 'Saurus_Warriors', 'Clawlord', 'Stegadon']

# Test the main Warhammer wiki which has Age of Sigmar content
wikis_to_try = [
    ('warhammer-wiki', 'https://warhammerwiki.com/w/api.php'),
    ('whfb-fandom', 'https://warhammerfantasy.fandom.com/api.php'),
    ('aos-fandom', 'https://ageofsigmar.fandom.com/api.php'),
]

for wiki_name, api_url in wikis_to_try:
    print(f'\n=== {wiki_name} ({api_url}) ===')
    for unit_slug in units[:2]:
        url = f'{api_url}?action=query&titles={unit_slug}&prop=images&imlimit=5&format=json'
        try:
            resp = session.get(url, timeout=15)
            data = resp.json()
            pages = data.get('query', {}).get('pages', {})
            for pid, page in pages.items():
                missing = 'MISSING' if page.get('missing') == '' else 'FOUND'
                imgs = page.get('images', [])
                print(f'  {unit_slug}: {missing} | images: {[i["title"] for i in imgs]}')
        except Exception as e:
            print(f'  {unit_slug}: ERROR {e}')

# Also try WikiMedia search
print('\n=== Search warhammer on Wikipedia ===')
url = 'https://en.wikipedia.org/api/rest_v1/page/summary/Stormvermin'
try:
    resp = session.get(url, timeout=15)
    print('HTTP', resp.status_code, resp.text[:200])
except Exception as e:
    print('ERROR:', e)

# Try warhammer.fandom.com directly via API
print('\n=== warhammer.fandom.com API search ===')
url = 'https://warhammer.fandom.com/api.php?action=opensearch&search=Stormvermin&limit=5&format=json'
try:
    resp = session.get(url, timeout=15)
    print('HTTP', resp.status_code, 'body:', resp.text[:400])
except Exception as e:
    print('ERROR:', e)
