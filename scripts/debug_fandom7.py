"""Explore warhammerfantasy.fandom.com API to get actual image URLs."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests, json

session = requests.Session()
session.headers.update({'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'})

BASE = 'https://warhammerfantasy.fandom.com/api.php'

# Get all images for Stormvermin page
url = f'{BASE}?action=query&titles=Stormvermin&prop=images&imlimit=10&format=json'
resp = session.get(url, timeout=15)
data = resp.json()
print('Images on Stormvermin page:')
pages = data['query']['pages']
for pid, page in pages.items():
    for img in page.get('images', []):
        print(' ', img['title'])

# Now get the actual image URL for one of them
img_title = 'File:Skaven Stormvermin.jpg'
url2 = f'{BASE}?action=query&titles={requests.utils.quote(img_title)}&prop=imageinfo&iiprop=url|size&format=json'
resp2 = session.get(url2, timeout=15)
data2 = resp2.json()
print('\nImage info for', img_title)
print(json.dumps(data2, indent=2)[:800])

# Also try pageimages prop to get the representative thumbnail
url3 = f'{BASE}?action=query&titles=Stormvermin&prop=pageimages&piprop=thumbnail&pithumbsize=600&format=json'
resp3 = session.get(url3, timeout=15)
data3 = resp3.json()
print('\nPageimages for Stormvermin:')
print(json.dumps(data3, indent=2)[:500])

# Try for more units
print('\n\nChecking more units:')
units = ['Stormvermin', 'Clanrats', 'Hell_Pit_Abomination', 'Rat_Ogors', 'Plague_Monks',
         'Saurus_Warriors', 'Stegadon', 'Slann_Starmaster']
for unit in units:
    url_p = f'{BASE}?action=query&titles={unit}&prop=pageimages&piprop=thumbnail&pithumbsize=600&format=json'
    r = session.get(url_p, timeout=15)
    d = r.json()
    pages = d.get('query', {}).get('pages', {})
    for pid, page in pages.items():
        thumb = page.get('thumbnail', {})
        missing = page.get('missing') == ''
        print(f'  {unit}: missing={missing} thumb={thumb.get("source", "none")[:80]}')
