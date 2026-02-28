import re
import requests
from bs4 import BeautifulSoup
import json
import os
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

CACHE_FILE = os.path.join(os.path.dirname(__file__), "movies_cache.json")
CACHE_VERSION = "3"

class IMDbMovieCrawler:
    def __init__(self):
        self.url = "https://www.imdb.com/chart/top/"
        self.movies = []
        self.movies_dict = {}  # Store movies by ID for quick lookup
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept-Language': 'en-US,en;q=0.9',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        }
    
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
        """Fetch a web page with error handling"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
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
        
        # Try JSON-LD extraction first coz to be faster
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'itemListElement' in data:
                    self._extract_from_json(data)
                    return True
            except Exception:
                continue
        
        # Fallback to HTML parsing
        self._extract_from_html(soup)
        return len(self.movies) > 0
    
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

                desc = movie_item.get('description', '')
                if desc:
                    year = self.extract_year(desc)
                    if year:
                        movie_data['year'] = year
                
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
        """Fallback HTML extraction method"""
        movie_items = soup.find_all('li', class_=re.compile(r'ipc-metadata-list-summary-item'))
        
        print(f"Found {len(movie_items)} movie items. Extracting...\n")
        
        for idx, item in enumerate(movie_items, 1):
            try:
                movie_data = {'rank': idx}

                title_elem = item.find('h3', class_=re.compile(r'ipc-title'))
                if title_elem:
                    movie_data['title'] = self.clean_title(title_elem.get_text(strip=True))

                link = item.find('a', href=re.compile(r'/title/tt\d+/'))
                if link and link.get('href'):
                    movie_data['url'] = f"https://www.imdb.com{link['href']}"
                    movie_data['id']  = self.extract_movie_id(movie_data['url'])

                img = item.find('img', class_='ipc-image')
                if img and img.get('src'):
                    movie_data['poster'] = img['src']

                for meta in item.find_all('span', class_=re.compile(r'cli-title-metadata-item')):
                    text = meta.get_text(strip=True)
                    if re.match(r'^\d{4}$', text):
                        movie_data['year'] = int(text)

                rating_elem = item.find('span', class_=re.compile(r'ipc-rating-star'))
                if rating_elem:
                    rm = re.search(r'(\d+\.?\d*)', rating_elem.get_text(strip=True)) #<-- here regular lang
                    if rm:
                        movie_data['rating'] = float(rm.group(1))
                
                if 'title' in movie_data:
                    self.movies.append(movie_data)
                    if movie_data.get('id'):
                        self.movies_dict[movie_data['id']] = movie_data
                    
            except Exception as e:
                print(f"Error parsing movie {idx}: {e}")
                continue
        
        self.movies = self.movies[:150]
        self.movies_dict = {m['id']: m for m in self.movies if m.get('id')}
        print(f"Extracted {len(self.movies)} movies\n")
    
    # this is fetch for detail page
    def fetch_movie_details(self, movie: dict) -> dict:
        """Fetch detailed information for a specific movie"""
        if not movie.get('url') or movie.get('details_fetched'):
            return movie

        html = self.fetch_page(movie['url'])
        if not html:
            return movie

        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract year
        if not movie.get('year'):
            year_elem = soup.select_one('[data-testid="hero-title-block__metadata"] a')
            if year_elem:
                y = self.extract_year(year_elem.get_text())
                if y:
                    movie['year'] = y
        
        # Extract genres
        genres = []
        for chip in soup.select('a.ipc-chip span.ipc-chip__text')[:10]:
            g = chip.get_text(strip=True)
            if g and len(g) < 20:
                genres.append(g)
        if genres:
            movie['genres'] = genres
        
        # Extract country
        country_elem = soup.select_one('[data-testid="title-details-origin"] a')
        if country_elem:
            movie['country'] = country_elem.get_text(strip=True)
        
        # Extract plot
        plot_elem = (
            soup.select_one('[data-testid="plot-xl"]') or
            soup.select_one('[data-testid="plot-l"]') or
            soup.select_one('[data-testid="plot-m"]') or
            soup.select_one('[data-testid="plot-xs"]') or
            soup.select_one('span[data-testid^="plot"]') or
            soup.select_one('p[data-testid="plot"]') or
            soup.select_one('.sc-e226b0e3-3') or
            soup.select_one('[class*="GenresAndPlot"] span[role="presentation"]') or
            soup.select_one('meta[name="description"]')
        )
        if plot_elem:
            if plot_elem.name == 'meta':
                movie['plot'] = plot_elem.get('content', '').strip()
            else:
                movie['plot'] = plot_elem.get_text(strip=True)
                
            if not movie.get('language'):
                detected = self.extract_language_from_text(movie['plot'])
                if detected:
                    movie['language'] = detected
        # Extract director
        directors = []
        dir_section = soup.select_one('[data-testid="title-pc-principal-credit"]')
        if dir_section:
            for a in dir_section.select('a.ipc-metadata-list-item__list-content-item'):
                directors.append(a.get_text(strip=True))
        if directors:
            movie['director'] = directors
        
        # Extract cast 
        cast = []
        for item in soup.select('[data-testid="title-cast-item"]')[:5]:
            name_elem = item.select_one('[data-testid="title-cast-item__actor"]')
            if not name_elem:
                continue
            name = name_elem.get_text(strip=True)

            # Scrape actor photo from the cast card <img>
            img_url = ""
            img_elem = item.select_one('img.ipc-image')
            if img_elem:
                raw_src = img_elem.get('src') or img_elem.get('data-src') or ""
                # re: resize IMDb thumbnail to a usable portrait size
                # IMDb image URLs contain a size token like _UX32_CR0,0,32,44_
                # We replace it with UX140 to get a proper headshot
                clean_src = re.sub(
                    r'_V1_.*?\.(jpg|jpeg|png|webp)',
                    r'_V1_UX140_CR0,0,140,193_.\1',
                    raw_src,
                    flags=re.IGNORECASE
                )   # here also regular lang
                img_url = clean_src if clean_src else raw_src

            cast.append({"name": name, "img": img_url})

        if cast:
            movie['cast'] = cast
        
        # Extract runtime
        runtime_elem = soup.select_one(
            '[data-testid="title-techspec_runtime"] .ipc-metadata-list-item__list-content-item'
        )
        if runtime_elem:
            raw_rt = runtime_elem.get_text(strip=True)
            movie['runtime'] = raw_rt
            mins = self.extract_runtime_minutes(raw_rt)
            if mins:
                movie['runtime_minutes'] = mins
        
        # Extract release date
        rel_elem = soup.select_one(
            '[data-testid="title-details-releasedate"] .ipc-metadata-list-item__list-content-item'
        )
        if rel_elem:
            raw_date = rel_elem.get_text(strip=True)
            movie['release_date'] = raw_date
            date_m = re.search(
                r'(\d{1,2}\s+\w+\s+\d{4}|\w+\s+\d{1,2},?\s+\d{4})',
                raw_date
            ) #re: extract clean date dd mm yy
            if date_m:
                movie['release_date_clean'] = date_m.group(1)
            if not movie.get('year'):
                y = self.extract_year(raw_date)
                if y:
                    movie['year'] = y
        
        # Extract budget
        budget_elem = soup.select_one(
            '[data-testid="title-boxoffice-budget"] .ipc-metadata-list-item__list-content-item'
        )
        if budget_elem:
            raw_budget = budget_elem.get_text(strip=True)
            movie['budget'] = raw_budget
            amt = self.extract_money_usd(raw_budget)
            if amt:
                movie['budget_usd'] = amt
        
        # Extract worldwide box office
        bo_elem = soup.select_one(
            '[data-testid="title-boxoffice-cumulativeworldwidegross"] '
            '.ipc-metadata-list-item__list-content-item'
        )
        if bo_elem:
            raw_bo = bo_elem.get_text(strip=True)
            movie['box_office'] = raw_bo
            amt = self.extract_money_usd(raw_bo)
            if amt:
                movie['box_office_usd'] = amt
        
        # Extract rating certificate 
        cert_elem = soup.select_one(
            '[data-testid="title-details-certificate"] .ipc-metadata-list-item__list-content-item'
        )
        if cert_elem:
            movie['certificate'] = self.normalize_certificate(cert_elem.get_text(strip=True))
        
        # Extract Metascore
        meta_elem = soup.select_one('[data-testid="meta-score-box"]')
        if meta_elem:
            sm = re.search(r'(\d+)', meta_elem.get_text(strip=True)) #<-- here also regular lang
            if sm:
                movie['metascore'] = int(sm.group(1))
        
        # Extract awards
        awards_elem = soup.select_one('[data-testid="award_information"]')
        if awards_elem:
            awards_text = awards_elem.get_text(strip=True)
            movie['awards'] = awards_text
            movie['oscar_wins'] = self.extract_oscar_count(awards_text)
            wins_m = re.search(r'(\d+)\s+win', awards_text, re.IGNORECASE) #<-- regular lang
            noms_m = re.search(r'(\d+)\s+nomination', awards_text, re.IGNORECASE) #<-- regular lang
            if wins_m:
                movie['total_wins'] = int(wins_m.group(1))
            if noms_m:
                movie['total_nominations'] = int(noms_m.group(1))

        movie['details_fetched'] = True
        time.sleep(0.3)   # <--delay
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