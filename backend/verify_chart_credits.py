from imdb_movie_crawler import IMDbMovieCrawler
import os

def verify_chart():
    # Remove cache to force fresh crawl of chart page
    if os.path.exists("movies_cache.json"):
        os.remove("movies_cache.json")
        
    crawler = IMDbMovieCrawler()
    print("Fetching Top Movies list...")
    success = crawler.fetch_top_movies()
    
    if not success:
        print("❌ Failed to fetch top movies")
        return

    print(f"Total movies: {len(crawler.movies)}")
    
    # Check first few movies for credits
    for i in range(5):
        m = crawler.movies[i]
        print(f"\nMovie: {m.get('title')}")
        print(f"Director: {m.get('director')}")
        print(f"Cast (Stars): {[c.get('name') for c in m.get('cast', [])]}")
        
    # Check if any have directors
    has_directors = any(m.get('director') for m in crawler.movies)
    if has_directors:
        print("\n✅ Successfully extracted directors from Chart page!")
    else:
        print("\n❌ Failed to extract directors from Chart page.")

if __name__ == "__main__":
    verify_chart()
