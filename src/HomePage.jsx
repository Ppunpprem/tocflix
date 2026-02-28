import { useState, useEffect, useRef } from "react";
import { useNavigate } from "react-router-dom";
import Navbar from "./Navbar";

import { API_BASE_URL as API } from "./config";

// Genre config  colours only posters come from real movie data
const GENRE_CONFIG = [
  { label: "Action",    color: "bg-red-600"    },
  { label: "Drama",     color: "bg-purple-600" },
  { label: "Comedy",    color: "bg-green-500"  },
  { label: "Adventure", color: "bg-yellow-500" },
];

// IMDb Badge
function ImdbBadge({ score }) {
  return (
    <span className="inline-flex items-center gap-1 bg-[#f5c518] text-black text-[10px] font-black px-1.5 py-0.5 rounded leading-none">
      IMDb <span className="font-bold">{score}</span>
    </span>
  );
}

// Movie Card
function MovieCard({ movie, onMovieClick }) {
  const [imgError, setImgError] = useState(false);
  return (
    <div
      onClick={() => onMovieClick && onMovieClick(movie)}
      className="flex-shrink-0 w-[140px] sm:w-[160px] md:w-[175px] lg:w-[190px] cursor-pointer group"
    >
      <div className="relative overflow-hidden rounded-lg aspect-[2/3] bg-gray-900">
        {!imgError ? (
          <img
            src={movie.poster}
            alt={movie.title}
            onError={() => setImgError(true)}
            className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
          />
        ) : (
          <div className="flex items-center justify-center w-full h-full p-2 text-xs text-center text-gray-500 bg-gray-800">
            {movie.title}
          </div>
        )}
      </div>
      <div className="mt-2 space-y-0.5">
        <p className="text-[10px] text-gray-500 uppercase tracking-wide">
          {movie.language}, {movie.year}
        </p>
        <p className="text-sm font-semibold leading-snug text-white line-clamp-2">
          {movie.title}
        </p>
        <div className="flex items-center gap-2 pt-1">
          {movie.rating != null && (
            <ImdbBadge score={typeof movie.rating === "number" ? movie.rating.toFixed(1) : movie.rating} />
          )}
        </div>
      </div>
    </div>
  );
}

// Skeleton Card 
function SkeletonCard() {
  return (
    <div className="flex-shrink-0 w-[140px] sm:w-[160px] md:w-[175px] lg:w-[190px] animate-pulse">
      <div className="rounded-lg aspect-[2/3] bg-gray-800" />
      <div className="mt-2 space-y-1.5">
        <div className="w-2/3 h-2 bg-gray-800 rounded" />
        <div className="w-full h-3 bg-gray-700 rounded" />
        <div className="w-3/4 h-3 bg-gray-700 rounded" />
      </div>
    </div>
  );
}

//Scroll Row
function ScrollRow({ title, items, loading, onMovieClick, onSeeMore }) {
  const ref = useRef(null);
  const scroll = (dir) => {
    if (ref.current) ref.current.scrollBy({ left: dir * 400, behavior: "smooth" });
  };

  return (
    <section className="mb-10">
      <div className="flex items-center justify-between px-4 mb-4 sm:px-6 md:px-10">
        <h2 className="text-lg font-bold text-white sm:text-xl md:text-2xl">{title}</h2>
        <button
          onClick={onSeeMore}
          style={{ background: "none", border: "none", color: "#e50914" }}
          className="items-center hidden gap-1 text-xs font-bold transition-opacity cursor-pointer sm:flex sm:text-sm hover:opacity-75"
        >
          See more <span className="text-base">›</span>
        </button>
      </div>

      <div className="relative group/scroller">
        {/* Left arrow */}
        <button
          onClick={() => scroll(-1)}
          className="absolute top-0 left-0 z-10 items-center justify-center hidden w-12 text-xl text-white transition-all group-hover:flex bottom-8 bg-gradient-to-r from-black/80 to-transparent hover:from-black/95"
          style={{ border: "none", cursor: "pointer" }}
        >
          ‹
        </button>

        {/* Scroll container */}
        <div
          ref={ref}
          className="flex gap-4 px-4 pb-2 overflow-x-auto scroll-smooth sm:px-6 md:px-10 no-scrollbar"
          style={{ scrollbarWidth: "none", msOverflowStyle: "none" }}
        >
          {loading
            ? Array.from({ length: 8 }).map((_, i) => <SkeletonCard key={i} />)
            : items.map((movie) => (
                <MovieCard key={movie.id} movie={movie} onMovieClick={onMovieClick} />
              ))}
        </div>

        {/* Right arrow */}
        <button
          onClick={() => scroll(1)}
          className="absolute top-0 right-0 z-10 items-center justify-center hidden w-12 text-xl text-white transition-all group-hover:flex bottom-8 bg-gradient-to-l from-black/80 to-transparent hover:from-black/95"
          style={{ border: "none", cursor: "pointer" }}
        >
          ›
        </button>
      </div>
    </section>
  );
}

