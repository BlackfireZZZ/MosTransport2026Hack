import { useCallback, useState } from "react"

import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Skeleton } from "@/components/ui/skeleton"
import {
  useNetworkGeoJson,
  useNetworkStats,
  useOverpassStatus,
  useRouteGeoJson,
  useStopDetail,
  useTramPath,
  useTramRoutes,
} from "@/features/tram-network/hooks/use-tram-network"
import { componentLabel, formatCount, formatKm } from "@/features/tram-network/lib/network"
import type { StopRef } from "@/features/tram-network/types"

import { NetworkProvenance } from "./network-provenance"
import { NetworkStats } from "./network-stats"
import { PathPanel } from "./path-panel"
import { RouteFilter } from "./route-filter"
import { StopInspector } from "./stop-inspector"
import { TramMap } from "./tram-map"

function toStopRef(stop: StopRef): StopRef {
  return { id: stop.id, name: stop.name, latitude: stop.latitude, longitude: stop.longitude }
}

export function TramNetworkView() {
  const [selectedRoute, setSelectedRoute] = useState<string | null>(null)
  const [selectedStopId, setSelectedStopId] = useState<number | null>(null)
  const [fromStop, setFromStop] = useState<StopRef | null>(null)
  const [toStop, setToStop] = useState<StopRef | null>(null)

  const stats = useNetworkStats()
  const routes = useTramRoutes()
  const network = useNetworkGeoJson()
  const routeGeoJson = useRouteGeoJson(selectedRoute)
  const selectedStop = useStopDetail(selectedStopId)
  const overpass = useOverpassStatus()
  const path = useTramPath(fromStop?.id ?? null, toStop?.id ?? null)

  const handleStopClick = useCallback((stopId: number) => setSelectedStopId(stopId), [])

  const handleSetEndpoint = useCallback((stop: StopRef, role: "from" | "to") => {
    if (role === "from") setFromStop(toStopRef(stop))
    else setToStop(toStopRef(stop))
  }, [])

  const swapEndpoints = useCallback(() => {
    setFromStop(toStop)
    setToStop(fromStop)
  }, [fromStop, toStop])

  const clearEndpoints = useCallback(() => {
    setFromStop(null)
    setToStop(null)
  }, [])

  const activeRoute = routes.data?.find((route) => route.ref === selectedRoute)
  const metadata = (routeGeoJson.data ?? network.data)?.metadata

  return (
    <div className="workspace" id="network">
      <section className="filters tram-filters" aria-label="Фильтры графа сети">
        {routes.isPending && <Skeleton className="h-16 w-[280px]" />}
        {routes.data && (
          <RouteFilter routes={routes.data} value={selectedRoute} onChange={setSelectedRoute} />
        )}
        <div className="freshness">
          <span>Выбрано</span>
          <strong>
            {activeRoute
              ? `${activeRoute.ref} · ${formatCount(activeRoute.stop_count)} ост. · ${formatKm(activeRoute.length_m)} · ${componentLabel(activeRoute.component)}`
              : "вся сеть"}
          </strong>
        </div>
        {selectedRoute !== null && (
          <Button variant="ghost" onClick={() => setSelectedRoute(null)}>
            Показать всю сеть
          </Button>
        )}
      </section>

      {stats.isPending && (
        <div className="kpi-grid">
          {Array.from({ length: 5 }).map((_, index) => (
            <Skeleton key={index} className="h-28" />
          ))}
        </div>
      )}
      {stats.data && <NetworkStats stats={stats.data} />}

      {(network.isError || routes.isError || stats.isError) && (
        <Card className="error-state">
          <CardContent>
            <h2>Граф сети недоступен</h2>
            <p>Проверьте соединение с API и повторите запрос.</p>
            <Button
              onClick={() => {
                void network.refetch()
                void routes.refetch()
                void stats.refetch()
              }}
            >
              Повторить
            </Button>
          </CardContent>
        </Card>
      )}

      {!network.isError && (
        <div className="tram-grid">
          <Card className="tram-map-card">
            <CardContent>
              <TramMap
                network={network.data}
                routeGeoJson={selectedRoute === null ? undefined : routeGeoJson.data}
                selectedRoute={selectedRoute}
                path={path.data}
                fromStop={fromStop}
                toStop={toStop}
                selectedStop={selectedStop.data ?? null}
                onStopClick={handleStopClick}
              />
              <div className="tram-legend">
                <span className="legend-swatch legend-track" />
                Пути сети
                <span className="legend-swatch legend-route" />
                Выбранный маршрут
                <span className="legend-swatch legend-path" />
                Кратчайший путь
                <span className="legend-swatch legend-from" />
                Откуда
                <span className="legend-swatch legend-to" />
                Куда
              </div>
              <p className="tram-map-status" role="status">
                {network.isPending
                  ? "Загружаем граф сети…"
                  : `${formatCount(network.data?.features.length ?? 0)} объектов на карте`}
              </p>
            </CardContent>
          </Card>

          <div className="tram-side">
            <StopInspector
              stopId={selectedStopId}
              onSelect={handleStopClick}
              onSetEndpoint={handleSetEndpoint}
            />
            <PathPanel
              fromStop={fromStop}
              toStop={toStop}
              path={path.data}
              isPending={path.isPending && path.fetchStatus !== "idle"}
              isError={path.isError}
              onSwap={swapEndpoints}
              onClear={clearEndpoints}
              onRetry={() => void path.refetch()}
            />
          </div>
        </div>
      )}

      <NetworkProvenance metadata={metadata} overpass={overpass.data} />
    </div>
  )
}
