"""Debug: try Fandom MediaWiki API (not blocked by Cloudflare browser check)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import requests
import json

BROWSER_UA = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36'

session = requests.Session()
session.headers.update({'User-Agent': BROWSER_UA})

# Fandom MediaWiki API - much more likely to bypass Cloudflare JS challenge
# API endpoints (not HTML pages) often bypass browser JS checks

test_urls = [
    # Fandom MediaWiki API - get page images
    'https://ageofsigmar.fandom.com/api.php?action=query&titles=Stormvermin&prop=images&format=json',
    # Fandom MediaWiki API - get page content (wikitext)
    'https://ageofsigmar.fandom.com/api.php?action=query&titles=Stormvermin&prop=revisions&rvprop=content&format=json&rvslots=main',
    # Fandom v2 API - article details with image
    'https://ageofsigmar.fandom.com/api/v1/Articles/Details?titles=Stormvermin',
    # Fandom Wikia API - thumbnail
    'https://ageofsigmar.fandom.com/api/v1/Articles/AsSimpleJson?id=1',
    # Open source warhammer wiki (1d4chan)
    'https://1d4chan.org/wiki/Skaven',
    # warhammer wiki (sigmarwiki?) - lesser-known
    'https://sigmarwiki.com/wiki/Stormvermin',
]

for url in test_urls:
    try:
        resp = session.get(url, timeout=15, allow_redirects=True)
        print(f'HTTP {resp.status_code} len={len(resp.text):>7} -> {url[:80]}')
        if resp.status_code == 200:
            # Show a bit of content
            ct = resp.headers.get('content-type', '')
            if 'json' in ct:
                try:
                    data = resp.json()
                    print(f'  JSON keys: {list(data.keys())[:6]}')
                except Exception:
                    pass
            else:
                preview = resp.text[:200].replace('\n', ' ')
                print(f'  preview: {preview}')
    except Exception as e:
        print(f'EXCEPTION: {type(e).__name__}: {e}  -> {url[:80]}')
