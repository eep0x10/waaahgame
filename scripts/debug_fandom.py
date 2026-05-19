"""Debug script: test fandom fetch for a single unit."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import requests
from scripts.scrape_wiki_images import (
    WIKI_UA, FANDOM_BASE, _name_to_wiki_slug, _get_html,
    _scrape_fandom, _scrape_lexicanum
)
from bs4 import BeautifulSoup

session = requests.Session()
session.headers.update({'User-Agent': WIKI_UA})

name = 'Stormvermin'
wiki_slug = _name_to_wiki_slug(name)
url = FANDOM_BASE.format(wiki_slug)
print('URL:', url)
html = _get_html(url, session)
if not html:
    print('FETCH FAILED - html is None')
else:
    print('HTML len:', len(html))
    soup = BeautifulSoup(html, 'html.parser')
    # Show page title
    title = soup.find('title')
    print('Title:', title.text if title else 'none')
    # Show aside/infobox
    aside = soup.find('aside')
    print('aside:', aside is not None)
    # Find all img tags
    imgs = soup.find_all('img')
    print('Total imgs:', len(imgs))
    for img in imgs[:10]:
        src = img.get('data-src') or img.get('src') or ''
        print('  IMG src:', src[:120])

print()
print('Testing _scrape_fandom:')
img_url, page_url = _scrape_fandom(name, session)
print('Result:', img_url, page_url)
