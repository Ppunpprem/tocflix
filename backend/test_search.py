#!/usr/bin/env python3
"""
Test the new search by name feature
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imdb_movie_crawler import IMDbMovieCrawler

def test_search():
    """Test search by name functionality"""
    print("\n" + "="*90)
    print(" " * 27 + "SEARCH BY NAME - DEMO")
    print("="*90 + "\n")
    
    crawler = IMDbMovieCrawler()
    
    # Fetch top movies
    print("📥 Fetching IMDb Top 250 movies...")
    if not crawler.fetch_top_movies():
        print("❌ Failed to fetch movies")
        return
    
    print(f"✅ Successfully fetched {len(crawler.movies)} movies\n")
    
    # Test searches
    test_searches = [
        "Lord",          # Should find "Lord of the Rings" movies
        "dark",          # Should find "The Dark Knight", etc.
        "godfather",     # Should find "The Godfather"
        "star",          # Should find Star Wars movies
        "inception",     # Should find exact match
    ]
    
    for search_term in test_searches:
        print("="*90)
        print(f"Search: '{search_term}'")
        print("="*90)
        
        results = crawler.search_by_name(search_term)
        
        if results:
            print(f"\n✅ Found {len(results)} movie(s):\n")
            sorted_results = crawler.sort_alphabetically(results)
            for idx, movie in enumerate(sorted_results, 1):
                print(f"   {idx}. {movie.get('title')} ({movie.get('year')}) - ⭐ {movie.get('rating')}/10")
        else:
            print(f"\n❌ No movies found")
        
        print()
    
    print("="*90)
    print("✅ Search functionality test completed!")
    print("="*90 + "\n")

if __name__ == "__main__":
    try:
        test_search()
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user.\n")
    except Exception as e:
        print(f"\n✗ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
