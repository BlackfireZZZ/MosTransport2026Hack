import type { StopDetail } from '../types'
import { formatKm, isUnnamed, stopLabel } from '../format'

interface Props {
  stop: StopDetail | null
  loading: boolean
  error: string | null
  onClose: () => void
  onSetFrom: () => void
  onSetTo: () => void
  onOpenNeighbour: (id: number) => void
}

export function StopInspector({
  stop,
  loading,
  error,
  onClose,
  onSetFrom,
  onSetTo,
  onOpenNeighbour,
}: Props) {
  if (!loading && !error && !stop) return null

  const outgoing = stop?.neighbours.filter((n) => n.direction === 'out') ?? []
  const incoming = stop?.neighbours.filter((n) => n.direction === 'in') ?? []

  return (
    <div className="inspector" role="dialog" aria-label="Stop details">
      <button type="button" className="close" onClick={onClose} aria-label="Close">
        ×
      </button>

      {loading && <p className="muted">Loading stop…</p>}
      {error && <p className="error">{error}</p>}

      {stop && (
        <>
          <h3 className={isUnnamed(stop.name) ? 'is-unnamed' : ''}>{stopLabel(stop)}</h3>
          <p className="small muted mono">
            OSM node {stop.id} · {stop.lat.toFixed(5)}, {stop.lon.toFixed(5)}
          </p>

          <div className="inspector-section">
            <h4>Routes calling here</h4>
            {stop.routes.length ? (
              <div className="chips chips--static">
                {stop.routes.map((ref) => (
                  <span className="chip chip--static" key={ref}>
                    {ref}
                  </span>
                ))}
              </div>
            ) : (
              <p className="muted small">None recorded.</p>
            )}
          </div>

          <div className="row">
            <button type="button" className="pick" onClick={onSetFrom}>
              set as from
            </button>
            <button type="button" className="pick" onClick={onSetTo}>
              set as to
            </button>
          </div>

          {/*
            The graph is directed, so in- and out-neighbours are listed separately --
            a stop you can reach from here is not necessarily one you can get back from.
          */}
          <div className="inspector-section">
            <h4>Onward ({outgoing.length})</h4>
            {outgoing.map((n) => (
              <div className="neighbour" key={`out-${n.id}`}>
                <button type="button" className="linkish" onClick={() => onOpenNeighbour(n.id)}>
                  {stopLabel(n)}
                </button>
                <span className="n-len mono">{formatKm(n.length_m)}</span>
              </div>
            ))}
            {!outgoing.length && <p className="muted small">Terminus in this direction.</p>}
          </div>

          <div className="inspector-section">
            <h4>Arriving from ({incoming.length})</h4>
            {incoming.map((n) => (
              <div className="neighbour" key={`in-${n.id}`}>
                <button type="button" className="linkish" onClick={() => onOpenNeighbour(n.id)}>
                  {stopLabel(n)}
                </button>
                <span className="n-len mono">{formatKm(n.length_m)}</span>
              </div>
            ))}
            {!incoming.length && <p className="muted small">Nothing arrives here.</p>}
          </div>

          <p className="small muted">
            A physical stop is usually two nodes, one per direction, with slightly
            different coordinates and different ids.
          </p>
        </>
      )}
    </div>
  )
}