// Genre Card 
function GenreCard({ genre, genreMovies, onGenreClick }) {
  // Pick up to 4 posters from real data for this genre
  const posters = genreMovies
    .filter((m) => m.poster)
    .slice(0, 4)
    .map((m) => m.poster);

  return (
    <div
      onClick={() => onGenreClick(genre.label)}
      className="relative rounded-xl overflow-hidden cursor-pointer group aspect-[4/3] bg-gray-900"
    >
      {/* 2×2 poster grid */}
      <div className="absolute inset-0 grid grid-cols-2 grid-rows-2">
        {posters.length >= 4 ? (
          posters.map((src, i) => (
            <img
              key={i}
              src={src}
              alt=""
              className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
            />
          ))
        ) : (
          // Fallback show available posters or placeholder blocks
          Array.from({ length: 4 }).map((_, i) =>
            posters[i] ? (
              <img
                key={i}
                src={posters[i]}
                alt=""
                className="object-cover w-full h-full transition-transform duration-500 group-hover:scale-105"
              />
            ) : (
              <div key={i} className="bg-gray-800" />
            )
          )
        )}
      </div>

      <div className="absolute inset-0 bg-gradient-to-t from-black/90 via-black/25 to-transparent" />
      <div className="absolute bottom-0 left-0 right-0 flex items-end justify-between p-3">
        <div>
          <span
            className={`text-[10px] font-bold px-2 py-0.5 rounded text-white uppercase tracking-wide ${genre.color}`}
          >
            Top 10 In
          </span>
          <p className="mt-1 text-sm font-bold text-white sm:text-base">{genre.label}</p>
        </div>
        <div className="flex items-center justify-center text-sm text-white transition-colors border rounded-full w-7 h-7 bg-white/10 border-white/20 group-hover:bg-white/20">
          →
        </div>
      </div>
    </div>
  );
}

//Hero 
function Hero({ movies, loading, onMovieClick }) {
  const [idx, setIdx] = useState(0);
  const [visible, setVisible] = useState(true);

  // Use top-rated movies as hero slides
  const heroMovies = movies.slice(0, 5);

  useEffect(() => {
    if (heroMovies.length === 0) return;
    const interval = setInterval(() => {
      setVisible(false);
      setTimeout(() => {
        setIdx((p) => (p + 1) % heroMovies.length);
        setVisible(true);
      }, 400);
    }, 6000);
    return () => clearInterval(interval);
  }, [heroMovies.length]);

  const goTo = (i) => {
    if (i === idx) return;
    setVisible(false);
    setTimeout(() => { setIdx(i); setVisible(true); }, 400);
  };

  if (loading || heroMovies.length === 0) {
    return (
      <div
        className="relative w-full overflow-hidden bg-gray-900 animate-pulse"
        style={{ height: "clamp(420px, 70vw, 520px)" }}
      />
    );
  }

  const movie = heroMovies[idx];

  return (
    <div
      className="relative w-full overflow-hidden"
      style={{ height: "clamp(420px, 70vw, 520px)" }}
    >
      <div
        className="absolute inset-0"
        style={{ opacity: visible ? 1 : 0, transition: "opacity 0.4s ease" }}
      >
        <img
          src={movie.backdrop ||movie.poster}
          alt={movie.title}
          className="object-cover object-top w-full h-full"
        />
        <div className="absolute inset-0 bg-gradient-to-r from-black via-black/70 to-black/30" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#111] via-transparent to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-b from-black/40 via-transparent to-transparent" />
      </div>

      <div
        className="relative z-10 flex flex-col justify-center w-full h-full px-4 sm:px-6 md:px-10 sm:max-w-md md:max-w-lg"
        style={{ opacity: visible ? 1 : 0, transition: "opacity 0.4s ease" }}
      >
        <h1 className="text-xl sm:text-3xl md:text-4xl lg:text-[46px] font-black text-white leading-tight mb-2 sm:mb-4 drop-shadow-lg">
          {movie.title}
        </h1>

        <div className="flex flex-wrap items-center gap-2 mb-2 sm:gap-4 sm:mb-3">
          <ImdbBadge score={typeof movie.rating === "number" ? movie.rating.toFixed(1) : movie.rating} />
          <span className="text-[11px] sm:text-sm text-gray-400 font-semibold tracking-wide">
            {movie.year} {movie.country}
          </span>
        </div>

        {movie.genres && movie.genres.length > 0 && (
          <div className="flex flex-wrap gap-2 mb-3">
            {movie.genres.slice(0, 3).map((g) => (
              <span
                key={g}
                className="text-[10px] bg-white/10 border border-white/20 text-gray-200 px-2 py-0.5 rounded-full"
              >
                {g}
              </span>
            ))}
          </div>
        )}

        {movie.plot && (
          <p className="text-gray-300 text-xs sm:text-sm leading-relaxed mb-4 sm:mb-5 line-clamp-3 max-w-[280px] sm:max-w-sm md:max-w-md">
            {movie.plot}
          </p>
        )}

        <button
          onClick={() => onMovieClick && onMovieClick(movie)}
          style={{ backgroundColor: "#e50914", color: "#fff", border: "none", cursor: "pointer" }}
          className="text-white text-xs sm:text-sm font-bold px-4 sm:px-7 py-1.5 sm:py-2.5 rounded-lg w-fit transition-colors duration-200 tracking-wide hover:opacity-90"
        >
          See More
        </button>
      </div>

      {/* Dot navigation */}
      <div
        className="absolute z-10 flex gap-1 bottom-4 left-4 sm:left-6 md:left-10"
        style={{ alignItems: "center" }}
      >
        {heroMovies.map((_, i) => (
          <button
            key={i}
            onClick={() => goTo(i)}
            style={{
              height: "3px",
              width: i === idx ? "14px" : "5px",
              background: i === idx ? "white" : "rgba(255,255,255,0.3)",
              padding: 0, margin: 0, border: "none", outline: "none",
              cursor: "pointer", borderRadius: "999px",
              transition: "all 0.3s ease", display: "block", flexShrink: 0,
            }}
          />
        ))}
      </div>
    </div>
  );
}

