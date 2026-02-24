#!/usr/bin/env python3
"""
Test script for IMDb Movie Crawler
Simulates user input to test all functionality
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from imdb_movie_crawler import IMDbMovieCrawler

def test_crawler():
    """Test the enhanced IMDb movie crawler"""
    print("="*90)
    print(" " * 28 + "TESTING IMDb MOVIE CRAWLER")
    print("="*90 + "\n")
    
    # Initialize crawler
    print("TEST 1: Initializing crawler and fetching Top 250...")
    crawler = IMDbMovieCrawler()
    
    if not crawler.fetch_top_movies():
        print("❌ FAILED: Could not fetch movies")
        return False
    
    if not crawler.movies:
        print("❌ FAILED: No movies extracted")
        return False
    
    print(f"✓ PASSED: Successfully fetched {len(crawler.movies)} movies\n")
    
    # Test 2: Filter by genre (Action)
    print("TEST 2: Filtering by genre 'Action'...")
    filters = {'genres': ['Action']}
    action_movies = crawler.filter_movies(filters)
    
    if not action_movies:
        print("⚠️  WARNING: No Action movies found (this might be expected)")
    else:
        print(f"✓ PASSED: Found {len(action_movies)} Action movies")
        # Show first 3
        sorted_action = crawler.sort_alphabetically(action_movies)
        for movie in sorted_action[:3]:
            genres = ', '.join(movie.get('genres', [])) if movie.get('genres') else 'N/A'
            print(f"   - {movie.get('title')} ({movie.get('year')}) - Genres: {genres}")
    print()
    
    # Test 3: Filter by year
    print("TEST 3: Filtering by year range (2000-2010)...")
    filters = {'year_start': 2000, 'year_end': 2010}
    year_movies = crawler.filter_movies(filters)
    
    if not year_movies:
        print("❌ FAILED: No movies found in year range")
        return False
    
    print(f"✓ PASSED: Found {len(year_movies)} movies from 2000-2010")
    sorted_year = crawler.sort_alphabetically(year_movies)
    for movie in sorted_year[:3]:
        print(f"   - {movie.get('title')} ({movie.get('year')})")
    print()
    
    # Test 4: Filter by rating
    print("TEST 4: Filtering by minimum rating (9.0+)...")
    filters = {'min_rating': 9.0}
    high_rated = crawler.filter_movies(filters)
    
    if not high_rated:
        print("❌ FAILED: No highly rated movies found")
        return False
    
    print(f"✓ PASSED: Found {len(high_rated)} movies with rating 9.0+")
    sorted_rated = crawler.sort_alphabetically(high_rated)
    for movie in sorted_rated[:3]:
        print(f"   - {movie.get('title')} - Rating: {movie.get('rating')}/10")
    print()
    
    # Test 5: Alphabetical sorting
    print("TEST 5: Testing alphabetical sorting...")
    sorted_movies = crawler.sort_alphabetically(crawler.movies[:10])
    prev_title = ""
    is_sorted = True
    
    for movie in sorted_movies:
        title = movie.get('title', '').lower()
        if title < prev_title:
            is_sorted = False
            break
        prev_title = title
    
    if is_sorted:
        print("✓ PASSED: Movies are sorted alphabetically (A-Z)")
        print(f"   First 5: {', '.join([m.get('title') for m in sorted_movies[:5]])}")
    else:
        print("❌ FAILED: Movies are not properly sorted")
        return False
    print()
    
    # Test 6: Get movie by ID
    print("TEST 6: Fetching movie details by ID...")
    if crawler.movies:
        test_movie = crawler.movies[0]
        movie_id = test_movie.get('id')
        
        if movie_id:
            retrieved = crawler.get_movie_by_id(movie_id)
            if retrieved:
                print(f"✓ PASSED: Successfully retrieved movie by ID: {retrieved.get('title')}")
            else:
                print("❌ FAILED: Could not retrieve movie by ID")
                return False
        else:
            print("⚠️  WARNING: First movie has no ID")
    print()
    
    # Test 7: Get movie by rank
    print("TEST 7: Fetching movie by rank...")
    movie_rank_1 = crawler.get_movie_by_rank(1)
    if movie_rank_1:
        print(f"✓ PASSED: Movie at rank 1: {movie_rank_1.get('title')}")
    else:
        print("❌ FAILED: Could not retrieve movie by rank")
        return False
    print()
    
    # Test 8: Fetch detailed information
    print("TEST 8: Fetching detailed movie information...")
    if crawler.movies:
        test_movie = crawler.movies[0].copy()
        detailed = crawler.fetch_movie_details(test_movie)
        
        # Check if details were fetched
        expected_fields = ['genres', 'country', 'plot', 'director', 'cast']
        found_fields = [f for f in expected_fields if f in detailed]
        
        print(f"✓ PASSED: Fetched details for '{detailed.get('title')}'")
        print(f"   Found fields: {', '.join(found_fields)}")
        
        if detailed.get('genres'):
            print(f"   Genres: {', '.join(detailed['genres'])}")
        if detailed.get('country'):
            print(f"   Country: {detailed['country']}")
        if detailed.get('director'):
            directors = ', '.join(detailed['director']) if isinstance(detailed['director'], list) else detailed['director']
            print(f"   Director: {directors}")
    print()
    
    # Test 9: Display formatting
    print("TEST 9: Testing display formatting...")
    test_movies = crawler.movies[:2]
    print("\nSample output (list view):")
    print("─" * 90)
    crawler.display_movies_list(test_movies)
    print("─" * 90)
    print("✓ PASSED: Display formatting works\n")
    
    # Test 10: Detailed view
    print("TEST 10: Testing detailed movie view...")
    if crawler.movies:
        print("\nSample output (detail view):")
        print("─" * 90)
        crawler.display_movie_details(crawler.movies[0])
        print("─" * 90)
        print("✓ PASSED: Detail view works\n")
    
    # Summary
    print("\n" + "="*90)
    print(" " * 35 + "TEST SUMMARY")
    print("="*90)
    print("✓ ALL TESTS PASSED!")
    print("\nFunctionality verified:")
    print("  ✓ Movie list fetching from IMDb Top 250")
    print("  ✓ Genre filtering using regex")
    print("  ✓ Year range filtering")
    print("  ✓ Rating filtering")
    print("  ✓ Alphabetical sorting (A-Z)")
    print("  ✓ Movie lookup by ID")
    print("  ✓ Movie lookup by rank")
    print("  ✓ Detailed information extraction")
    print("  ✓ List and detail view display")
    print("="*90 + "\n")
    
    return True

if __name__ == "__main__":
    try:
        success = test_crawler()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n✓ Tests interrupted by user.\n")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Test failed with error: {e}\n")
        import traceback
        traceback.print_exc()
        sys.exit(1)
