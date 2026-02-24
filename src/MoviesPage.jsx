import { useState, useMemo, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import Navbar from './Navbar'

const API = "http://127.0.0.1:5000"

// All genres sourced from real IMDb data these are the most common ones in Top 250
const ALL_GENRES = [
  'Action', 'Adventure', 'Animation', 'Biography', 'Comedy',
  'Crime', 'Drama', 'Fantasy', 'Film-Noir', 'History',
  'Horror', 'Music', 'Mystery', 'Romance', 'Sci-Fi',
  'Sport', 'Thriller', 'War', 'Western',
]

//IMDb Badge
function ImdbBadge({ score }) {
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', gap: '4px' }}>
      <span style={{
        background: '#f5c518', color: '#000', fontWeight: 900,
        fontSize: '9px', padding: '1px 4px', borderRadius: '2px',
        letterSpacing: '0.3px', lineHeight: 1.4,
      }}>IMDb</span>
      <span style={{ color: '#f5c518', fontSize: '11px', fontWeight: 700 }}>
        {score != null ? (typeof score === 'number' ? score.toFixed(1) : score) : 'N/A'}
      </span>
    </span>
  )
}

// Skeleton Card
function SkeletonCard() {
  return (
    <div style={{ animation: 'pulse 1.5s infinite' }}>
      <div style={{ borderRadius: '6px', aspectRatio: '2/3', background: '#2a2a2a' }} />
      <div style={{ marginTop: '8px' }}>
        <div style={{ height: '13px', background: '#333', borderRadius: '4px', marginBottom: '6px' }} />
        <div style={{ height: '11px', background: '#2a2a2a', borderRadius: '4px', width: '60%' }} />
      </div>
    </div>
  )
}

