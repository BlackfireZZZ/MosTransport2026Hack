/** Shapes returned by the FastAPI backend in app/backend. */

import type { Feature, LineString, Point } from 'geojson'

export interface Stop {
  id: number
  name: string
  lat: number
  lon: number
  routes: string[]
}

export interface Neighbour {
  id: number
  name: string
  length_m: number
  routes: string[]
  /** The graph is directed: 'out' is a successor, 'in' a predecessor. */
  direction: 'in' | 'out'
}

export interface StopDetail extends Stop {
  neighbours: Neighbour[]
}

export interface RouteSummary {
  ref: string
  stop_count: number
  length_m: number
  /** Index of the undirected connected component; 0 is the main network. */
  component: number
}

export interface Edge {
  source: number
  target: number
  length_m: number
  routes: string[]
}

export interface Health {
  status: string
  graph: {
    stops: number
    edges: number
    generated_at: string | null
    osm_data_timestamp: string | null
  }
  overpass: {
    reachable: boolean
    url: string
    detail: string | null
  }
}

export interface Stats {
  stops: number
  edges: number
  routes: number
  route_relations: number | null
  total_length_km: number
  components: { size: number; routes: string[] }[]
  degree_histogram: Record<string, number>
  segment_length_m: { min: number; median: number; mean: number; max: number }
}

/**
 * `found: false` is a normal 200 answer, not an error -- the network is in two
 * disconnected pieces and a cross-component request genuinely has no path.
 */
export interface PathResult {
  found: boolean
  reason: string | null
  stops: Stop[]
  total_length_m: number
  /** [lon, lat] pairs following the real track, not stop-to-stop straight lines. */
  geometry: [number, number][]
  routes: string[]
}

export interface GraphMetadata {
  source?: string
  license?: string
  area?: string
  osm_data_timestamp?: string
  generated_at?: string
  stop_count?: number
  edge_count?: number
  routes_total?: number
  stops_missing_name?: number
  filtered_to_route?: string
}

export interface StopProperties {
  id: number
  name: string
  routes: string[]
}

export interface TrackProperties {
  source: number
  target: number
  length_m: number
  routes: string[]
}

export interface GraphGeoJSON {
  type: 'FeatureCollection'
  metadata?: GraphMetadata
  features: Feature<Point | LineString, StopProperties | TrackProperties>[]
}
