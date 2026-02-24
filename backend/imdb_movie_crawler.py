import re
import requests
from bs4 import BeautifulSoup
import json
import time
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed

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
        
    def fetch_page(self, url: str) -> Optional[str]:
        """Fetch a web page with error handling"""
        try:
            response = requests.get(url, headers=self.headers, timeout=15)
            response.raise_for_status()
            return response.text
        except requests.RequestException as e:
            print(f"✗ Error fetching {url}: {e}")
            return None
    
    def extract_movie_id(self, url: str) -> Optional[str]:
        """Extract IMDb movie ID from URL"""
        match = re.search(r'/title/(tt\d+)', url)
        return match.group(1) if match else None
    
    def fetch_top_movies(self):
        """Fetch IMDb Top 250 movies list"""
        print("Fetching IMDb Top 250 movies...")
        html = self.fetch_page(self.url)
        if not html:
            return False
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Try JSON-LD extraction first
        script_tags = soup.find_all('script', type='application/ld+json')
        for script in script_tags:
            try:
                data = json.loads(script.string)
                if isinstance(data, dict) and 'itemListElement' in data:
                    self._extract_from_json(data)
                    return True
            except:
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
                movie_data = {}
                movie_item = item.get('item', {})
                
                movie_data['rank'] = item.get('position', 0)
                movie_data['title'] = movie_item.get('name', 'N/A')
                
                url = movie_item.get('url', '')
                if url:
                    movie_data['url'] = f"https://www.imdb.com{url}" if url.startswith('/') else url
                    movie_data['id'] = self.extract_movie_id(movie_data['url'])
                
                image = movie_item.get('image', '')
                if image:
                    movie_data['poster'] = image
                
                rating_data = movie_item.get('aggregateRating', {})
                if rating_data:
                    rating_value = rating_data.get('ratingValue')
                    if rating_value:
                        movie_data['rating'] = float(rating_value)
                
                description = movie_item.get('description', '')
                if description:
                    year_match = re.search(r'\b(19|20)\d{2}\b', description)
                    if year_match:
                        movie_data['year'] = int(year_match.group(0))
                
                self.movies.append(movie_data)
                if movie_data.get('id'):
                    self.movies_dict[movie_data['id']] = movie_data
                
            except Exception as e:
                print(f"Error parsing movie: {e}")
                continue
        
        print(f"✓ Extracted {len(self.movies)} movies\n")
    
    def _extract_from_html(self, soup: BeautifulSoup):
        """Fallback HTML extraction method"""
        movie_items = soup.find_all('li', class_=re.compile(r'ipc-metadata-list-summary-item'))
        
        print(f"Found {len(movie_items)} movie items. Extracting...\n")
        
        for idx, item in enumerate(movie_items, 1):
            try:
                movie_data = {'rank': idx}
                
                title_elem = item.find('h3', class_=re.compile(r'ipc-title'))
                if title_elem:
                    title_text = title_elem.get_text(strip=True)
                    title_match = re.search(r'^\d+\.\s*(.+)', title_text)
                    movie_data['title'] = title_match.group(1) if title_match else title_text
                
                link = item.find('a', href=re.compile(r'/title/tt\d+/'))
                if link and link.get('href'):
                    movie_data['url'] = f"https://www.imdb.com{link['href']}"
                    movie_data['id'] = self.extract_movie_id(movie_data['url'])
                
                img = item.find('img', class_='ipc-image')
                if img and img.get('src'):
                    movie_data['poster'] = img['src']
                
                metadata_items = item.find_all('span', class_=re.compile(r'cli-title-metadata-item'))
                for meta in metadata_items:
                    text = meta.get_text(strip=True)
                    if re.match(r'^\d{4}$', text):
                        movie_data['year'] = int(text)
                
                rating_elem = item.find('span', class_=re.compile(r'ipc-rating-star'))
                if rating_elem:
                    rating_text = rating_elem.get_text(strip=True)
                    rating_match = re.search(r'(\d+\.?\d*)', rating_text)
                    if rating_match:
                        movie_data['rating'] = float(rating_match.group(1))
                
                if 'title' in movie_data:
                    self.movies.append(movie_data)
                    if movie_data.get('id'):
                        self.movies_dict[movie_data['id']] = movie_data
                    
            except Exception as e:
                print(f"Error parsing movie {idx}: {e}")
                continue
        
        print(f"✓ Extracted {len(self.movies)} movies\n")
    
    def fetch_movie_details(self, movie: dict) -> dict:
        """Fetch detailed information for a specific movie"""
        if not movie.get('url'):
            return movie
        
        # Check if details already fetched
        if movie.get('details_fetched'):
            return movie
        
        print(f"  Fetching details for: {movie.get('title', 'Unknown')}")
        
        html = self.fetch_page(movie['url'])
        if not html:
            return movie
        
        soup = BeautifulSoup(html, 'html.parser')
        
        # Extract year if not already present
        if not movie.get('year'):
            # Try to extract from title element or release info
            title_elem = soup.select_one('h1[data-testid="hero-title-block__title"]')
            if title_elem:
                # Look for year in nearby elements
                year_elem = soup.select_one('[data-testid="hero-title-block__metadata"] a')
                if year_elem:
                    year_text = year_elem.get_text(strip=True)
                    year_match = re.search(r'\b(19|20)\d{2}\b', year_text)
                    if year_match:
                        movie['year'] = int(year_match.group(0))
        
        # Extract genres
        genres = []
        genre_chips = soup.select('a.ipc-chip span.ipc-chip__text')
        for chip in genre_chips[:10]:  # Limit to first 10 to avoid picking up other chips
            genre_text = chip.get_text(strip=True)
            if genre_text and len(genre_text) < 20:  # Genres are typically short
                genres.append(genre_text)
        if genres:
            movie['genres'] = genres
        
        # Extract country
        country_elem = soup.select_one('[data-testid="title-details-origin"] a')
        if country_elem:
            movie['country'] = country_elem.get_text(strip=True)
        
        # Extract plot
        plot_elem = soup.select_one('[data-testid="plot-xl"]') or soup.select_one('[data-testid="plot-l"]')
        if plot_elem:
            movie['plot'] = plot_elem.get_text(strip=True)
        
        # Extract director
        directors = []
        director_section = soup.select_one('[data-testid="title-pc-principal-credit"]')
        if director_section:
            director_links = director_section.select('a.ipc-metadata-list-item__list-content-item')
            for director in director_links:
                directors.append(director.get_text(strip=True))
        if directors:
            movie['director'] = directors
        
        # Extract cast
        cast = []
        cast_items = soup.select('[data-testid="title-cast-item__actor"]')
        for actor in cast_items[:5]:  # Top 5 actors
            cast.append(actor.get_text(strip=True))
        if cast:
            movie['cast'] = cast
        
        # Extract runtime
        runtime_elem = soup.select_one('[data-testid="title-techspec_runtime"] .ipc-metadata-list-item__list-content-item')
        if runtime_elem:
            movie['runtime'] = runtime_elem.get_text(strip=True)
        
        # Extract release date
        release_elem = soup.select_one('[data-testid="title-details-releasedate"] .ipc-metadata-list-item__list-content-item')
        if release_elem:
            movie['release_date'] = release_elem.get_text(strip=True)
            # Extract year from release date if still not found
            if not movie.get('year'):
                year_match = re.search(r'\b(19|20)\d{2}\b', release_elem.get_text())
                if year_match:
                    movie['year'] = int(year_match.group(0))
        
        # Extract budget
        budget_elem = soup.select_one('[data-testid="title-boxoffice-budget"] .ipc-metadata-list-item__list-content-item')
        if budget_elem:
            movie['budget'] = budget_elem.get_text(strip=True)
        
        # Extract worldwide box office
        boxoffice_elem = soup.select_one('[data-testid="title-boxoffice-cumulativeworldwidegross"] .ipc-metadata-list-item__list-content-item')
        if boxoffice_elem:
            movie['box_office'] = boxoffice_elem.get_text(strip=True)
        
        # Extract rating certificate (PG, R, etc.)
        cert_elem = soup.select_one('[data-testid="title-details-certificate"] .ipc-metadata-list-item__list-content-item')
        if cert_elem:
            movie['certificate'] = cert_elem.get_text(strip=True)
        
        # Extract Metascore
        metascore_elem = soup.select_one('[data-testid="meta-score-box"]')
        if metascore_elem:
            score_text = metascore_elem.get_text(strip=True)
            score_match = re.search(r'(\d+)', score_text)
            if score_match:
                movie['metascore'] = int(score_match.group(1))
        
        # Extract awards
        awards_elem = soup.select_one('[data-testid="award_information"]')
        if awards_elem:
            awards_text = awards_elem.get_text(strip=True)
            movie['awards'] = awards_text
        
        movie['details_fetched'] = True
        time.sleep(0.5)  # Be polite to IMDb servers
        
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
                    print(f"  Progress: {completed}/{total} movies fetched ({int(completed/total*100)}%)")
        
        print(f"✓ Completed fetching details for {total} movies\n")
    
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
        if filters.get('year_start') or filters.get('year_end'):
            year_start = filters.get('year_start', 0)
            year_end = filters.get('year_end', 9999)
            filtered = [
                m for m in filtered 
                if 'year' in m and year_start <= m['year'] <= year_end
            ]
        
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
    
    def display_movies_list(self, movies: List[dict]):
        """Display filtered movies in list format"""
        if not movies:
            print("\n❌ No movies found matching your criteria.\n")
            return
        
        # Sort alphabetically
        sorted_movies = self.sort_alphabetically(movies)
        
        # Fetch missing country info in parallel if needed
        movies_needing_country = [m for m in sorted_movies if not m.get('country') and not m.get('details_fetched')]
        if movies_needing_country:
            self.fetch_movies_details_parallel(movies_needing_country, max_workers=10)
        
        print("\n" + "╔" + "═"*88 + "╗")
        print("║" + f"{'FILTERED MOVIES (A-Z)':^88}" + "║")
        print("╚" + "═"*88 + "╝\n")
        print(f"Found {len(sorted_movies)} movie(s)\n")
        
        for idx, movie in enumerate(sorted_movies, 1):
            # Ensure country is fetched
            if not movie.get('country') and not movie.get('details_fetched'):
                self.fetch_movie_details(movie)
            
            print(f"{idx}. {movie.get('title', 'N/A')}")
            print(f"   🆔 ID: {movie.get('id', 'N/A')}")
            print(f"   🌍 Country: {movie.get('country', 'N/A')}")
            print(f"   📅 Year: {movie.get('year', 'N/A')}")
            print(f"   ⭐ IMDb: {movie.get('rating', 'N/A')}/10")
            if movie.get('poster'):
                print(f"   🖼️  Poster: {movie['poster']}")
            if movie.get('genres'):
                print(f"   🎭 Genres: {', '.join(movie['genres'])}")
            print()
    
    def display_movie_details(self, movie: dict):
        """Display comprehensive movie details"""
        # Fetch details if not already fetched
        if not movie.get('details_fetched'):
            movie = self.fetch_movie_details(movie)
        
        title = movie.get('title', 'Unknown')
        year = movie.get('year', 'N/A')
        
        print("\n" + "╔" + "═"*88 + "╗")
        print("║" + f"{title.upper()} ({year})".center(88) + "║")
        print("╚" + "═"*88 + "╝\n")
        
        if movie.get('poster'):
            print(f"🖼️  POSTER: {movie['poster']}\n")
        
        if movie.get('plot'):
            print(f"🎬 PLOT SUMMARY:")
            print(f"   {movie['plot']}\n")
        
        if movie.get('cast'):
            print(f"👥 CAST:")
            for actor in movie['cast']:
                print(f"   • {actor}")
            print()
        
        if movie.get('director'):
            directors = ', '.join(movie['director']) if isinstance(movie['director'], list) else movie['director']
            print(f"🎥 DIRECTOR: {directors}\n")
        
        if movie.get('genres'):
            genres = ', '.join(movie['genres']) if isinstance(movie['genres'], list) else movie['genres']
            print(f"🎭 GENRES: {genres}\n")
        
        if movie.get('certificate'):
            print(f"⭐ RATING: {movie['certificate']}\n")
        
        if movie.get('budget'):
            print(f"💰 BUDGET: {movie['budget']}\n")
        
        if movie.get('box_office'):
            print(f"💵 WORLDWIDE BOX OFFICE: {movie['box_office']}\n")
        
        if movie.get('runtime'):
            print(f"⏱️  RUNTIME: {movie['runtime']}\n")
        
        if movie.get('release_date'):
            print(f"📅 RELEASE DATE: {movie['release_date']}\n")
        
        if movie.get('rating'):
            print(f"🌟 IMDb SCORE: {movie['rating']}/10\n")
        
        if movie.get('metascore'):
            print(f"🍅 METASCORE: {movie['metascore']}/100\n")
        
        if movie.get('awards'):
            print(f"🏆 AWARDS: {movie['awards']}\n")
        
        if movie.get('country'):
            print(f"🌍 COUNTRY: {movie['country']}\n")
        
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
        print("🎭 Filter by Genres:")
        print("   Available: Action, Comedy, Drama, Sci-Fi")
        genre_input = input("   Enter genres (comma-separated): ").strip()
        if genre_input:
            genres = [g.strip() for g in genre_input.split(',')]
            # Validate genres match the options
            valid_genres = []
            for genre in genres:
                if re.search(r'\b(Action|Comedy|Drama|Sci-Fi)\b', genre, re.IGNORECASE):
                    valid_genres.append(genre)
            if valid_genres:
                filters['genres'] = valid_genres
        
        # Year range
        year_start = input("\n📅 Year from (e.g., 1990): ").strip()
        if year_start and year_start.isdigit():
            filters['year_start'] = int(year_start)
        
        year_end = input("📅 Year to (e.g., 2024): ").strip()
        if year_end and year_end.isdigit():
            filters['year_end'] = int(year_end)
        
        # Rating range
        min_rating = input("\n⭐ Minimum IMDb rating (1-10): ").strip()
        if min_rating:
            try:
                filters['min_rating'] = float(min_rating)
            except ValueError:
                print("Invalid rating, skipping...")
        
        max_rating = input("⭐ Maximum IMDb rating (1-10): ").strip()
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
                        print(f"\n✓ Found {len(results)} movie(s) matching '{search_term}'")
                        self.display_movies_list(results)
                    else:
                        print(f"\n❌ No movies found matching '{search_term}'.\n")
                else:
                    print("\n❌ Please enter a search term.\n")
                
            elif choice == '3':
                movie_id = input("\nEnter IMDb ID (e.g., tt0111161): ").strip()
                movie = self.get_movie_by_id(movie_id)
                if movie:
                    self.display_movie_details(movie)
                else:
                    print(f"\n❌ Movie with ID '{movie_id}' not found in Top 250.\n")
                    
            elif choice == '4':
                print("\n✓ Thank you for using IMDb Movie Crawler!\n")
                break
                
            else:
                print("\n❌ Invalid option. Please select 1-4.\n")
    
    def run(self):
        """Main execution method"""
        print("\n" + "="*90)
        print(" " * 25 + "IMDb TOP 250 MOVIE CRAWLER")
        print("="*90 + "\n")
        
        # Fetch movie list
        if not self.fetch_top_movies():
            print("❌ Failed to fetch movies. Please check your internet connection.\n")
            return
        
        if not self.movies:
            print("❌ No movies extracted. Please try again later.\n")
            return
        
        print(f"✓ Successfully loaded {len(self.movies)} movies from IMDb Top 250\n")
        
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