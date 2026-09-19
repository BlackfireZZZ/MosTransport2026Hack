import type { Health } from '../types'

interface Props {
  health: Health | null
  healthError: string | null
}

export function TopBar({ health, healthError }: Props) {
  let tone = 'unknown'
  let text = 'checking /api/health…'

  if (healthError) {
    tone = 'bad'
    text = 'backend unreachable'
  } else if (health) {
    // A dead Overpass passthrough does not stop the graph being served, so it is a
    // warning rather than a failure.
    tone = health.overpass.reachable ? 'ok' : 'warn'
    text = health.overpass.reachable ? 'backend ok · overpass ok' : 'backend ok · overpass down'
  }

  return (
    <header className="topbar">
      <div className="brand">
        <span className="brand-mark" aria-hidden="true" />
        <h1>Moscow tram network</h1>
      </div>
      <div className="health" title={healthError ?? health?.overpass.detail ?? ''}>
        <span className={`dot dot--${tone}`} aria-hidden="true" />
        <span>{text}</span>
      </div>
    </header>
  )
}
