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
    
    # Check for budget and gross
    # The subagent said it's under props.pageProps.mainColumnData
    main_data = data.get('props', {}).get('pageProps', {}).get('mainColumnData', {})
    if not main_data:
        # Try finding anywhere
        def find_key(d, key):
            if not isinstance(d, dict): return None
            if key in d: return d[key]
            for v in d.values():
                res = find_key(v, key)
                if res: return res
            return None
        
        main_data = find_key(data, 'mainColumnData') or {}

    print("Main Keys:", main_data.keys() if main_data else "None")
    
    budget = main_data.get('productionBudget')
    gross = main_data.get('worldwideGross')
    awards = data.get('props', {}).get('pageProps', {}).get('awards') or find_key(data, 'awards')
    
    print(f"Budget: {budget}")
    print(f"Worldwide Gross: {gross}")
    print(f"Awards Fragment: {awards}")

if __name__ == "__main__":
    parse_debug()
