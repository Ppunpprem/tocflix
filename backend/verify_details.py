from imdb_movie_crawler import IMDbMovieCrawler
import json

def verify():
    import os
    if os.path.exists("movies_cache.json"):
        os.remove("movies_cache.json")
    crawler = IMDbMovieCrawler()
    print("Step 1: Fetching Chart page to establish session...")
    crawler.fetch_top_movies()
    
    # Let's test with The Godfather (tt0068646)
    movie_id = "tt0068646"
    movie = {
        "id": movie_id,
        "url": f"https://www.imdb.com/title/{movie_id}/",
        "title": "The Godfather"
    }
    
    print(f"Fetching details for {movie['title']}...")
    updated_movie = crawler.fetch_movie_details(movie)
    
    fields_to_check = [
        "budget", "box_office", "release_date", "awards", 
        "backdrop", "rating", "director", "genres", "cast"
    ]
    
    print("\n--- Extracted Details ---")
    for field in fields_to_check:
        val = updated_movie.get(field)
        print(f"{field}: {val}")
    
    # Check backdrop specifically
    backdrop = updated_movie.get("backdrop")
    if backdrop and isinstance(backdrop, str) and ("slate" in backdrop.lower() or "amazon" in backdrop.lower()):
        print("\n✅ Backdrop looks like a high-res URL")
    else:
        print("\n❌ Backdrop is missing or fallback")

    # Check awards
    awards = updated_movie.get("awards")
    if awards and isinstance(awards, str) and ("win" in awards.lower() or "nomination" in awards.lower()):
        print("✅ Awards info is detailed")
    else:
        print("❌ Awards info is basic or missing")

if __name__ == "__main__":
    verify()
