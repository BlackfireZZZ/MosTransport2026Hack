import { useMemo, useState } from 'react'
import type { RouteSummary } from '../types'
import { compareRouteRefs, formatKm, plural } from '../format'

interface Props {
  routes: RouteSummary[]
  selected: string | null
  loading: boolean
  onSelect: (ref: string | null) => void
}

export function RoutePanel({ routes, selected, loading, onSelect }: Props) {
  const [filter, setFilter] = useState('')

  const sorted = useMemo(
    () => [...routes].sort((a, b) => compareRouteRefs(a.ref, b.ref)),
    [routes],
  )

  const visible = useMemo(() => {
    const needle = filter.trim().toLocaleLowerCase('ru')
    if (!needle) return sorted
    // Substring match on the ref as a string -- refs like "1а" and "т1" must not be
    // coerced to numbers anywhere.
    return sorted.filter((route) => route.ref.toLocaleLowerCase('ru').includes(needle))
  }, [sorted, filter])

  const current = selected ? routes.find((route) => route.ref === selected) : undefined

  return (
    <section className="panel">
      <h2>
        Routes <span className="count">{loading ? '…' : sorted.length}</span>
      </h2>

      <div className="row">
        <input
          type="search"
          value={filter}
          onChange={(event) => setFilter(event.target.value)}
          placeholder="filter refs, e.g. 1а or т2…"
          aria-label="Filter route refs"
        />
      </div>

      <div className="chips" role="group" aria-label="Tram routes">
        <button
          type="button"
          className={`chip chip--all ${selected === null ? 'is-on' : ''}`}
          onClick={() => onSelect(null)}
        >
          all
        </button>
        {visible.map((route) => (
          <button
            key={route.ref}
            type="button"
            className={`chip ${selected === route.ref ? 'is-on' : ''}`}
            title={`${plural(route.stop_count, 'stop')} · ${formatKm(route.length_m)}`}
            onClick={() => onSelect(selected === route.ref ? null : route.ref)}
          >
            {route.ref}
          </button>
        ))}
      </div>

      {!loading && visible.length === 0 && filter.trim() !== '' && (
        <p className="muted small">No route ref matches “{filter}”.</p>
      )}

      {!loading && sorted.length === 0 && filter.trim() === '' && (
        <p className="muted small">No routes loaded — is the backend running?</p>
      )}

      {current && (
        <div className="detail">
          <dl>
            <dt>Route</dt>
            <dd className="mono">{current.ref}</dd>
            <dt>Stops</dt>
            <dd>{current.stop_count}</dd>
            <dt>Track</dt>
            <dd>{formatKm(current.length_m)}</dd>
            <dt>Component</dt>
            <dd>
              {current.component === 0 ? 'main network' : `north network (#${current.component})`}
            </dd>
          </dl>
        </div>
      )}
    </section>
  )
}
