import re
import requests
import cloudscraper
from bs4 import BeautifulSoup
import json
import os
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_FILE = os.path.join(os.path.dirname(__file__), "movies_cache.json")
CACHE_VERSION = "6"

class IMDbMovieCrawler:
    def __init__(self):
        self.url = "https://www.imdb.com/chart/top/"
        self.movies = []
        self.movies_dict = {}  # Store movies by ID for quick lookup
        # Use cloudscraper to bypass IMDb Cloudflare protection (HTTP 202 errors)
        self.scraper = cloudscraper.create_scraper(
            browser={
                'browser': 'chrome',
                'platform': 'darwin',
                'desktop': True
            }
        )
        self.scraper.headers.update({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'Accept-Language': 'en-US,en;q=0.9',
            'Cache-Control': 'max-age=0',
            'DNT': '1',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        })
    
    #I add to load and save the cache
    def load_cache(self) -> bool:
        """Load movies from disk cache. Returns True if cache is valid."""
        if not os.path.exists(CACHE_FILE):
            return False
        try:
            with open(CACHE_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if data.get("version") != CACHE_VERSION:
                print("Cache version mismatch re-crawling")
                return False
            movies = data.get("movies", [])
            if not movies:
                return False
            self.movies = movies
            self.movies_dict = {m["id"]: m for m in movies if m.get("id")}
            print(f"Loaded {len(self.movies)} movies from disk cache (instant!)")
            return True
        except Exception as e:
            print(f"Cache load failed ({e}) re-crawling")
            return False

    def save_cache(self):
        """Persist movies list to disk so next restart is instant."""
        try:
            with open(CACHE_FILE, "w", encoding="utf-8") as f:
                json.dump({"version": CACHE_VERSION, "movies": self.movies}, f,
                          ensure_ascii=False, indent=2)
            print(f"Cache saved {CACHE_FILE}")
        except Exception as e:
            print(f"Could not save cache: {e}")
    
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling using Cloudscraper to bypass bot protection"""
        try:
            response = self.scraper.get(url, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def extract_movie_id(self, url: str) -> Optional[str]:
        """Extract IMDb movie ID from URL
        Pattern: /title/(tt followed by digits)"""
        match = re.search(r'/title/(tt\d+)', url) #<-- this is regular lang
        return match.group(1) if match else None
    
    def extract_year(self, text: str) -> Optional[int]:
        """Find a 4-digit year (1900-2099) anywhere in a string."""
        match = re.search(r'\b(19\d{2}|20\d{2})\b', text) #<-- this is regular lang
        return int(match.group(1)) if match else None

    def extract_runtime_minutes(self, text: str) -> Optional[int]:
        """Convert '2 hours 22 minutes' or '142 minutes' or '2h 22m' → int minutes.
        Uses multiple named-group patterns to handle varied IMDb formats.
        """
        # e.g. 2 hours 22 minutes
        m = re.search(r'(?P<h>\d+)\s*hour[s]?\s*(?P<m>\d+)\s*minute[s]?', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group('h')) * 60 + int(m.group('m'))
        
        # e.g. 2 hours
        m = re.search(r'(?P<h>\d+)\s*hour[s]?', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group('h')) * 60
        
        # e.g. 142 minutes
        m = re.search(r'(?P<m>\d+)\s*minute[s]?', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group('m'))
        
        # e.g. 2h 22m
        m = re.search(r'(?P<h>\d+)h\s*(?P<m>\d+)m', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group('h')) * 60 + int(m.group('m'))
        return None
    
    def extract_money_usd(self, text: str) -> Optional[int]:
        """Extract a dollar amount and return it as an integer.
        Handles:  $1,234,567  /  $1.2 million  /  $500 thousand
        Uses re to strip symbols, separators, and scale words.
        """
        text = text.strip()
        # "$ 1,234,567" or "$1,234,567"
        m = re.search(r'\$\s*([\d,]+)', text) #<-- this is regular lang
        if m:
            return int(re.sub(r',', '', m.group(1)))
        
        # "$1.2 million"
        m = re.search(r'\$\s*([\d.]+)\s*million', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(float(m.group(1)) * 1_000_000)
        
        # "$500 thousand"
        m = re.search(r'\$\s*([\d.]+)\s*thousand', text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(float(m.group(1)) * 1_000)
        return None
    
    def extract_oscar_count(self, awards_text: str) -> int:
        """Count Oscar wins mentioned in an awards string.
        Patterns handled:
          "Won 7 Oscars"  /  "Won 1 Oscar"  /  "1 win (Academy Award)"
        """
        m = re.search(r'Won\s+(\d+)\s+Oscar', awards_text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group(1))
        
        m = re.search(r'(\d+)\s+win.*?Academy Award', awards_text, re.IGNORECASE) #<-- this is regular lang
        if m:
            return int(m.group(1))
        return 0
    
    def extract_language_from_text(self, text: str) -> Optional[str]:
        """Detect a spoken language mentioned in plot or details text.
        Looks for explicit language markers with a word-boundary assertion
        so 'Spanish' isn't matched inside 'Francophones'.
        """
        known = [
            'English', 'French', 'German', 'Italian', 'Spanish', 'Japanese',
            'Korean', 'Mandarin', 'Cantonese', 'Hindi', 'Portuguese', 'Russian',
            'Arabic', 'Swedish', 'Danish', 'Norwegian', 'Latin', 'Hebrew',
            'Persian', 'Turkish', 'Polish', 'Dutch',
        ]
        pattern = re.compile(
            r'\b(' + '|'.join(known) + r')\b', re.IGNORECASE #<-- this is regular lang
        )
        match = pattern.search(text)
        return match.group(1).capitalize() if match else None
    
    def clean_title(self, raw_title: str) -> str:
        """Strip rank numbers from titles like '1. The Shawshank Redemption'.
        Uses re to remove a leading  '<digits>. ' prefix.
        """
        cleaned = re.sub(r'^\d+\.\s*', '', raw_title.strip()) #<-- this is regular lang
        cleaned = cleaned.replace('&apos;', "'").replace('&amp;', '&').replace('&quot;', '"') #<-- this is for cleaning html entities
        return cleaned
    
    def normalize_certificate(self, cert: str) -> str:
        """Map raw IMDb certificate strings to standard labels via re.

        e.g. 'TV-14' → 'TV-14', 'Not Rated' → 'NR', bare digits → 'Unrated'
        """
        if not cert:
            return 'NR'
        # Already a known label
        if re.match(r'^(G|PG|PG-13|R|NC-17|TV-G|TV-PG|TV-14|TV-MA|NR|Approved|Passed|Unrated)$',
                    cert, re.IGNORECASE): #<-- this is regular lang
            return cert.upper()
        # "Not Rated" / "Unrated"
        if re.search(r'not\s+rated|unrated', cert, re.IGNORECASE): #<-- this is regular lang
            return 'NR'
        return cert
    
    def fetch_top_movies(self):
        """Fetch IMDb Top 150 movies list"""
        if self.load_cache(): #<-- this is for cache 
            return True
        
        print("Fetching IMDb Top 150 movies...")
        html = self.fetch_page(self.url)
        if not html:
            return False
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # 1. Try JSON-LD extraction first (Fastest)
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'itemListElement' in data:
                    self._extract_from_json(data)
                    break
            except Exception:
                continue

        # 2. Try NEXT_DATA extraction (Best for Credits/Directors in bulk)
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            try:
                next_data = json.loads(next_data_script.string)
                # re: find edges in the deep nest
                # Modern path: props -> pageProps -> pageData -> chartTitles -> edges
                # or props -> pageProps -> mainColumnData -> ...
                def find_edges(d):
                    if not isinstance(d, dict): return None
                    if 'edges' in d and isinstance(d['edges'], list): return d['edges']
                    for k, v in d.items():
                        res = find_edges(v)
                        if res: return res
                    return None
                
                edges = find_edges(next_data.get('props', {}))
                if edges:
                    print(f"Found {len(edges)} movies in NEXT_DATA. Extracting metadata...")
                    for edge in edges:
                        node = edge.get('node', {})
                        mid = node.get('id')
                        if mid and mid in self.movies_dict:
                            movie = self.movies_dict[mid]
                            
                            # Extract Rating
                            if not movie.get('rating'):
                                rs = node.get('ratingsSummary', {})
                                if rs.get('aggregateRating'):
                                    movie['rating'] = float(rs['aggregateRating'])
                            
                            # Extract Plot
                            if not movie.get('plot'):
                                p = node.get('plot', {})
                                if p.get('plotText', {}).get('plainText'):
                                    movie['plot'] = p['plotText']['plainText']
                            
                            # Extract Runtime
                            if not movie.get('runtime_minutes'):
                                r = node.get('runtime', {})
                                if r.get('seconds'):
                                    movie['runtime_minutes'] = r['seconds'] // 60
                                    movie['runtime'] = f"{movie['runtime_minutes'] // 60}h {movie['runtime_minutes'] % 60}m"
                            
                            # Extract Certificate
                            if not movie.get('certificate'):
                                c = node.get('certificate', {})
                                if c.get('rating'):
                                    movie['certificate'] = self.normalize_certificate(c['rating'])

                            # Extract Directors and Stars (if present)
                            credits = node.get('principalCreditsV2', []) or node.get('principalCredits', [])
                            for group in credits:
                                label = ""
                                if isinstance(group, dict):
                                    label = group.get('grouping', {}).get('text', '').lower() or \
                                            group.get('category', {}).get('text', '').lower()
                                    active_credits = group.get('credits', [])
                                    names = [c.get('name', {}).get('nameText', {}).get('text') for c in active_credits]
                                    names = [n for n in names if n]
                                    
                                    if 'director' in label:
                                        movie['director'] = names
                                    elif 'star' in label or 'actor' in label:
                                        movie['cast'] = [{"name": n} for n in names]
            except Exception as e:
                print(f"Error parsing NEXT_DATA: {e}")
        
        # 3. Supplemental HTML parsing for Year, Runtime, Certificate from Chart rows
        print("Running HTML extraction for supplementary data...")
        self._extract_from_html(soup)
        
        if len(self.movies) > 0:
            # Sort by rank and limit
            self.movies.sort(key=lambda x: x.get('rank', 999))
            self.movies = self.movies[:150]
            self.save_cache()
            return True
            
        return False
    
    def _extract_from_json(self, data: dict):
        """Extract movies from JSON-LD structured data"""
        print("Found JSON-LD data. Extracting basic info...")
        
        items = data.get('itemListElement', [])
        
        for item in items:
            try:
                movie_item = item.get('item', {})
                movie_data = {
                    'rank':  item.get('position', 0),
                    'title': self.clean_title(movie_item.get('name', 'N/A')),
                }

                url = movie_item.get('url', '')
                if url:
                    movie_data['url'] = (
                        f"https://www.imdb.com{url}" if url.startswith('/') else url
                    )
                    movie_data['id'] = self.extract_movie_id(movie_data['url'])

                if movie_item.get('image'):
                    movie_data['poster'] = movie_item['image']

                rating_data = movie_item.get('aggregateRating', {})
                if rating_data.get('ratingValue'):
                    movie_data['rating'] = float(rating_data['ratingValue'])

                # Enhanced extraction from JSON-LD
                if movie_item.get('genre'):
                    raw_genre = movie_item['genre']
                    if isinstance(raw_genre, list):
                        movie_data['genres'] = raw_genre
                    else:
                        # re: split by comma and clean
                        movie_data['genres'] = [g.strip() for g in re.split(r',', str(raw_genre))]

                if movie_item.get('description'):
                    movie_data['plot'] = movie_item['description']
                    # Try to get year from description if missing
                    if not movie_data.get('year'):
                        year = self.extract_year(movie_item['description'])
                        if year:
                            movie_data['year'] = year

                if movie_item.get('contentRating'):
                    movie_data['certificate'] = self.normalize_certificate(movie_item['contentRating'])

                if movie_item.get('duration'):
                    # ISO 8601 duration: PT2H22M
                    dur = movie_item['duration']
                    movie_data['runtime_iso'] = dur
                    # re: extract hours and minutes
                    hm = re.search(r'PT(?:(?P<h>\d+)H)?(?:(?P<m>\d+)M)?', dur)
                    if hm:
                        h = int(hm.group('h') or 0)
                        m = int(hm.group('m') or 0)
                        total_mins = h * 60 + m
                        if total_mins > 0:
                            movie_data['runtime_minutes'] = total_mins
                            movie_data['runtime'] = f"{h}h {m}m" if h > 0 else f"{m}min"

                # Mark as partially fetched so we don't ALWAYS need to visit detail page
                # but we'll still call it a fetch if we have genres and plot
                if movie_data.get('genres') and movie_data.get('plot'):
                    movie_data['details_fetched'] = True

                self.movies.append(movie_data)
                if movie_data.get('id'):
                    self.movies_dict[movie_data['id']] = movie_data
                
            except Exception as e:
                print(f"Error parsing movie: {e}")
                continue
        
        self.movies = self.movies[:150]
        self.movies_dict = {m['id']: m for m in self.movies if m.get('id')}
        print(f"Extracted {len(self.movies)} movies\n")
    
    def _extract_from_html(self, soup: BeautifulSoup):
        """Standard HTML scraping from the Top 250 chart page"""
        # Select all movie rows
        rows = soup.select('li.ipc-metadata-list-summary-item')
        print(f"Found {len(rows)} movie rows. Extracting metadata...")
        
        for i, row in enumerate(rows):
            try:
                # Title and ID extraction
                title_elem = row.select_one('h3.ipc-title__text')
                url_elem = row.select_one('a.ipc-title-link-wrapper')
                
                if not title_elem or not url_elem:
                    continue
                    
                raw_title = title_elem.get_text(strip=True)
                title = self.clean_title(raw_title)
                movie_url = "https://www.imdb.com" + url_elem.get('href', '').split('?')[0]
                movie_id = self.extract_movie_id(movie_url)
                
                if not movie_id:
                    continue

                # Use existing data from JSON-LD if available, otherwise create new
                movie_data = self.movies_dict.get(movie_id)
                if not movie_data:
                    movie_data = {
                        'id': movie_id,
                        'title': title,
                        'url': movie_url,
                        'rank': i + 1
                    }
                    self.movies.append(movie_data)
                    self.movies_dict[movie_id] = movie_data

                # Metadata extraction (Year, Runtime, Certificate)
                # re: find all cli-title-metadata-item spans
                metadata_items = row.select('span.cli-title-metadata-item')
                for item in metadata_items:
                    text = item.get_text(strip=True)
                    
                    # 1. Year: exactly 4 digits
                    if not movie_data.get('year'):
                        y = self.extract_year(text)
                        if y:
                            movie_data['year'] = y
                            continue
                    
                    # 2. Runtime: e.g., "2h 22m" or "121m"
                    if 'h' in text.lower() or 'm' in text.lower():
                        if not movie_data.get('runtime'):
                            movie_data['runtime'] = text
                            # re: parse runtime to minutes
                            rm = re.search(r'(?:(?P<h>\d+)h)?\s*(?:(?P<m>\d+)m|min)?', text.lower())
                            if rm:
                                h = int(rm.group('h') or 0)
                                m = int(rm.group('m') or 0)
                                movie_data['runtime_minutes'] = h * 60 + m
                            continue
                    
                    # 3. Certificate: typically remaining short item like "R", "PG-13"
                    if len(text) < 10 and not movie_data.get('certificate'):
                        # re: ensure it's not a year
                        if not re.match(r'^\d{4}$', text) and 'h' not in text.lower():
                            movie_data['certificate'] = self.normalize_certificate(text)

                # Rating (fallback if JSON-LD missed it)
                rating_elem = row.select_one('span.ipc-rating-star--rating')
                if rating_elem and not movie_data.get('rating'):
                    try:
                        movie_data['rating'] = float(rating_elem.get_text(strip=True))
                    except:
                        pass
                
                # Check for poster if missing
                if not movie_data.get('poster'):
                    img_elem = row.select_one('img.ipc-image')
                    if img_elem:
                        movie_data['poster'] = img_elem.get('src') or img_elem.get('data-src')

            except Exception as e:
                print(f"Error parsing row {i}: {e}")
                continue
        
        # Ensure we keep the limit
        self.movies = self.movies[:150]
        self.movies_dict = {m['id']: m for m in self.movies if m.get('id')}
        print(f"Final dataset: {len(self.movies)} movies\n")
    
    # this is fetch for detail page
    def fetch_movie_details(self, movie: dict) -> dict:
        """Fetch detailed information for a specific movie using the /reference endpoint
        which is typically not protected by AWS WAF challenges.
        """
        if not movie.get('url') or movie.get('details_fetched'):
            return movie

        # Use the /reference URL for full data and WAF bypass
        ref_url = movie['url'].rstrip('/') + '/reference'
        html = self.fetch_page(ref_url)
        if not html:
            print(f"FAILED to fetch: {ref_url}")
            return movie

        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract NEXT_DATA for robust structured data
        next_data_script = soup.find('script', id='__NEXT_DATA__')
        if next_data_script:
            try:
                data = json.loads(next_data_script.string)
                
                # Helper to find keys in deep nest
                def find_key(d, key):
                    if not isinstance(d, dict): return None
                    if key in d: return d[key]
                    for v in d.values():
                        res = find_key(v, key)
                        if res: return res
                    return None
                
                main_data = find_key(data, 'mainColumnData') or find_key(data, 'pageProps') or {}
                # Sometimes it's nested elsewhere in /reference
                if not main_data.get('productionBudget'):
                    # Fallback to searching the whole JSON
                    pass 

                # 1. Budget
                pb = find_key(data, 'productionBudget')
                if pb and pb.get('budget'):
                    amt = pb['budget'].get('amount')
                    curr = pb['budget'].get('currency', 'USD')
                    movie['budget'] = f"${amt:,}" if curr == 'USD' else f"{curr} {amt:,}"
                
                # 2. Box Office
                wg = find_key(data, 'worldwideGross')
                if wg and wg.get('total'):
                    amt = wg['total'].get('amount')
                    movie['box_office'] = f"${amt:,}"

                # 3. Awards
                wins_data = find_key(data, 'wins')
                noms_data = find_key(data, 'nominationsExcludeWins')
                pres_data = find_key(data, 'prestigiousAwardSummary')
                
                award_parts = []
                if pres_data and isinstance(pres_data, dict):
                    award_name = pres_data.get('award', {}).get('text', 'Award')
                    p_wins = pres_data.get('wins', 0)
                    p_noms = pres_data.get('nominations', 0)
                    if p_wins > 0:
                        award_parts.append(f"Won {p_wins} {award_name}{'s' if p_wins > 1 else ''}")
                    elif p_noms > 0:
                        award_parts.append(f"Nominated for {p_noms} {award_name}{'s' if p_noms > 1 else ''}")
                
                counts = []
                if wins_data and isinstance(wins_data, dict) and wins_data.get('total'): 
                    counts.append(f"{wins_data['total']} wins")
                if noms_data and isinstance(noms_data, dict) and noms_data.get('total'): 
                    counts.append(f"{noms_data['total']} nominations")
                
                if counts:
                    award_parts.append(" & ".join(counts) + " total")
                
                if award_parts:
                    movie['awards'] = ". ".join(award_parts)

                # 4. Genres
                gn_data = find_key(data, 'genres')
                if gn_data:
                    # Case 1: Dict with 'genres' key which is a list
                    if isinstance(gn_data, dict) and isinstance(gn_data.get('genres'), list):
                        movie['genres'] = [g.get('text') for g in gn_data['genres'] if isinstance(g, dict) and g.get('text')]
                    # Case 2: Direct list of genre objects
                    elif isinstance(gn_data, list):
                        movie['genres'] = [g.get('genre', {}).get('text') or g.get('text') for g in gn_data if isinstance(g, dict)]
                
                # Fallback to titleGenres
                if not movie.get('genres'):
                    tg = find_key(data, 'titleGenres')
                    if tg and isinstance(tg, list):
                        movie['genres'] = [g.get('genre', {}).get('text') or g.get('text') for g in tg if isinstance(g, dict)]
                
                if movie.get('genres'):
                    movie['genres'] = [g for g in movie['genres'] if g]

                # 4a. Release Date
                rd = find_key(data, 'releaseDate')
                if rd and isinstance(rd, dict):
                    y, m, d = rd.get('year'), rd.get('month'), rd.get('day')
                    if y and m and d:
                        import datetime
                        try:
                            dt = datetime.date(y, m, d)
                            movie['release_date'] = dt.strftime('%B %d, %Y')
                        except:
                            movie['release_date'] = f"{y}-{m:02d}-{d:02d}"

                # 5. Backdrop (Main Image)
                pi = find_key(data, 'primaryImage')
                if pi and isinstance(pi, dict) and pi.get('url'):
                    movie['backdrop'] = pi['url']
                
                # 6. Rating (if missing)
                rs = find_key(data, 'ratingsSummary')
                if rs and isinstance(rs, dict) and rs.get('aggregateRating'):
                    movie['rating'] = float(rs['aggregateRating'])
                
                # 7. Cast & Director (Categories)
                cats = find_key(data, 'categories')
                if cats and isinstance(cats, list):
                    for cat in cats:
                        if not isinstance(cat, dict): continue
                        cat_name = cat.get('name')
                        items = cat.get('section', {}).get('items', [])
                        
                        if cat_name == "Director":
                            directors = [item.get('rowTitle') for item in items if isinstance(item, dict) and item.get('rowTitle')]
                            if directors: movie['director'] = directors
                            
                        elif cat_name in ["Cast", "Stars"]:
                            cast = []
                            for item in items[:8]:
                                if not isinstance(item, dict): continue
                                name = item.get('rowTitle')
                                img = item.get('imageProps', {}).get('imageModel', {}).get('url')
                                if name:
                                    cast.append({"name": name, "img": img or ""})
                            if cast: movie['cast'] = cast

                # 8. Plot
                p = find_key(data, 'plot')
                if p and p.get('plotText', {}).get('plainText'):
                    movie['plot'] = p['plotText']['plainText']

                # 9. Runtime
                rt = find_key(data, 'runtime')
                if rt and rt.get('seconds'):
                    s = rt['seconds']
                    movie['runtime_minutes'] = s // 60
                    movie['runtime'] = f"{s // 3600}h {(s % 3600) // 60}m"

            except Exception as e:
                print(f"Error parsing NEXT_DATA from reference page: {e}")

        # Final backup to HTML if NEXT_DATA missed anything (re usage)
        if not movie.get('plot'):
            plot_elem = soup.select_one('[data-testid="plot-xl"]') or soup.select_one('.ipc-metadata-list-item__list-content-item')
            if plot_elem:
                movie['plot'] = plot_elem.get_text(strip=True)

        movie['details_fetched'] = True
        time.sleep(0.3)
        return movie
    
    def fetch_movies_details_parallel(self, movies: List[dict], max_workers: int = 10) -> None:
        """Fetch details for multiple movies in parallel using multithreading"""
        movies_to_fetch = [m for m in movies if not m.get('details_fetched')]
        
        if not movies_to_fetch:
            return
        
        total = len(movies_to_fetch)
        print(f"\nFetching details for {total} movies using {max_workers} parallel threads...")
        
        completed = 0
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            # Submit all tasks
            future_to_movie = {executor.submit(self.fetch_movie_details, movie): movie for movie in movies_to_fetch}
            
            # Process results as they complete
            for future in as_completed(future_to_movie):
                completed += 1
                if completed % 10 == 0 or completed == total:
                    print(f"Progress: {completed}/{total} movies fetched ({int(completed/total*100)}%)")
        
        print(f"Completed fetching details for {total} movies\n")
        self.save_cache() #<-- save to disk so next run is instant
    
    def filter_movies(self, filters: dict) -> List[dict]:
        """Filter movies based on user criteria"""
        filtered = self.movies.copy()
        
        # Filter by genres using regex
        if filters.get('genres'):
            target_genres = filters['genres']
            genre_pattern = re.compile(r'\b(' + '|'.join(target_genres) + r')\b', re.IGNORECASE)
            
            # Fetch details in parallel for genre filtering
            self.fetch_movies_details_parallel(filtered, max_workers=15)
            
            filtered = [
                m for m in filtered 
                if 'genres' in m and genre_pattern.search(', '.join(m['genres']))
            ]
        
        # Filter by year range
        year_start = filters.get('year_start', 0)
        year_end   = filters.get('year_end',   9999)
        if filters.get('year_start') or filters.get('year_end'):
            filtered = [m for m in filtered
                        if year_start <= (m.get('year') or 0) <= year_end]
        
        # Filter by rating range
        if filters.get('min_rating') is not None:
            filtered = [
                m for m in filtered 
                if 'rating' in m and m['rating'] >= filters['min_rating']
            ]
        
        if filters.get('max_rating') is not None:
            filtered = [
                m for m in filtered 
                if 'rating' in m and m['rating'] <= filters['max_rating']
            ]
        
        return filtered
    
    def sort_alphabetically(self, movies: List[dict]) -> List[dict]:
        """Sort movies alphabetically by title (A-Z)"""
        return sorted(movies, key=lambda x: x.get('title', '').lower())
    
    def search_by_name(self, search_term: str) -> List[dict]:
        """Case-insensitive regex search across title, genres, country, language."""
        if not search_term:
            return []
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        return [
            m for m in self.movies
            if pattern.search(m.get('title', ''))
            or pattern.search(' '.join(m.get('genres', [])))
            or pattern.search(m.get('country', ''))
            or pattern.search(m.get('language', ''))
        ]
    
    def get_movie_by_id(self, movie_id: str) -> Optional[dict]:
        return self.movies_dict.get(movie_id)
    
    def display_movies_list(self, movies: List[dict]):
        """Display filtered movies in list format"""
        if not movies:
            print("\nNo movies found matching your criteria.\n")
            return
        
        # Sort alphabetically
        sorted_movies = self.sort_alphabetically(movies)
        
        # Fetch missing country info in parallel if needed
        movies_needing_country = [m for m in sorted_movies if not m.get('country') and not m.get('details_fetched')]
        if movies_needing_country:
            self.fetch_movies_details_parallel(movies_needing_country, max_workers=10)
        
        print("\n{'='*88}")
        print(f"{'FILTERED MOVIES (A-Z)':^88}")
        print("{'='*88}\n")
        print(f"Found {len(sorted_movies)} movie(s)\n")
        
        for idx, movie in enumerate(sorted_movies, 1):
            # Ensure country is fetched
            if not movie.get('country') and not movie.get('details_fetched'):
                self.fetch_movie_details(movie)
            
            print(f"{idx}. {movie.get('title', 'N/A')}")
            print(f"ID: {movie.get('id', 'N/A')}")
            print(f"Country: {movie.get('country', 'N/A')}")
            print(f"Year: {movie.get('year', 'N/A')}")
            print(f"IMDb: {movie.get('rating', 'N/A')}/10")
            if movie.get('poster'):
                print(f"Poster: {movie['poster']}")
            if movie.get('genres'):
                print(f"Genres: {', '.join(movie['genres'])}")
            print()
    
    def display_movie_details(self, movie: dict):
        """Display comprehensive movie details"""
        # Fetch details if not already fetched
        if not movie.get('details_fetched'):
            movie = self.fetch_movie_details(movie)
        
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'N/A')
        
        print("\n{'='*88}")
        print(f"{title.upper()} ({year})".center(88) )
        print("{'='*88}\n")
        
        for label, key in [
            ('IMDb Score',   'rating'),
            ('Runtime',      'runtime'),
            ('Runtime (min)','runtime_minutes'),
            ('Certificate',  'certificate'),
            ('Country',      'country'),
            ('Language',     'language'),
            ('Release Date', 'release_date_clean'),
            ('Budget',       'budget'),
            ('Box Office',   'box_office'),
            ('Metascore',    'metascore'),
            ('Oscar Wins',   'oscar_wins'),
            ('Total Wins',   'total_wins'),
            ('Nominations',  'total_nominations'),
            ('Awards',       'awards'),
        ]:
            val = movie.get(key)
            if val is not None:
                print(f"  {label:<20}: {val}")

        if movie.get('poster'):
            print(f"POSTER: {movie['poster']}\n")
        
        if movie.get('plot'):
            print(f"PLOT SUMMARY:")
            print(f"   {movie['plot']}\n")
        
        if movie.get('cast'):
            print(f"CAST:")
            for actor in movie['cast']:
                print(f"   • {actor}")
            print()
        
        if movie.get('director'):
            directors = ', '.join(movie['director']) if isinstance(movie['director'], list) else movie['director']
            print(f"DIRECTOR: {directors}\n")
        
        if movie.get('genres'):
            genres = ', '.join(movie['genres']) if isinstance(movie['genres'], list) else movie['genres']
            print(f"GENRES: {genres}\n")
        
        if movie.get('certificate'):
            print(f"RATING: {movie['certificate']}\n")
        
        if movie.get('budget'):
            print(f"BUDGET: {movie['budget']}\n")
        
        if movie.get('box_office'):
            print(f"WORLDWIDE BOX OFFICE: {movie['box_office']}\n")
        
        if movie.get('runtime'):
            print(f"RUNTIME: {movie['runtime']}\n")
        
        if movie.get('release_date'):
            print(f"RELEASE DATE: {movie['release_date']}\n")
        
        if movie.get('rating'):
            print(f"IMDb SCORE: {movie['rating']}/10\n")
        
        if movie.get('metascore'):
            print(f"METASCORE: {movie['metascore']}/100\n")
        
        if movie.get('awards'):
            print(f"AWARDS: {movie['awards']}\n")
        
        if movie.get('country'):
            print(f"COUNTRY: {movie['country']}\n")
        
        print("─" * 90)
    
    def get_movie_by_id(self, movie_id: str) -> Optional[dict]:
        """Get movie by IMDb ID"""
        return self.movies_dict.get(movie_id)
    
    def search_by_name(self, search_term: str) -> List[dict]:
        """Search movies by name using regex pattern matching"""
        if not search_term:
            return []
        
        # Create case-insensitive regex pattern
        pattern = re.compile(re.escape(search_term), re.IGNORECASE)
        
        # Search through all movies
        matches = []
        for movie in self.movies:
            title = movie.get('title', '')
            if pattern.search(title):
                matches.append(movie)
        
        return matches
    
    def get_user_filters(self) -> dict:
        """Get filter criteria from user input"""
        print("\n" + "="*90)
        print(" " * 30 + "IMDb TOP 250 MOVIE FILTER")
        print("="*90)
        print("\nEnter your filter criteria (press Enter to skip any filter):\n")
        
        filters = {}
        
        # Genre selection
        print("Filter by Genres:")
        print("Available: Action, Comedy, Drama, Sci-Fi")
        genre_input = input("Enter genres (comma-separated): ").strip()
        if genre_input:
            genres = [g.strip() for g in genre_input.split(',')]
            # Validate genres match the options
            valid_genres = []
            for genre in genres:
                if re.search(r'\b\w+\b', g, re.IGNORECASE): #<-- this is regular lang
                    valid_genres.append(genre)
            if valid_genres:
                filters['genres'] = valid_genres
        
        # Year range
        year_start = input("\nYear from (e.g., 1990): ").strip()
        if year_start and year_start.isdigit():
            filters['year_start'] = int(year_start)
        
        year_end = input("Year to (e.g., 2024): ").strip()
        if year_end and year_end.isdigit():
            filters['year_end'] = int(year_end)
        
        # Rating range
        min_rating = input("\nMinimum IMDb rating (1-10): ").strip()
        if min_rating:
            try:
                filters['min_rating'] = float(min_rating)
            except ValueError:
                print("Invalid rating, skipping...")
        
        max_rating = input("Maximum IMDb rating (1-10): ").strip()
        if max_rating:
            try:
                filters['max_rating'] = float(max_rating)
            except ValueError:
                print("Invalid rating, skipping...")
        
        return filters
    
    def interactive_menu(self):
        """Main interactive menu"""
        while True:
            print("\n" + "="*90)
            print(" "*35 + "MAIN MENU")
            print("="*90)
            print("\n1. Filter and display movies")
            print("2. Search movie by name")
            print("3. View movie details by ID")
            print("4. Exit")
            
            choice = input("\nSelect an option (1-4): ").strip()
            
            if choice == '1':
                filters = self.get_user_filters()
                filtered = self.filter_movies(filters)
                self.display_movies_list(filtered)
                
            elif choice == '2':
                search_term = input("\nEnter movie name (or part of it): ").strip()
                if search_term:
                    results = self.search_by_name(search_term)
                    if results:
                        print(f"\nFound {len(results)} movie(s) matching '{search_term}'")
                        self.display_movies_list(results)
                    else:
                        print(f"\nNo movies found matching '{search_term}'.\n")
                else:
                    print("\nPlease enter a search term.\n")
                
            elif choice == '3':
                movie_id = input("\nEnter IMDb ID (e.g., tt0111161): ").strip()
                movie = self.get_movie_by_id(movie_id)
                if movie:
                    self.display_movie_details(movie)
                else:
                    print(f"\nMovie with ID '{movie_id}' not found in Top 250.\n")
                    
            elif choice == '4':
                print("\nThank you for using IMDb Movie Crawler!\n")
                break
                
            else:
                print("\nInvalid option. Please select 1-4.\n")
    
    def run(self):
        """Main execution method"""
        print("\n" + "="*90)
        print(" " * 25 + "IMDb TOP 150 MOVIE CRAWLER")
        print("="*90 + "\n")
        
        # Fetch movie list
        if not self.fetch_top_movies():
            print("Failed to fetch movies. Please check your internet connection.\n")
            return
        
        if not self.movies:
            print("No movies extracted. Please try again later.\n")
            return
        
        print(f"Successfully loaded {len(self.movies)} movies from IMDb Top 150\n")
        
        # Start interactive menu
        self.interactive_menu()


if __name__ == "__main__":
    try:
        crawler = IMDbMovieCrawler()
        crawler.run()
    except KeyboardInterrupt:
        print("\n\n✓ Program terminated by user.\n")
    except Exception as e:
        print(f"\n✗ An error occurred: {e}\n")
        import traceback
        traceback.print_exc()