// HomePage
export default function HomePage() {
  const navigate = useNavigate();

  const [trending,    setTrending]    = useState([]);
  const [newArrival,  setNewArrival]  = useState([]);
  const [allMovies,   setAllMovies]   = useState([]);
  const [loading,     setLoading]     = useState(true);

  const [warming,     setWarming]     = useState(false);
  useEffect(() => {
    const fetchAll = async () => {
      try {
        // Fetch trending (top rated) and new arrivals in parallel
        const [trendingRes, newRes, allRes] = await Promise.all([
          fetch(`${API}/movies/trending`),
          fetch(`${API}/movies/new-arrivals`),
          fetch(`${API}/movies`),
        ]);

        const [trendingData, newData, allData] = await Promise.all([
          trendingRes.json(),
          newRes.json(),
          allRes.json(),
        ]);

        setTrending(trendingData);
        setNewArrival(newData);
        setAllMovies(allData);
      } catch (err) {
        console.error("Failed to fetch movies:", err);
      } finally {
        setLoading(false);
      }
    };

    fetchAll();
  }, []);

  const handleMovieClick = (movie) => navigate(`/movies/${movie.id}`);
  const handleSeeMore    = ()      => navigate("/movies");
  const handleGenreClick = (genre) =>
    navigate(`/movies?sort=imdb_top10&genre=${encodeURIComponent(genre)}`);

  // Build a genre movies map from all movies (for GenreCard posters)
  const genreMoviesMap = {};
  for (const cfg of GENRE_CONFIG) {
    genreMoviesMap[cfg.label] = allMovies
      .filter((m) =>
        Array.isArray(m.genres) &&
        m.genres.some((g) => g.toLowerCase() === cfg.label.toLowerCase())
      )
      .slice(0, 4);
  }

  // heroMovies from allMovies sorted by rating 
  const [heroMovies, setHeroMovies] = useState([]);

  useEffect(() => {
    if (allMovies.length === 0) return;
    const top5 = [...allMovies]
      .sort((a, b) => (b.rating || 0) - (a.rating || 0))
      .slice(0, 5);

    // Fetch full details for each hero movie to get plot
    Promise.all(
      top5.map(m =>
        fetch(`${API}/movies/${m.id}`).then(r => r.json()).catch(() => m)
      )
    ).then(setHeroMovies);
  }, [allMovies]);

  return (
    <div
      className="w-full min-h-screen font-sans text-white"
      style={{ background: "#111", overflowX: "clip" }}
    >
      <Navbar />
      
      {/* Warming-up banner */}
      {warming && (
        <div style={{
          background: "#1a1a2e", borderBottom: "1px solid #e5091422",
          padding: "10px 20px", textAlign: "center", fontSize: "13px", color: "#aaa"
        }}>
          ⏳ Server warming up, loading movies… this takes ~30 seconds on first visit.
        </div>
      )}

      <Hero
        movies={heroMovies}
        loading={loading || heroMovies.length === 0}
        onMovieClick={handleMovieClick}
      />

      <div className="pt-6 sm:pt-8">
        <ScrollRow
          title="Trending"
          items={trending}
          loading={loading}
          onMovieClick={handleMovieClick}
          onSeeMore={handleSeeMore}
        />
        <ScrollRow
          title="New Arrival"
          items={newArrival}
          loading={loading}
          onMovieClick={handleMovieClick}
          onSeeMore={handleSeeMore}
        />

        {/* Popular Top 10 In Genres */}
        <section className="px-4 pb-16 sm:px-6 md:px-10">
          <h2 className="mb-4 text-lg font-bold text-white sm:text-xl md:text-2xl sm:mb-5">
            Popular Top 10 In Genres
          </h2>
          <div className="grid grid-cols-2 gap-3 md:grid-cols-4 sm:gap-4">
            {GENRE_CONFIG.map((g) => (
              <GenreCard
                key={g.label}
                genre={g}
                genreMovies={genreMoviesMap[g.label] || []}
                onGenreClick={handleGenreClick}
              />
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}