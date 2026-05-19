"""Debug: show actual exception from fandom fetch."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests

WIKI_UA = 'waaahgame/0.2 (educational; contact: yhextt@gmail.com)'
session = requests.Session()
session.headers.update({'User-Agent': WIKI_UA})

urls_to_test = [
    'https://ageofsigmar.fandom.com/wiki/Stormvermin',
    'https://ageofsigmar.lexicanum.com/wiki/Stormvermin',
    'https://warhammer.fandom.com/wiki/Stormvermin',
    'https://ageofsigmar.fandom.com/wiki/Skaven',
]

for url in urls_to_test:
    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
        print(f'{url[:60]} -> HTTP {resp.status_code} len={len(resp.text)}')
        if resp.status_code == 200:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.find('title')
            print(f'  title: {title.text[:80] if title else "none"}')
            imgs = soup.find_all('img')
            print(f'  imgs: {len(imgs)}')
            for img in imgs[:5]:
                src = img.get('data-src') or img.get('src') or ''
                print(f'    {src[:100]}')
    except Exception as e:
        print(f'{url[:60]} -> EXCEPTION: {type(e).__name__}: {e}')
