import json
import re

def parse_debug():
    with open('debug.html', 'r', encoding='utf-8') as f:
        html = f.read()
    
    match = re.search(r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>', html, re.DOTALL)
    if not match:
        print("❌ NEXT_DATA NOT FOUND")
        return

    data = json.loads(match.group(1))
    print("✅ FOUND NEXT_DATA")
    
    # Try finding mainColumnData anywhere
    def find_key(d, key):
        if not isinstance(d, dict): return None
        if key in d: return d[key]
        for v in d.values():
            res = find_key(v, key)
            if res: return res
        return None
    
    main_data = find_key(data, 'mainColumnData') or {}

    print("Main Keys:", list(main_data.keys()) if main_data else "None")
    
    budget = main_data.get('productionBudget')
    gross = main_data.get('worldwideGross')
    rd = main_data.get('releaseDate')
    print(f"Release Date: {rd}")
    
    gn = main_data.get('genres')
    print(f"Genres: {gn}")
    
    cats = main_data.get('categories')
    if cats:
        print(f"Categories: {len(cats)}")
        for i, cat in enumerate(cats):
            name = cat.get('name')
            items = cat.get('section', {}).get('items', [])
            print(f"  [{i}] Name: {name}, Items: {len(items)}")
            if name == "Director":
                if items:
                    print(f"    Full Item Structure: {items[0]}")

if __name__ == "__main__":
    parse_debug()