//Movie Card 
function MovieCard({ movie }) {
  const navigate = useNavigate()
  const [hovered,  setHovered]  = useState(false)
  const [imgError, setImgError] = useState(false)

  return (
    <div
      onClick={() => navigate(`/movies/${movie.id}`)}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        cursor: 'pointer',
        transform: hovered ? 'scale(1.04)' : 'scale(1)',
        transition: 'transform 0.2s ease',
      }}
    >
      <div style={{
        position: 'relative', borderRadius: '6px', overflow: 'hidden',
        aspectRatio: '2/3', background: '#1c1c1c',
      }}>
        {!imgError ? (
          <img
            src={movie.poster}
            alt={movie.title}
            onError={() => setImgError(true)}
            style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
          />
        ) : (
          <div style={{
            width: '100%', height: '100%', display: 'flex', alignItems: 'center',
            justifyContent: 'center', background: '#2a2a2a', color: '#666',
            fontSize: '12px', padding: '8px', textAlign: 'center',
          }}>
            {movie.title}
          </div>
        )}

        {/* Rank badge if present */}
        {movie.rank && (
          <div style={{
            position: 'absolute', top: '6px', left: '6px',
            background: 'rgba(0,0,0,0.75)', color: '#f5c518',
            fontSize: '10px', fontWeight: 700, padding: '2px 6px', borderRadius: '4px',
          }}>
            #{movie.rank}
          </div>
        )}
      </div>
      <div style={{ marginTop: '8px' }}>
        <div style={{
          color: '#fff', fontWeight: 600, fontSize: '13px',
          whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis',
        }}>
          {movie.title}
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '3px' }}>
          <span style={{ color: '#999', fontSize: '12px' }}>{movie.year}</span>
          {movie.rating != null && <ImdbBadge score={movie.rating} />}
        </div>
        {movie.genres && movie.genres.length > 0 && (
          <div style={{ marginTop: '4px', display: 'flex', gap: '4px', flexWrap: 'wrap' }}>
            {movie.genres.slice(0, 2).map(g => (
              <span key={g} style={{
                fontSize: '9px', background: '#2a2a2a', color: '#aaa',
                padding: '1px 5px', borderRadius: '3px',
              }}>{g}</span>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

//useIsMobile
function useIsMobile() {
  const [isMobile, setIsMobile] = useState(window.innerWidth < 768)
  useEffect(() => {
    const handler = () => setIsMobile(window.innerWidth < 768)
    window.addEventListener('resize', handler)
    return () => window.removeEventListener('resize', handler)
  }, [])
  return isMobile
}

//Filter Panel
function FilterPanel({
  selectedGenres, toggleGenre,
  yearInput, setYearInput,
  languageInput, setLanguageInput,
  minRating, setMinRating,
  onApply, onClear,
}) {
  const hasFilter = selectedGenres.length > 0 || yearInput || languageInput || minRating

  return (
    <div>
      {/* Genres */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Genres
        </h3>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', maxHeight: '260px', overflowY: 'auto', paddingRight: '4px' }}>
          {ALL_GENRES.map(g => (
            <label key={g} style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer', fontSize: '13px', color: selectedGenres.includes(g) ? '#fff' : '#aaa' }}>
              <input
                type="checkbox"
                checked={selectedGenres.includes(g)}
                onChange={() => toggleGenre(g)}
                style={{ accentColor: '#e50914', cursor: 'pointer' }}
              />
              {g}
            </label>
          ))}
        </div>
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '20px 0' }} />

      {/* Release Year */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Release Year
        </h3>
        <input
          type="text"
          placeholder="e.g. 2010"
          value={yearInput}
          onChange={e => setYearInput(e.target.value)}
          style={{
            width: '100%', background: '#2a2a2a', border: '1px solid #3a3a3a',
            borderRadius: '6px', padding: '8px 10px', color: '#fff',
            fontSize: '13px', outline: 'none', boxSizing: 'border-box',
          }}
        />
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '20px 0' }} />

      {/* Language / Country */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Country / Language
        </h3>
        <input
          type="text"
          placeholder="e.g. United States, Japan"
          value={languageInput}
          onChange={e => setLanguageInput(e.target.value)}
          style={{
            width: '100%', background: '#2a2a2a', border: '1px solid #3a3a3a',
            borderRadius: '6px', padding: '8px 10px', color: '#fff',
            fontSize: '13px', outline: 'none', boxSizing: 'border-box',
          }}
        />
      </div>

      <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '20px 0' }} />

      {/* Min IMDb Rating */}
      <div>
        <h3 style={{ fontSize: '13px', fontWeight: 700, color: '#fff', marginBottom: '10px', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
          Min IMDb Rating
        </h3>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <input
            type="range"
            min="7" max="10" step="0.1"
            value={minRating || 7}
            onChange={e => setMinRating(e.target.value)}
            style={{ flex: 1, accentColor: '#e50914' }}
          />
          <span style={{ color: '#f5c518', fontWeight: 700, fontSize: '14px', minWidth: '32px' }}>
            {minRating || '7.0'}
          </span>
        </div>
        {minRating && (
          <button
            onClick={() => setMinRating('')}
            style={{ marginTop: '6px', background: 'none', border: 'none', color: '#666', fontSize: '11px', cursor: 'pointer', padding: 0 }}
          >
            Reset rating filter
          </button>
        )}
      </div>

      {hasFilter && (
        <>
          <hr style={{ border: 'none', borderTop: '1px solid #333', margin: '20px 0' }} />
          <button
            onClick={onClear}
            style={{
              width: '100%', background: '#333', color: '#fff', border: 'none',
              borderRadius: '6px', padding: '8px', fontSize: '13px', fontWeight: 600,
              cursor: 'pointer', marginBottom: '8px',
            }}
          >
            Clear Filters
          </button>
        </>
      )}
    </div>
  )
}

//Main MoviesPage
export default function MoviesPage() {
  const [movies,       setMovies]       = useState([])
  const [loading,      setLoading]      = useState(true)
  const [searchParams, setSearchParams] = useSearchParams()
  const [selectedGenres, setSelectedGenres] = useState([])
  const [yearInput,    setYearInput]    = useState('')
  const [languageInput,setLanguageInput]= useState('')
  const [minRating,    setMinRating]    = useState('')
  const [drawerOpen,   setDrawerOpen]   = useState(false)
  const isMobile = useIsMobile()

  // Read URL params
  const urlSearch = searchParams.get('search') || ''
  const urlSort   = searchParams.get('sort')   || ''
  const urlGenre  = searchParams.get('genre')  || ''

  const [searchQuery, setSearchQuery] = useState(urlSearch)

  // Sync URL local search state
  useEffect(() => { setSearchQuery(urlSearch) }, [urlSearch])

  // Pre-select genre from URL (from genre card on HomePage)
  useEffect(() => {
    if (urlGenre) setSelectedGenres([urlGenre])
  }, [urlGenre])

  // Fetch ALL movies once on mount
  useEffect(() => {
    fetch(`${API}/movies`)
      .then(res => res.json())
      .then(data => { setMovies(data); setLoading(false) })
      .catch(err => { console.error("Error fetching movies:", err); setLoading(false) })
  }, [])

  const toggleGenre = (g) =>
    setSelectedGenres(prev => prev.includes(g) ? prev.filter(x => x !== g) : [...prev, g])

  const handleClear = () => {
    setSelectedGenres([])
    setYearInput('')
    setLanguageInput('')
    setMinRating('')
    setSearchQuery('')
    setSearchParams({})
  }

  const isTop10 = urlSort === 'imdb_top10'

  // All filtering is done client-side on the full 250-movie list 
  const filtered = useMemo(() => {
    let list = movies.filter(m => {
      // Text search title, genres, language/country
      if (searchQuery.trim()) {
        const q = searchQuery.trim().toLowerCase()
        const matchesTitle    = (m.title    || '').toLowerCase().includes(q)
        const matchesGenre    = (m.genres   || []).some(g => g.toLowerCase().includes(q))
        const matchesLanguage = (m.language || '').toLowerCase().includes(q)
        if (!matchesTitle && !matchesGenre && !matchesLanguage) return false
      }

      // Genre checkboxes
      if (selectedGenres.length > 0) {
        const movieGenres = (m.genres || []).map(g => g.toLowerCase())
        if (!selectedGenres.some(g => movieGenres.includes(g.toLowerCase()))) return false
      }

      // Year
      if (yearInput.trim() && String(m.year) !== yearInput.trim()) return false

      // Country / language
      if (languageInput.trim()) {
        const lang = (m.language || '').toLowerCase()
        if (!lang.includes(languageInput.trim().toLowerCase())) return false
      }

      // Min rating
      if (minRating && (m.rating || 0) < parseFloat(minRating)) return false

      return true
    })

    // Top-10 by IMDb rating when coming from genre card
    if (isTop10) {
      list = [...list].sort((a, b) => (b.rating || 0) - (a.rating || 0)).slice(0, 10)
    }

    return list
  }, [movies, searchQuery, selectedGenres, yearInput, languageInput, minRating, isTop10])

  const activeFilterCount =
    selectedGenres.length +
    (yearInput    ? 1 : 0) +
    (languageInput? 1 : 0) +
    (minRating    ? 1 : 0) +
    (searchQuery  ? 1 : 0)

  const filterProps = {
    selectedGenres, toggleGenre,
    yearInput, setYearInput,
    languageInput, setLanguageInput,
    minRating, setMinRating,
    onClear: handleClear,
  }

  return (
    <div style={{ minHeight: '100vh', background: '#141414', color: '#fff', fontFamily: 'sans-serif' }}>
      <Navbar />

      {/*Mobile Filter Drawer*/}
      {isMobile && drawerOpen && (
        <>
          <div
            onClick={() => setDrawerOpen(false)}
            style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.6)', zIndex: 100, top: '68px' }}
          />
          <div style={{
            position: 'fixed', top: '68px', left: 0, bottom: 0,
            width: '280px', background: '#1a1a1a', borderRight: '1px solid #2a2a2a',
            zIndex: 101, overflowY: 'auto', padding: '24px 20px', boxSizing: 'border-box',
          }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
              <h2 style={{ fontSize: '18px', fontWeight: 700, margin: 0 }}>Filter By</h2>
              <button
                onClick={() => setDrawerOpen(false)}
                style={{ background: 'none', border: 'none', color: '#fff', cursor: 'pointer', padding: '4px' }}
              >
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
                </svg>
              </button>
            </div>
            <FilterPanel {...filterProps} />
          </div>
        </>
      )}

      <div style={{ display: 'flex', alignItems: 'flex-start' }}>

        {/*Desktop Sidebar*/}
        {!isMobile && (
          <aside style={{
            width: '240px', minWidth: '240px',
            background: '#1a1a1a', borderRight: '1px solid #2a2a2a',
            position: 'sticky', top: '68px',
            height: 'calc(100vh - 68px)', overflowY: 'auto',
            padding: '24px 20px', boxSizing: 'border-box', flexShrink: 0,
          }}>
            <FilterPanel {...filterProps} />
          </aside>
        )}

        {/*Main content */}
        <main style={{ flex: 1, padding: isMobile ? '20px 16px' : '32px 32px', overflowY: 'auto' }}>

          {/* Header row */}
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
            <div>
              <h1 style={{ fontSize: isMobile ? '22px' : '28px', fontWeight: 800, margin: 0 }}>
                Browse All Movies
              </h1>

              {/* Top 10 IMDb banner */}
              {isTop10 && (
                <div style={{
                  display: 'inline-flex', alignItems: 'center', gap: '8px',
                  marginTop: '8px', background: '#1a1a1a',
                  border: '1px solid #f5c518', borderRadius: '8px', padding: '6px 12px',
                }}>
                  <span style={{ background: '#f5c518', color: '#000', fontWeight: 900, fontSize: '10px', padding: '2px 6px', borderRadius: '3px' }}>IMDb</span>
                  <span style={{ color: '#f5c518', fontSize: '13px', fontWeight: 700 }}>
                    Top 10 Highest Rated
                    {urlGenre && <span style={{ color: '#fff', fontWeight: 400 }}> · {urlGenre}</span>}
                  </span>
                  <button
                    onClick={handleClear}
                    style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', fontSize: '16px', lineHeight: 1, padding: 0 }}
                    title="Clear"
                  >×</button>
                </div>
              )}

              {/* Active search pill */}
              {searchQuery && (
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginTop: '8px' }}>
                  <span style={{ fontSize: '13px', color: '#aaa' }}>Results for:</span>
                  <span style={{
                    display: 'inline-flex', alignItems: 'center', gap: '6px',
                    background: '#2a2a2a', border: '1px solid #3a3a3a',
                    borderRadius: '999px', padding: '3px 10px 3px 12px',
                    fontSize: '13px', color: '#fff', fontWeight: 600,
                  }}>
                    {searchQuery}
                    <button
                      onClick={handleClear}
                      style={{ background: 'none', border: 'none', color: '#aaa', cursor: 'pointer', padding: '0', lineHeight: 1, fontSize: '16px', display: 'flex' }}
                      title="Clear search"
                    >×</button>
                  </span>
                  <span style={{ fontSize: '12px', color: '#666' }}>
                    {filtered.length} {filtered.length === 1 ? 'result' : 'results'}
                  </span>
                </div>
              )}

              {/* Movie count */}
              {!loading && !searchQuery && (
                <p style={{ fontSize: '13px', color: '#666', marginTop: '4px', marginBottom: 0 }}>
                  Showing {filtered.length} of {movies.length} movies
                </p>
              )}
            </div>

            {/* Mobile filter button */}
            {isMobile && (
              <button
                onClick={() => setDrawerOpen(true)}
                style={{
                  display: 'flex', alignItems: 'center', gap: '6px',
                  background: '#2a2a2a', border: '1px solid #3a3a3a',
                  color: '#fff', borderRadius: '8px', padding: '8px 14px',
                  fontSize: '13px', fontWeight: 600, cursor: 'pointer',
                  position: 'relative',
                }}
              >
                <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth={2}>
                  <line x1="4" y1="6" x2="20" y2="6"/>
                  <line x1="8" y1="12" x2="16" y2="12"/>
                  <line x1="11" y1="18" x2="13" y2="18"/>
                </svg>
                Filters
                {activeFilterCount > 0 && (
                  <span style={{
                    background: '#e50914', color: '#fff', borderRadius: '50%',
                    width: '18px', height: '18px', fontSize: '10px', fontWeight: 700,
                    display: 'flex', alignItems: 'center', justifyContent: 'center',
                    position: 'absolute', top: '-6px', right: '-6px',
                  }}>
                    {activeFilterCount}
                  </span>
                )}
              </button>
            )}
          </div>

          {/* Grid */}
          {loading ? (
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile ? 'repeat(auto-fill, minmax(130px, 1fr))' : 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: isMobile ? '16px 12px' : '20px 16px',
            }}>
              {Array.from({ length: 20 }).map((_, i) => <SkeletonCard key={i} />)}
            </div>
          ) : filtered.length === 0 ? (
            <div style={{ textAlign: 'center', marginTop: '80px' }}>
              <div style={{ fontSize: '48px', marginBottom: '16px' }}>🎬</div>
              <div style={{ color: '#fff', fontSize: '18px', fontWeight: 600, marginBottom: '8px' }}>
                No movies found
              </div>
              <div style={{ color: '#666', fontSize: '14px', marginBottom: '24px' }}>
                {searchQuery
                  ? `No results for "${searchQuery}". Try a different search or adjust your filters.`
                  : 'Try adjusting your filters.'}
              </div>
              <button
                onClick={handleClear}
                style={{
                  background: '#e50914', color: '#fff', border: 'none',
                  borderRadius: '8px', padding: '10px 24px',
                  fontSize: '14px', fontWeight: 600, cursor: 'pointer',
                }}
              >
                Clear All Filters
              </button>
            </div>
          ) : (
            <div style={{
              display: 'grid',
              gridTemplateColumns: isMobile
                ? 'repeat(auto-fill, minmax(130px, 1fr))'
                : 'repeat(auto-fill, minmax(160px, 1fr))',
              gap: isMobile ? '16px 12px' : '20px 16px',
            }}>
              {filtered.map(movie => (
                <MovieCard key={movie.id} movie={movie} />
              ))}
            </div>
          )}
        </main>
      </div>
    </div>
  )
}
