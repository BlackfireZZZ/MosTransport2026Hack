import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { Stop } from '../types'
import { isUnnamed, stopLabel } from '../format'

interface Props {
  onPick: (stop: Stop) => void
}

export function StopSearch({ onPick }: Props) {
  const [query, setQuery] = useState('')
  const [results, setResults] = useState<Stop[]>([])
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    const needle = query.trim()
    if (needle.length < 2) {
      setResults([])
      setError(null)
      return undefined
    }
    const controller = new AbortController()
    // Debounced: the backend matches with a casefold substring scan over 856 stops.
    const timer = setTimeout(() => {
      setBusy(true)
      api
        .stops(needle, 30, controller.signal)
        .then((stops) => {
          setResults(stops)
          setError(null)
        })
        .catch((err: unknown) => {
          if (controller.signal.aborted) return
          setError(err instanceof ApiError ? err.message : String(err))
          setResults([])
        })
        .finally(() => {
          if (!controller.signal.aborted) setBusy(false)
        })
    }, 220)

    return () => {
      controller.abort()
      clearTimeout(timer)
    }
  }, [query])

  return (
    <section className="panel">
      <h2>
        Stop search <span className="count">{busy ? '…' : results.length || ''}</span>
      </h2>
      <input
        type="search"
        value={query}
        onChange={(event) => setQuery(event.target.value)}
        placeholder="type a stop name, e.g. Курский…"
        aria-label="Search stops by name"
      />

      {error && <p className="error">{error}</p>}

      {!error && query.trim().length >= 2 && !busy && results.length === 0 && (
        <p className="muted small">Nothing matches “{query.trim()}”.</p>
      )}

      <div className="results">
        {results.map((stop) => (
          <button
            key={stop.id}
            type="button"
            className="result"
            onClick={() => onPick(stop)}
            title={`OSM node ${stop.id}`}
          >
            <span className={`name ${isUnnamed(stop.name) ? 'is-unnamed' : ''}`}>
              {stopLabel(stop)}
            </span>
            <span className="refs">{stop.routes.join(' · ')}</span>
          </button>
        ))}
      </div>
    </section>
  )
}
