import type { Health, Stats } from '../types'
import { formatNumber, formatTimestamp } from '../format'

interface Props {
  health: Health | null
  stats: Stats | null
  error: string | null
}

export function Provenance({ health, stats, error }: Props) {
  const components = stats?.components ?? []

  return (
    <section className="panel panel--provenance">
      <h2>Dataset</h2>

      {error && <p className="error">Backend unreachable: {error}</p>}

      <dl className="kv">
        <dt>OSM extract</dt>
        <dd>{formatTimestamp(health?.graph.osm_data_timestamp)}</dd>
        <dt>Graph built</dt>
        <dd>{formatTimestamp(health?.graph.generated_at)}</dd>
        {health && (
          <>
            <dt>Graph</dt>
            <dd>
              {formatNumber(health.graph.stops)} stops · {formatNumber(health.graph.edges)} directed
              edges
            </dd>
          </>
        )}
        {stats && (
          <>
            <dt>Track</dt>
            <dd>{stats.total_length_km.toFixed(1)} km</dd>
          </>
        )}
      </dl>

      {components.length > 1 && (
        <p className="notice notice--small">
          The network is in {components.length} disconnected pieces (
          {components.map((component) => formatNumber(component.size)).join(' and ')} stops). That
          is real geography, not a data fault: the northern section around
          Timiryazevskaya has no track linking it to the rest.
        </p>
      )}

      <p className="attrib">
        Data ©{' '}
        <a href="https://www.openstreetmap.org/copyright" target="_blank" rel="noreferrer">
          OpenStreetMap contributors
        </a>
        , ODbL 1.0. Basemap © CARTO.
      </p>
    </section>
  )
}
