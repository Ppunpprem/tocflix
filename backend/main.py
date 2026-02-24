from flask import Flask, jsonify, request
from flask_cors import CORS
from imdb_movie_crawler import IMDbMovieCrawler
import threading

# we need to set up the crawler and fetch movies before we can serve them through the API
app = Flask(__name__)
CORS(app)

#only crawl imdb once per server run
_cache_lock   = threading.Lock()
_crawler_cache: IMDbMovieCrawler | None = None

def get_crawler() -> IMDbMovieCrawler:
    """Return a fully-initialised crawler, fetching from IMDb only on first call."""
    global _crawler_cache
    with _cache_lock:
        if _crawler_cache is None:
            print("Cold-start: fetching IMDb Top 250 …")
            c = IMDbMovieCrawler()
            c.fetch_top_movies()                                   # list of 250
            c.fetch_movies_details_parallel(c.movies, max_workers=10)  # all details
            _crawler_cache = c
            print(f"Cache ready — {len(c.movies)} movies loaded")
        return _crawler_cache


def format_movie_brief(m: dict) -> dict:
    """Return the fields needed for the movie-grid cards."""
    return {
        "id":       m.get("id"),
        "title":    m.get("title"),
        "year":     m.get("year"),
        "rating":   m.get("rating"),
        "poster":   m.get("poster"),
        "genres":   m.get("genres", []),
        # "language" in the frontend actually means country of origin
        "language": m.get("country", ""),
    }


def format_movie_detail(movie: dict) -> dict:
    """Return the full fields needed for DetailPage."""
    directors = movie.get("director", [])
    if isinstance(directors, list):
        directors_str = ", ".join(directors)
    else:
        directors_str = str(directors)

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
            # cast images are not scraped from IMDb – keep blank so frontend
            # falls back to initials avatar gracefully
            {"name": actor, "img": f"https://ui-avatars.com/api/?name={actor.replace(' ', '+')}&background=333&color=fff&size=150"}
            for actor in movie.get("cast", [])
        ],
    }


# to fix 404 error while go to the root route
@app.route("/")
def home():
    return jsonify({"message": "Backend is running successfully!"})

# all movies route
@app.route("/movies")
def get_movies():
    crawler = get_crawler()

    search      = (request.args.get("search")      or "").strip().lower()
    genre_filter= (request.args.get("genre")       or "").strip()
    year_exact  = (request.args.get("year")        or "").strip()
    year_from   = request.args.get("year_from",  type=int)
    year_to     = request.args.get("year_to",    type=int)
    min_rating  = request.args.get("min_rating", type=float)
    sort_mode   = (request.args.get("sort")        or "").strip()   # "imdb_top10"

    results = []
    for m in crawler.movies:
        # search (title, genres, country) 
        if search:
            title    = (m.get("title")   or "").lower()
            genres   = " ".join(m.get("genres", [])).lower()
            language = (m.get("country") or "").lower()
            if search not in title and search not in genres and search not in language:
                continue

        # genre filter
        if genre_filter:
            movie_genres = [g.lower() for g in m.get("genres", [])]
            if genre_filter.lower() not in movie_genres:
                continue

        # year filters
        if year_exact and str(m.get("year", "")) != year_exact:
            continue
        if year_from is not None and (m.get("year") or 0) < year_from:
            continue
        if year_to is not None and (m.get("year") or 9999) > year_to:
            continue

        # rating filter
        if min_rating is not None and (m.get("rating") or 0) < min_rating:
            continue

        results.append(m)

    # Top-10 by rating mode (genre cards on home page)
    if sort_mode == "imdb_top10":
        results = sorted(results, key=lambda x: x.get("rating") or 0, reverse=True)[:10]

    return jsonify([format_movie_brief(m) for m in results])

# this is for specific movie route
@app.route("/movies/<movie_id>")
def get_movie(movie_id):
    crawler = get_crawler()

    # movies_dict is built during fetch_top_movies / _extract_from_json
    movie = crawler.movies_dict.get(movie_id)

    # fallback linear scan (handles edge-cases where dict wasn't populated)
    if not movie:
        movie = next((m for m in crawler.movies if m.get("id") == movie_id), None)

    if not movie:
        return jsonify({"error": "Movie not found"}), 404

    # details already fetched during warm-up; fetch on-demand only if missing
    if not movie.get("details_fetched"):
        movie = crawler.fetch_movie_details(movie)

    return jsonify(format_movie_detail(movie))

#trending movie
@app.route("/movies/trending")
def get_trending():
    crawler = get_crawler()
    top = sorted(crawler.movies, key=lambda x: x.get("rating") or 0, reverse=True)[:10]
    return jsonify([format_movie_brief(m) for m in top])

#new arrival
@app.route("/movies/new-arrivals")
def get_new_arrivals():
    crawler = get_crawler()
    recent = sorted(crawler.movies, key=lambda x: x.get("year") or 0, reverse=True)[:10]
    return jsonify([format_movie_brief(m) for m in recent])

if __name__ == "__main__":
    get_crawler()
    app.run(debug=False, port=5000)

# this part is just for testing before we set up the flask to test backend fetching correctly or not.
# url = "https://www.imdb.com/chart/top/"
# HEADERS = {
#     'User-Agent': 'Mozilla/5.0 (iPad; CPU OS 12_2 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148'
# }
# page = requests.get(url, headers=HEADERS)

# print(page.status_code)  # Should be 200 if successful

# soup = BeautifulSoup(page.text, "html.parser")
# # print(soup.prettify())
# print(soup.title)