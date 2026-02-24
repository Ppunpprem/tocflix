import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from imdb_movie_crawler import IMDbMovieCrawler
import threading
from concurrent.futures import ThreadPoolExecutor

app = Flask(__name__)
# Enable CORS for the frontend URL and local dev
CORS(app)

_cache_lock = threading.Lock()
_crawler_cache = None
_is_loading = False
_details_loaded = False

def _fetch_all_details(crawler):
    """Fetch full details (genres, cast, director, etc.) for every movie.
    Runs in the background after the basic list is ready.
    Uses 3 workers to balance speed vs Render free-tier memory limits.
    """
    global _details_loaded
    print(f"🔄 Loading details for all {len(crawler.movies)} movies (genres, cast, etc.)...")
    try:
        with ThreadPoolExecutor(max_workers=3) as executor:
            executor.map(crawler.fetch_movie_details, crawler.movies)
        _details_loaded = True
        print("✅ All movie details loaded! Genre filtering is now fully accurate.")
    except Exception as e:
        print(f"⚠️ Error loading all details: {e}")

def get_crawler(force_load=True):
    """Returns the crawler. If not loaded, starts a background thread to load it."""
    global _crawler_cache, _is_loading

    if _crawler_cache is not None:
        return _crawler_cache

    if not force_load:
        return None

    with _cache_lock:
        if _crawler_cache is None and not _is_loading:
            _is_loading = True
            def load_task():
                global _crawler_cache, _is_loading
                try:
                    print("🚀 Starting lazy load of IMDb data...")
                    c = IMDbMovieCrawler()
                    c.fetch_top_movies()
                    # Make basic data available IMMEDIATELY so the site loads fast
                    _crawler_cache = c
                    print(f"✅ Basic list ready: {len(c.movies)} movies. Now loading full details...")
                    # Fetch all detail pages in the background (genres, cast, etc.)
                    threading.Thread(target=_fetch_all_details, args=(c,), daemon=True).start()
                except Exception as e:
                    print(f"❌ Error during lazy load: {e}")
                finally:
                    _is_loading = False

            threading.Thread(target=load_task, daemon=True).start()

    return _crawler_cache

@app.route("/")
def home():
    if not _crawler_cache:
        status = "Loading..." if _is_loading else "Idle"
    elif not _details_loaded:
        status = f"Basic list ready ({len(_crawler_cache.movies)} movies) — loading genres & details..."
    else:
        status = f"Fully ready ({len(_crawler_cache.movies)} movies with genres)"
    return jsonify({
        "message": "Backend is running successfully!",
        "database_status": status,
        "details_loaded": _details_loaded
    })

@app.route("/movies")
def get_movies():
    crawler = get_crawler()
    if not crawler:
        return jsonify({"message": "Server is warming up, please refresh in a few seconds...", "loading": True}), 503

    search       = (request.args.get("search")      or "").strip().lower()
    genre_filter = (request.args.get("genre")       or "").strip()
    year_exact   = (request.args.get("year")        or "").strip()
    year_from    = request.args.get("year_from",  type=int)
    year_to      = request.args.get("year_to",    type=int)
    min_rating   = request.args.get("min_rating", type=float)
    sort_mode    = (request.args.get("sort")        or "").strip()

    results = []
    for m in crawler.movies:
        if search:
            title    = (m.get("title")   or "").lower()
            genres   = " ".join(m.get("genres", [])).lower()
            language = (m.get("country") or "").lower()
            if search not in title and search not in genres and search not in language:
                continue

        if genre_filter:
            movie_genres = [g.lower() for g in m.get("genres", [])]
            if genre_filter.lower() not in movie_genres:
                continue

        if year_exact and str(m.get("year", "")) != year_exact:
            continue
        if year_from is not None and (m.get("year") or 0) < year_from:
            continue
        if year_to is not None and (m.get("year") or 9999) > year_to:
            continue

        if min_rating is not None and (m.get("rating") or 0) < min_rating:
            continue

        results.append(m)

    if sort_mode == "imdb_top10":
        results = sorted(results, key=lambda x: x.get("rating") or 0, reverse=True)[:10]

    return jsonify([format_movie_brief(m) for m in results])

@app.route("/movies/<movie_id>")
def get_movie(movie_id):
    crawler = get_crawler()
    if not crawler:
        return jsonify({"error": "Server is still warming up"}), 503

    movie = crawler.movies_dict.get(movie_id)
    if not movie:
        movie = next((m for m in crawler.movies if m.get("id") == movie_id), None)

    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    if not movie.get("details_fetched"):
        movie = crawler.fetch_movie_details(movie)

    return jsonify(format_movie_detail(movie))

@app.route("/movies/trending")
def get_trending():
    crawler = get_crawler()
    if not crawler:
        return jsonify([]), 200 # Return empty list so frontend doesn't crash while loading
    
    top = sorted(crawler.movies, key=lambda x: x.get("rating") or 0, reverse=True)[:10]
    return jsonify([format_movie_brief(m) for m in top])

@app.route("/movies/new-arrivals")
def get_new_arrivals():
    crawler = get_crawler()
    if not crawler:
        return jsonify([]), 200
        
    recent = sorted(crawler.movies, key=lambda x: x.get("year") or 0, reverse=True)[:10]
    return jsonify([format_movie_brief(m) for m in recent])

def format_movie_brief(m: dict) -> dict:
    return {
        "id":       m.get("id"),
        "title":    m.get("title"),
        "year":     m.get("year"),
        "rating":   m.get("rating"),
        "poster":   m.get("poster"),
        "genres":   m.get("genres", []),
        "language": m.get("country", ""),
    }

def format_movie_detail(movie: dict) -> dict:
    directors = movie.get("director", [])
    directors_str = ", ".join(directors) if isinstance(directors, list) else str(directors)
    return {
        "id":          movie.get("id"),
        "title":       movie.get("title"),
        "year":        movie.get("year"),
        "runtime":     movie.get("runtime"),
        "rating":      movie.get("rating"),
        "certificate": movie.get("certificate", "N/A"),
        "director":    directors_str,
        "genres":      movie.get("genres", []),
        "budget":      movie.get("budget"),
        "boxOffice":   movie.get("box_office"),
        "releaseDate": movie.get("release_date"),
        "imdbScore":   f"{movie.get('rating', 'N/A')} / 10",
        "awardsInfo":  movie.get("awards"),
        "backdrop":    movie.get("poster"),
        "plot":        movie.get("plot"),
        "cast": [
            {"name": actor, "img": f"https://ui-avatars.com/api/?name={actor.replace(' ', '+')}&background=333&color=fff&size=150"}
            for actor in movie.get("cast", [])
        ],
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)