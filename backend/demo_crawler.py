#!/usr/bin/env python3
"""
Quick demo of IMDb Movie Crawler functionality
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imdb_movie_crawler import IMDbMovieCrawler

def demo():
    """Quick demonstration of key features"""
    print("\n" + "="*90)
    print(" " * 27 + "IMDb MOVIE CRAWLER DEMO")
    print("="*90 + "\n")
    
    crawler = IMDbMovieCrawler()
    
    # Fetch top movies
    print("📥 Fetching IMDb Top 250 movies...")
    if not crawler.fetch_top_movies():
        print("❌ Failed to fetch movies")
        return
    
    print(f"✅ Successfully fetched {len(crawler.movies)} movies\n")
    
    # Demo 1: Filter by year and rating
    print("="*90)
    print("DEMO 1: Filter by year (2010-2020) and rating (8.5+)")
    print("="*90)
    filters = {
        'year_start': 2010,
        'year_end': 2020,
        'min_rating': 8.5
    }
    filtered = crawler.filter_movies(filters)
    crawler.display_movies_list(filtered[:5])  # Show first 5
    
    # Demo 2: Filter by genre (Action)
    print("\n" + "="*90)
    print("DEMO 2: Filter by genre - Action movies")
    print("="*90)
    print("(This will fetch detail information for genre filtering...)")
    filters = {'genres': ['Action']}
    action_movies = crawler.filter_movies(filters)
    crawler.display_movies_list(action_movies[:3])  # Show first 3
    
    # Demo 3: View movie details
    print("\n" + "="*90)
    print("DEMO 3: View detailed information for movie #1")
    print("="*90)
    if crawler.movies:
        crawler.display_movie_details(crawler.movies[0])
    
    print("\n" + "="*90)
    print("✅ Demo completed successfully!")
    print("\nTo use the full interactive version, run:")
    print("  python imdb_movie_crawler.py")
    print("="*90 + "\n")

if __name__ == "__main__":
    try:
        demo()
    except KeyboardInterrupt:
        print("\n\n✓ Demo interrupted by user.\n")
    except Exception as e:
        print(f"\n✗ Demo failed: {e}\n")
        import traceback
        traceback.print_exc()
