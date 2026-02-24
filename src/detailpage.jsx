import { useState, useEffect } from "react";
import { useParams } from "react-router-dom";
import Navbar from "./Navbar";

const API = "http://127.0.0.1:5000";

// Loading Skeleton
function LoadingSkeleton() {
  return (
    <div className="w-full min-h-screen bg-[#0d0d0d] text-white animate-pulse">
      <div className="w-full h-[420px] bg-gray-800" />
      <div className="w-full px-6 md:px-12 py-10 grid grid-cols-1 md:grid-cols-2 gap-10">
        <div className="space-y-4">
          <div className="h-5 bg-gray-700 rounded w-1/3" />
          <div className="h-3 bg-gray-800 rounded w-full" />
          <div className="h-3 bg-gray-800 rounded w-5/6" />
          <div className="h-3 bg-gray-800 rounded w-4/6" />
          <div className="h-5 bg-gray-700 rounded w-1/3 mt-8" />
          <div className="flex gap-4 mt-2">
            {[1, 2, 3, 4].map((i) => (
              <div key={i} className="flex flex-col items-center gap-2">
                <div className="w-20 h-20 rounded-full bg-gray-700" />
                <div className="h-2 w-14 bg-gray-700 rounded" />
              </div>
            ))}
          </div>
        </div>
        <div className="space-y-4">
          <div className="h-5 bg-gray-700 rounded w-1/3" />
          <div className="h-3 bg-gray-800 rounded w-2/3" />
          <div className="h-3 bg-gray-800 rounded w-1/2" />
          <div className="h-5 bg-gray-700 rounded w-1/2 mt-8" />
          <div className="h-3 bg-gray-800 rounded w-3/4" />
          <div className="h-3 bg-gray-800 rounded w-2/3" />
          <div className="h-3 bg-gray-800 rounded w-1/2" />
        </div>
      </div>
    </div>
  );
}

// Error State
function ErrorState({ onBack }) {
  return (
    <div className="w-full min-h-screen bg-[#0d0d0d] text-white flex flex-col items-center justify-center gap-6">
      <div className="text-6xl">🎬</div>
      <h2 className="text-2xl font-bold text-gray-200">Movie not found</h2>
      <p className="text-gray-500 text-sm">Invalid ID or movie not in Top 250</p>
      <button
        onClick={onBack}
        className="px-6 py-2.5 bg-red-600 hover:bg-red-500 rounded-lg font-semibold transition-colors text-sm"
        style={{ border: "none" }}
      >
        ← Go Back
      </button>
    </div>
  );
}

