import { useCallback, useEffect, useRef, useState } from 'react'
import { api, ApiError } from './api'
import type { GraphGeoJSON, Health, PathResult, RouteSummary, Stats, Stop, StopDetail } from './types'
import { MapCanvas } from './components/MapCanvas'
import { RoutePanel } from './components/RoutePanel'
import { StopSearch } from './components/StopSearch'
import { PathPanel } from './components/PathPanel'
import type { PickTarget } from './components/PathPanel'
import { StopInspector } from './components/StopInspector'
import { Provenance } from './components/Provenance'
import { TopBar } from './components/TopBar'

function describe(error: unknown): string {
  if (error instanceof ApiError) return error.message
  if (error instanceof Error) return error.message
  return String(error)
}

export default function App() {
  const [health, setHealth] = useState<Health | null>(null)
  const [healthError, setHealthError] = useState<string | null>(null)
  const [stats, setStats] = useState<Stats | null>(null)

  const [routes, setRoutes] = useState<RouteSummary[]>([])
  const [routesLoading, setRoutesLoading] = useState(true)
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)

  const [network, setNetwork] = useState<GraphGeoJSON | null>(null)
  const [networkError, setNetworkError] = useState<string | null>(null)
  const [routeGeo, setRouteGeo] = useState<GraphGeoJSON | null>(null)

  const [stopDetail, setStopDetail] = useState<StopDetail | null>(null)
  const [stopLoading, setStopLoading] = useState(false)
  const [stopError, setStopError] = useState<string | null>(null)

  const [fromStop, setFromStop] = useState<Stop | null>(null)
  const [toStop, setToStop] = useState<Stop | null>(null)
  const [pickTarget, setPickTarget] = useState<PickTarget>(null)

  const [path, setPath] = useState<PathResult | null>(null)
  const [pathBusy, setPathBusy] = useState(false)
  const [pathError, setPathError] = useState<string | null>(null)

  // Guards a slow stop request from overwriting the result of a newer click.
  const stopRequestRef = useRef(0)

  // --- initial load ----------------------------------------------------------

  useEffect(() => {
    const controller = new AbortController()

    api
      .health(controller.signal)
      .then((value) => {
        setHealth(value)
        setHealthError(null)
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setHealthError(describe(error))
      })

    api
      .stats(controller.signal)
      .then(setStats)
      .catch(() => {
        /* stats are decoration; /api/health already reports a dead backend */
      })

    api
      .routes(controller.signal)
      .then(setRoutes)
      .catch(() => setRoutes([]))
      .finally(() => {
        if (!controller.signal.aborted) setRoutesLoading(false)
      })

    api
      .graph(undefined, controller.signal)
      .then((value) => {
        setNetwork(value)
        setNetworkError(null)
      })
      .catch((error: unknown) => {
        if (!controller.signal.aborted) setNetworkError(describe(error))
      })

    return () => controller.abort()
  }, [])

  // --- route filter ----------------------------------------------------------

  useEffect(() => {
    if (!selectedRoute) {
      setRouteGeo(null)
      return undefined
    }
    const controller = new AbortController()
    // The backend does the filtering; refs are opaque strings and get URL-encoded.
    api
      .graph(selectedRoute, controller.signal)
      .then(setRouteGeo)
      .catch((error: unknown) => {
        if (!controller.signal.aborted) {
          setRouteGeo(null)
          setNetworkError(describe(error))
        }
      })
    return () => controller.abort()
  }, [selectedRoute])

  // --- stop selection --------------------------------------------------------

  const openStop = useCallback(
    async (id: number, assignTo: PickTarget = null) => {
      const token = ++stopRequestRef.current
      setStopLoading(true)
      setStopError(null)
      try {
        const detail = await api.stop(id)
        if (stopRequestRef.current !== token) return
        setStopDetail(detail)
        if (assignTo === 'from') setFromStop(detail)
        if (assignTo === 'to') setToStop(detail)
      } catch (error: unknown) {
        if (stopRequestRef.current !== token) return
        setStopDetail(null)
        setStopError(describe(error))
      } finally {
        if (stopRequestRef.current === token) setStopLoading(false)
      }
    },
    [],
  )

  const handleStopClick = useCallback(
    (id: number) => {
      const target = pickTarget
      setPickTarget(null)
      void openStop(id, target)
    },
    [pickTarget, openStop],
  )

  const handleSearchPick = useCallback(
    (stop: Stop) => {
      const target = pickTarget
      setPickTarget(null)
      if (target === 'from') setFromStop(stop)
      if (target === 'to') setToStop(stop)
      void openStop(stop.id)
    },
    [pickTarget, openStop],
  )

  // Changing an endpoint invalidates the drawn path rather than leaving a stale one.
  useEffect(() => {
    setPath(null)
    setPathError(null)
  }, [fromStop, toStop])

  const runPath = useCallback(async () => {
    if (!fromStop || !toStop) return
    setPathBusy(true)
    setPathError(null)
    try {
      const result = await api.path(fromStop.id, toStop.id)
      setPath(result)
    } catch (error: unknown) {
      // A genuine transport/500 failure. `found: false` arrives as a 200 and is
      // handled in PathPanel as an answer, not an error.
      setPathError(describe(error))
      setPath(null)
    } finally {
      setPathBusy(false)
    }
  }, [fromStop, toStop])

  const clearPath = useCallback(() => {
    setFromStop(null)
    setToStop(null)
    setPath(null)
    setPathError(null)
    setPickTarget(null)
  }, [])

  const swapEnds = useCallback(() => {
    // Worth having on a directed graph: A->B existing says nothing about B->A.
    const previousFrom = fromStop
    setFromStop(toStop)
    setToStop(previousFrom)
  }, [fromStop, toStop])

  const selectedStop: Stop | null = stopDetail

  return (
    <div className="app">
      <TopBar health={health} healthError={healthError} />

      <main>
        <aside className="sidebar">
          <RoutePanel
            routes={routes}
            selected={selectedRoute}
            loading={routesLoading}
            onSelect={setSelectedRoute}
          />
          <StopSearch onPick={handleSearchPick} />
          <PathPanel
            fromStop={fromStop}
            toStop={toStop}
            pickTarget={pickTarget}
            result={path}
            busy={pathBusy}
            error={pathError}
            onArm={setPickTarget}
            onSwap={swapEnds}
            onClear={clearPath}
            onRun={() => void runPath()}
            onFocusStop={(stop) => void openStop(stop.id)}
          />
          <Provenance health={health} stats={stats} error={healthError} />
        </aside>

        <div className="stage">
          <MapCanvas
            network={network}
            routeGeo={routeGeo}
            selectedRoute={selectedRoute}
            path={path}
            fromStop={fromStop}
            toStop={toStop}
            selectedStop={selectedStop}
            onStopClick={handleStopClick}
          />

          {!network && !networkError && (
            <div className="map-overlay">Loading the tram network…</div>
          )}
          {networkError && (
            <div className="map-overlay map-overlay--error">
              <strong>Could not load the network.</strong>
              <span>{networkError}</span>
              <span className="small muted">
                Start the backend (see the README) and reload.
              </span>
            </div>
          )}

          {pickTarget && (
            <div className="pick-hint">Click a stop on the map to set “{pickTarget}”</div>
          )}

          <StopInspector
            stop={stopDetail}
            loading={stopLoading}
            error={stopError}
            onClose={() => {
              setStopDetail(null)
              setStopError(null)
            }}
            onSetFrom={() => stopDetail && setFromStop(stopDetail)}
            onSetTo={() => stopDetail && setToStop(stopDetail)}
            onOpenNeighbour={(id) => void openStop(id)}
          />
        </div>
      </main>
    </div>
  )
}
