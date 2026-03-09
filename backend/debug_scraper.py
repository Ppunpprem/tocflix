import cloudscraper
import sys
from bs4 import BeautifulSoup

def debug_fetch(url):
    import requests
    session = requests.Session()
    headers = {
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'Accept-Language': 'en-US,en;q=0.9',
        'Cache-Control': 'max-age=0',
        'DNT': '1',
        'Upgrade-Insecure-Requests': '1',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    
    # 1. Hit awards page to get session/cookies
    awards_url = url.rstrip('/') + '/awards'
    print(f"Step 1: Fetching {awards_url}...")
    r1 = session.get(awards_url, headers=headers, timeout=15)
    print(f"Awards Status: {r1.status_code}")
    
    # 2. Hit main page
    print(f"Step 2: Fetching {url} with same session...")
    try:
        response = session.get(url, headers=headers, timeout=15)
        print(f"Status Code: {response.status_code}")
        with open('debug.html', 'w') as f:
            f.write(response.text)
        print(f"HTML saved to debug.html (Length: {len(response.text)})")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        debug_fetch(sys.argv[1])
    else:
        debug_fetch("https://www.imdb.com/title/tt0068646/")
