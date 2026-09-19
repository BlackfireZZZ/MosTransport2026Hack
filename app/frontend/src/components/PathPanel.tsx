import type { PathResult, Stop } from '../types'
import { formatKm, isUnnamed, plural, stopLabel } from '../format'

export type PickTarget = 'from' | 'to' | null

interface Props {
  fromStop: Stop | null
  toStop: Stop | null
  pickTarget: PickTarget
  result: PathResult | null
  busy: boolean
  error: string | null
  onArm: (target: PickTarget) => void
  onSwap: () => void
  onClear: () => void
  onRun: () => void
  onFocusStop: (stop: Stop) => void
}

function Slot({
  label,
  stop,
  armed,
  onArm,
}: {
  label: string
  stop: Stop | null
  armed: boolean
  onArm: () => void
}) {
  return (
    <div className="slot">
      <span className="slot-label">{label}</span>
      <span className={`slot-value ${stop ? '' : 'is-empty'}`} title={stop ? `OSM node ${stop.id}` : ''}>
        {stop ? stopLabel(stop) : 'not set'}
      </span>
      <button
        type="button"
        className={`pick ${armed ? 'is-arming' : ''}`}
        onClick={onArm}
        title="Then click a stop on the map, or pick one from the search results"
      >
        {armed ? 'picking…' : 'pick'}
      </button>
    </div>
  )
}

export function PathPanel(props: Props) {
  const { fromStop, toStop, pickTarget, result, busy, error, onArm, onSwap, onClear, onRun, onFocusStop } =
    props

  const runnable = Boolean(fromStop && toStop && fromStop.id !== toStop.id) && !busy

  return (
    <section className="panel">
      <h2>Shortest path</h2>

      <Slot
        label="from"
        stop={fromStop}
        armed={pickTarget === 'from'}
        onArm={() => onArm(pickTarget === 'from' ? null : 'from')}
      />
      <Slot
        label="to"
        stop={toStop}
        armed={pickTarget === 'to'}
        onArm={() => onArm(pickTarget === 'to' ? null : 'to')}
      />

      <div className="row">
        <button type="button" className="primary" disabled={!runnable} onClick={onRun}>
          {busy ? 'Routing…' : 'Find path'}
        </button>
        <button type="button" className="link" onClick={onSwap} disabled={!fromStop && !toStop}>
          swap
        </button>
        <button type="button" className="link" onClick={onClear}>
          clear
        </button>
      </div>

      {fromStop && toStop && fromStop.id === toStop.id && (
        <p className="notice">From and to are the same stop. Pick two different stops.</p>
      )}

      {error && <p className="error">{error}</p>}

      {/*
        `found: false` is a 200 answer, not a failure. The Moscow network splits into
        two pieces with no track between them, so "no path" is often the correct
        result and must not look like a crash.
      */}
      {result && !result.found && (
        <div className="notice notice--nopath">
          <strong>No path exists.</strong>
          <p>{result.reason ?? 'The backend reported no route between these two stops.'}</p>
        </div>
      )}

      {result?.found && (
        <div className="detail">
          <div className="path-summary">
            <div className="tile">
              <div className="v">{formatKm(result.total_length_m)}</div>
              <div className="k">by track</div>
            </div>
            <div className="tile">
              <div className="v">{result.stops.length}</div>
              <div className="k">stops</div>
            </div>
          </div>
          {result.routes.length > 0 && (
            <p className="small muted">
              Track shared with {plural(result.routes.length, 'route')}:{' '}
              <span className="mono">{result.routes.join(', ')}</span>
            </p>
          )}
          <ol className="path-stops">
            {result.stops.map((stop, index) => (
              <li key={`${stop.id}-${index}`}>
                <button
                  type="button"
                  className={`linkish ${isUnnamed(stop.name) ? 'is-unnamed' : ''}`}
                  onClick={() => onFocusStop(stop)}
                >
                  {stopLabel(stop)}
                </button>
              </li>
            ))}
          </ol>
        </div>
      )}
    </section>
  )
}
