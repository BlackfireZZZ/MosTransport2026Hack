import type {
  Edge,
  GraphGeoJSON,
  Health,
  PathResult,
  RouteSummary,
  Stats,
  Stop,
  StopDetail,
} from './types'

/**
 * Every call is relative. In production the backend mounts the Vite build at `/`
 * and answers `/api/*` itself; in development the Vite proxy forwards `/api` to
 * VITE_API_PROXY_TARGET (see vite.config.ts). No host is ever named here.
 */
const BASE = '/api'

export class ApiError extends Error {
  status: number

  constructor(message: string, status: number) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type Params = Record<string, string | number | undefined | null>

function url(path: string, params?: Params): string {
  const qs = new URLSearchParams()
  for (const [key, value] of Object.entries(params ?? {})) {
    if (value !== undefined && value !== null && value !== '') qs.set(key, String(value))
  }
  const query = qs.toString()
  return query ? `${BASE}${path}?${query}` : `${BASE}${path}`
}

async function get<T>(path: string, params?: Params, signal?: AbortSignal): Promise<T> {
  const response = await fetch(url(path, params), { signal, headers: { Accept: 'application/json' } })
  if (!response.ok) {
    // FastAPI puts the human-readable message in `detail`.
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = (await response.json()) as { detail?: string; error?: string }
      detail = body.detail ?? body.error ?? detail
    } catch {
      /* non-JSON error body; keep the status line */
    }
    throw new ApiError(detail, response.status)
  }
  return (await response.json()) as T
}

export const api = {
  health: (signal?: AbortSignal) => get<Health>('/health', undefined, signal),
  stats: (signal?: AbortSignal) => get<Stats>('/stats', undefined, signal),
  routes: (signal?: AbortSignal) => get<RouteSummary[]>('/routes', undefined, signal),

  /** Route refs are arbitrary strings ("А", "1а", "т1"), so they must be encoded. */
  stops: (q?: string, limit = 50, signal?: AbortSignal) =>
    get<Stop[]>('/stops', { q, limit }, signal),
  stop: (id: number, signal?: AbortSignal) =>
    get<StopDetail>(`/stops/${encodeURIComponent(id)}`, undefined, signal),
  edges: (route?: string, signal?: AbortSignal) => get<Edge[]>('/edges', { route }, signal),

  graph: (route?: string, signal?: AbortSignal) =>
    get<GraphGeoJSON>('/graph.geojson', { route }, signal),

  path: (from: number, to: number, signal?: AbortSignal) =>
    get<PathResult>('/path', { from, to }, signal),
}
