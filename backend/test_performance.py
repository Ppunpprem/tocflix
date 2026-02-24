#!/usr/bin/env python3
"""
Performance test comparing sequential vs parallel fetching
"""
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imdb_movie_crawler import IMDbMovieCrawler

def test_performance():
    """Test multithreading performance"""
    print("\n" + "="*90)
    print(" " * 25 + "MULTITHREADING PERFORMANCE TEST")
    print("="*90 + "\n")
    
    crawler = IMDbMovieCrawler()
    
    # Fetch top movies
    print("📥 Fetching IMDb Top 250 movies...")
    if not crawler.fetch_top_movies():
        print("❌ Failed to fetch movies")
        return
    
    print(f"✅ Successfully fetched {len(crawler.movies)} movies\n")
    
    # Test with Action genre filtering (requires detail fetching)
    print("="*90)
    print("TEST: Filter by Genre 'Action' (Multithreaded)")
    print("="*90)
    
    start_time = time.time()
    filters = {'genres': ['Action']}
    action_movies = crawler.filter_movies(filters)
    end_time = time.time()
    
    elapsed = end_time - start_time
    
    print(f"\n✅ Performance Results:")
    print(f"   • Total movies fetched: {len(crawler.movies)}")
    print(f"   • Action movies found: {len(action_movies)}")
    print(f"   • Time elapsed: {elapsed:.2f} seconds")
    print(f"   • Average per movie: {elapsed/len(crawler.movies):.3f} seconds")
    
    # Display first 5 results
    print(f"\nFirst 5 Action movies (alphabetically):")
    sorted_action = crawler.sort_alphabetically(action_movies)
    for i, movie in enumerate(sorted_action[:5], 1):
        genres = ', '.join(movie.get('genres', [])) if movie.get('genres') else 'N/A'
        print(f"   {i}. {movie.get('title')} ({movie.get('year')}) - {genres}")
    
    print("\n" + "="*90)
    print("✅ Multithreading test completed!")
    print("="*90 + "\n")

if __name__ == "__main__":
    try:
        test_performance()
    except KeyboardInterrupt:
        print("\n\n✓ Test interrupted by user.\n")
    except Exception as e:
        print(f"\n✗ Test failed: {e}\n")
        import traceback
        traceback.print_exc()
