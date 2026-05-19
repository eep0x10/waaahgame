"""Debug: try different UAs and approaches."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
from bs4 import BeautifulSoup

BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

session = requests.Session()
session.headers.update({
    'User-Agent': BROWSER_UA,
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.9',
})

urls = [
    ('fandom', 'https://ageofsigmar.fandom.com/wiki/Stormvermin'),
    ('lexicanum', 'https://ageofsigmar.lexicanum.com/wiki/Stormvermin'),
    ('warhammer-wiki', 'https://www.warhammer-community.com/en-gb/faction/skaven/'),
]

for label, url in urls:
    try:
        resp = session.get(url, timeout=20, allow_redirects=True)
        print(f'[{label}] {url[:60]} -> HTTP {resp.status_code} len={len(resp.text)}')
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, 'html.parser')
            title = soup.find('title')
            print(f'  title: {title.text[:80] if title else "none"}')
            imgs = soup.find_all('img')
            print(f'  imgs: {len(imgs)}')
            for img in imgs[:8]:
                src = img.get('data-src') or img.get('src') or ''
                if src:
                    print(f'    {src[:100]}')
        else:
            print(f'  body preview: {resp.text[:200]}')
    except Exception as e:
        print(f'[{label}] EXCEPTION: {type(e).__name__}: {e}')