//Detail Page
export default function DetailPage() {
  const { id } = useParams();
  const [movie,       setMovie]       = useState(null);
  const [loading,     setLoading]     = useState(true);
  const [error,       setError]       = useState(false);
  const [hoveredCast, setHoveredCast] = useState(null);

  useEffect(() => {

    fetch(`${API}/movies/${id}`)
      .then(res => {
        if (!res.ok) throw new Error("Movie not found");
        return res.json();
      })
      .then(data => {
        setMovie(data);
        setLoading(false);
      })
      .catch(() => {
        setError(true);
        setLoading(false);
      });
  }, [id]);

  const handleBack = () => window.history.back();

  if (loading) return <LoadingSkeleton />;
  if (error || !movie) return <ErrorState onBack={handleBack} />;

  return (
    <div
      className="w-full min-h-screen text-white font-sans"
      style={{ background: "#111", overflowX: "clip" }}
    >
      <Navbar />

      {/*  HERO */}
      <div className="relative w-full h-[420px] md:h-[480px] overflow-hidden">
        <img
          src={movie.backdrop}
          alt={movie.title}
          className="absolute inset-0 w-full h-full object-cover object-center"
          onError={(e) => { e.target.style.display = 'none'; }}
        />
        <div className="absolute inset-0 bg-gradient-to-r from-[#000000] via-[#0d0d0d88] to-transparent" />
        <div className="absolute inset-0 bg-gradient-to-t from-[#0d0d0d] via-transparent to-transparent" />

        <div className="relative z-10 flex flex-col justify-end h-full px-6 md:px-12 pb-10 w-full max-w-4xl">
          <h1
            className="text-4xl md:text-5xl font-black mb-3 drop-shadow-lg"
            style={{ fontFamily: "'Georgia', serif", letterSpacing: "-1px" }}
          >
            {movie.title}
          </h1>
          <div className="flex items-center gap-3 text-sm text-gray-300 font-medium flex-wrap">
            <span>{movie.year}</span>
            {movie.certificate && movie.certificate !== "N/A" && (
              <span className="border border-gray-500 px-1.5 py-0.5 rounded text-xs">
                {movie.certificate}
              </span>
            )}
            {movie.runtime && <span>{movie.runtime}</span>}
          </div>
        </div>
      </div>

      {/* BODY*/}
      <div className="w-full px-6 md:px-12 py-10 grid grid-cols-1 md:grid-cols-2 gap-10 md:gap-16">

        {/* LEFT */}
        <div className="space-y-10">

          {/* Plot */}
          {movie.plot && (
            <section>
              <h2 className="text-base font-bold mb-3 tracking-widest uppercase text-gray-200 border-b border-gray-700 pb-2">
                Plot Summary
              </h2>
              <p className="text-gray-400 leading-relaxed text-sm">{movie.plot}</p>
            </section>
          )}

          {/* Cast */}
          {movie.cast && movie.cast.length > 0 && (
            <section>
              <h2 className="text-base font-bold mb-5 tracking-widest uppercase text-gray-200 border-b border-gray-700 pb-2">
                Cast
              </h2>
              <div className="flex gap-5 flex-wrap">
                {movie.cast.map((member, i) => (
                  <div
                    key={i}
                    className="flex flex-col items-center gap-2 cursor-pointer"
                    onMouseEnter={() => setHoveredCast(i)}
                    onMouseLeave={() => setHoveredCast(null)}
                  >
                    <div
                      className={`w-20 h-20 rounded-full overflow-hidden border-2 transition-all duration-300 ${
                        hoveredCast === i
                          ? "border-red-500 scale-110 shadow-lg shadow-red-900/40"
                          : "border-gray-700"
                      }`}
                    >
                      {/* Use generated avatar IMDb doesn't expose cast photos via scraping */}
                      <img
                        src={member.img || `https://ui-avatars.com/api/?name=${encodeURIComponent(member.name)}&background=333&color=fff&size=150`}
                        alt={member.name}
                        className="w-full h-full object-cover"
                        onError={(e) => {
                          e.target.src = `https://ui-avatars.com/api/?name=${encodeURIComponent(member.name)}&background=444&color=fff&size=150`;
                        }}
                      />
                    </div>
                    <span
                      className={`text-xs text-center transition-colors duration-200 ${
                        hoveredCast === i ? "text-red-400" : "text-gray-400"
                      }`}
                    >
                      {member.name}
                    </span>
                  </div>
                ))}
              </div>
            </section>
          )}
        </div>

        {/* RIGHT */}
        <div className="space-y-10">

          {/* Movie Info */}
          <section>
            <h2 className="text-base font-bold mb-3 tracking-widest uppercase text-gray-200 border-b border-gray-700 pb-2">
              Movie Info
            </h2>
            <div className="space-y-2 text-sm">
              {movie.director && (
                <p>
                  <span className="text-gray-400 font-semibold">Director: </span>
                  <span className="text-red-400">{movie.director}</span>
                </p>
              )}
              {movie.genres && movie.genres.length > 0 && (
                <p>
                  <span className="text-gray-400 font-semibold">Genres: </span>
                  {movie.genres.map((g, i, arr) => (
                    <span key={g}>
                      <span className="text-red-400">{g}</span>
                      {i < arr.length - 1 && <span className="text-gray-600">, </span>}
                    </span>
                  ))}
                </p>
              )}
              {movie.certificate && movie.certificate !== "N/A" && (
                <p>
                  <span className="text-gray-400 font-semibold">Certificate: </span>
                  <span className="text-gray-200">{movie.certificate}</span>
                </p>
              )}
            </div>
          </section>

          {/* Technical Specs */}
          <section>
            <h2 className="text-base font-bold mb-3 tracking-widest uppercase text-gray-200 border-b border-gray-700 pb-2">
              Technical Specs &amp; Box Office
            </h2>
            <div className="space-y-2 text-sm">
              {[
                { label: "Budget",               value: movie.budget      },
                { label: "Worldwide Box Office",  value: movie.boxOffice   },
                { label: "Runtime",               value: movie.runtime     },
                { label: "Release Date",          value: movie.releaseDate },
              ].filter(({ value }) => value).map(({ label, value }) => (
                <p key={label}>
                  <span className="text-gray-400 font-semibold">{label}: </span>
                  <span className="text-gray-200">{value}</span>
                </p>
              ))}
            </div>
          </section>

          {/* Awards & Ratings */}
          {(movie.imdbScore || movie.awardsInfo) && (
            <section>
              <h2 className="text-base font-bold mb-3 tracking-widest uppercase text-gray-200 border-b border-gray-700 pb-2">
                Awards &amp; Ratings
              </h2>
              <div className="space-y-2 text-sm">
                {movie.imdbScore && (
                  <p>
                    <span className="text-gray-400 font-semibold">IMDb Score: </span>
                    <span className="text-gray-200">{movie.imdbScore}</span>
                  </p>
                )}
                {movie.awardsInfo && (
                  <p>
                    <span className="text-gray-400 font-semibold">Awards: </span>
                    <span className="text-gray-200">{movie.awardsInfo}</span>
                  </p>
                )}
              </div>
            </section>
          )}
        </div>
      </div>
    </div>
  );
}
