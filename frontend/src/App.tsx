import { Activity, Bell, Database, GitBranch, Map, Settings2, TramFront } from "lucide-react"
import { lazy, Suspense, useState } from "react"

import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { NetworkMap } from "@/features/forecast/components/network-map"
import { ScenarioPanel } from "@/features/forecast/components/scenario-panel"
import { useForecast, useRoutes } from "@/features/forecast/hooks/use-forecast"
import type { ForecastHorizon } from "@/features/forecast/types"
import { formatPassengers } from "@/lib/utils"

const horizons: Array<{ value: ForecastHorizon; label: string }> = [
  { value: "day", label: "1 день" },
  { value: "month", label: "1 месяц" },
  { value: "year", label: "1 год" },
]

const ForecastChart = lazy(() =>
  import("@/features/forecast/components/forecast-chart").then((module) => ({
    default: module.ForecastChart,
  })),
)

const TramNetworkView = lazy(() =>
  import("@/features/tram-network/components/tram-network-view").then((module) => ({
    default: module.TramNetworkView,
  })),
)

type Section = "forecast" | "network" | "scenario" | "data"

const sections: ReadonlyArray<{
  id: Section
  label: string
  icon: typeof Activity
  anchor?: string
}> = [
  { id: "forecast", label: "Прогноз", icon: Activity, anchor: "forecast" },
  { id: "network", label: "Граф сети", icon: GitBranch },
  { id: "scenario", label: "Сценарии", icon: Settings2, anchor: "scenario" },
  { id: "data", label: "Данные", icon: Database, anchor: "data" },
]

function DashboardSkeleton() {
  return (
    <div className="dashboard-skeleton" aria-label="Загрузка прогноза">
      <div className="kpi-grid">{Array.from({ length: 4 }).map((_, index) => <Skeleton key={index} className="h-28" />)}</div>
      <Skeleton className="h-[360px]" />
      <div className="lower-grid"><Skeleton className="h-[420px]" /><Skeleton className="h-[420px]" /></div>
    </div>
  )
}

function App() {
  const routes = useRoutes()
  const [section, setSection] = useState<Section>("forecast")
  const [routeId, setRouteId] = useState<number | null>(null)
  const [horizon, setHorizon] = useState<ForecastHorizon>("day")
  const selectedRouteId = routeId === null
    ? (routes.data?.[0]?.id ?? null)
    : routes.data?.some((route) => route.id === routeId) ? routeId : null
  const forecast = useForecast(selectedRouteId, horizon)

  const data = forecast.data
  const busiestStop = data?.stops.length
    ? data.stops.reduce((max, stop) => (stop.load_percent ?? -1) > (max.load_percent ?? -1) ? stop : max)
    : undefined
  const reserve = data?.peak_load_percent == null ? null : 100 - data.peak_load_percent
  const reserveLabel = reserve === null ? "вместимость неизвестна" : reserve >= 0 ? "до расчётной вместимости" : "дефицит вместимости"
  const generatedAt = data
    ? new Intl.DateTimeFormat("ru-RU", { day: "2-digit", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", timeZone: "Europe/Moscow" }).format(new Date(data.generated_at))
    : "—"

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand"><span className="brand-mark"><TramFront /></span><span><b>TramFlow</b><small>ЕДЦ · Москва</small></span></div>
        <nav aria-label="Основная навигация">
          {sections.map((item) => (
            <button
              key={item.id}
              type="button"
              className={section === item.id ? "active" : undefined}
              aria-current={section === item.id ? "page" : undefined}
              onClick={() => {
                setSection(item.id)
                const anchor = item.anchor
                if (anchor) {
                  requestAnimationFrame(() =>
                    document.getElementById(anchor)?.scrollIntoView({ block: "start" }),
                  )
                }
              }}
            >
              <item.icon />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-foot">
          {data && <span className="status-dot" aria-hidden="true" />}
          <span>{data ? "Демонстрационный прогноз" : forecast.isError ? "Демопрогноз недоступен" : "Ожидание демоданных"}<small>{data ? `сформирован ${generatedAt} МСК` : "качество модели не подтверждено"}</small></span>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div><p className="eyebrow">ДИСПЕТЧЕРСКИЙ ЦЕНТР</p><h1>{section === "network" ? "Граф трамвайной сети Москвы" : "Пассажиропоток трамвайной сети"}</h1></div>
          <div className="topbar-actions"><Badge>{section === "network" ? "Данные OpenStreetMap" : "Демо-данные"}</Badge><Button variant="ghost" size="icon" aria-label="Уведомления"><Bell /></Button></div>
        </header>

        {section === "network" && (
          <Suspense fallback={<div className="workspace"><Skeleton className="h-[640px]" /></div>}>
            <TramNetworkView />
          </Suspense>
        )}

        <div className="workspace" id="forecast" hidden={section === "network"}>
          <section className="filters" aria-label="Параметры прогноза">
            <div className="filter-field">
              <label htmlFor="route-select">Маршрут</label>
              <Select value={selectedRouteId === null ? "" : String(selectedRouteId)} onValueChange={(value) => setRouteId(Number(value))}>
                <SelectTrigger id="route-select" disabled={!routes.data?.length}><SelectValue placeholder="Выберите маршрут" /></SelectTrigger>
                <SelectContent>
                  {routes.data?.map((route) => <SelectItem key={route.id} value={String(route.id)}>{route.number} · {route.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="filter-field horizon-field">
              <label>Горизонт планирования</label>
              <Tabs value={horizon} onValueChange={(value) => setHorizon(value as ForecastHorizon)}>
                <TabsList aria-label="Горизонт планирования">{horizons.map((item) => <TabsTrigger key={item.value} value={item.value}>{item.label}</TabsTrigger>)}</TabsList>
                {horizons.map((item) => (
                  <TabsContent key={item.value} value={item.value} className="sr-only">
                    Выбран горизонт: {item.label}
                  </TabsContent>
                ))}
              </Tabs>
            </div>
            <div className="freshness"><span>Прогноз сформирован · МСК</span><strong>{generatedAt}</strong></div>
            <Button variant="secondary" disabled={selectedRouteId === null || forecast.isFetching} onClick={() => void forecast.refetch()}>Обновить прогноз</Button>
          </section>

          {(routes.isLoading || forecast.isLoading) && <DashboardSkeleton />}
          {routes.isError && (
            <Card className="error-state"><CardContent><h2>{routes.data ? "Список маршрутов не обновлён" : "Маршруты временно недоступны"}</h2><p>Повторите загрузку списка маршрутов.</p><Button onClick={() => void routes.refetch()}>Повторить загрузку маршрутов</Button></CardContent></Card>
          )}
          {forecast.isError && selectedRouteId !== null && (
            <Card className="error-state"><CardContent><h2>{data ? "Показан сохранённый демопрогноз" : "Прогноз временно недоступен"}</h2><p>{data ? `Не удалось обновить данные. Прогноз сформирован ${generatedAt} МСК; данные могут быть устаревшими.` : "Проверьте соединение с API и повторите запрос."}</p><Button onClick={() => void forecast.refetch()}>Повторить прогноз</Button></CardContent></Card>
          )}
          {routes.data?.length === 0 && !routes.isLoading && (
            <Card className="error-state"><CardContent><h2>Маршруты не найдены</h2><p>Загрузите сетевой граф и опубликуйте прогноз.</p></CardContent></Card>
          )}
          {data && data.points.length === 0 && (
            <Card className="error-state"><CardContent><h2>Нет точек прогноза</h2><p>Для выбранного маршрута и горизонта опубликованный срез пуст.</p></CardContent></Card>
          )}
          {data && data.points.length > 0 && (
            <>
              <section className="kpi-grid" aria-label="Ключевые показатели">
                <article className="kpi"><span>Пиковый поток</span><strong>{formatPassengers(data.peak_passengers)}</strong><small>пассажиров / интервал</small></article>
                <article className="kpi"><span>Пиковая загрузка</span><strong className={(data.peak_load_percent ?? -1) >= 100 ? "is-critical" : ""}>{data.peak_load_percent == null ? "—" : `${data.peak_load_percent.toFixed(0)}%`}</strong><small>{data.peak_load_percent == null ? "вместимость неизвестна" : data.peak_load_percent >= 100 ? "выше вместимости" : "в пределах вместимости"}</small></article>
                <article className="kpi"><span>Напряжённый узел</span><strong className="kpi-text">{busiestStop?.name ?? "—"}</strong><small>{busiestStop?.load_percent != null ? `${busiestStop.load_percent.toFixed(0)}% загрузки` : "нет данных"}</small></article>
                <article className="kpi"><span>{(reserve ?? 0) >= 0 ? "Резерв сети" : "Дефицит сети"}</span><strong className={(reserve ?? 0) < 0 ? "is-critical" : ""}>{reserve === null ? "—" : `${Math.abs(reserve).toFixed(0)}%`}</strong><small>{reserveLabel}</small></article>
              </section>

              <Suspense fallback={<Skeleton className="h-[360px]" />}>
                <ForecastChart points={data.points} horizon={horizon} />
              </Suspense>
              <section className="lower-grid">
                <NetworkMap stops={data.stops} />
                <div id="scenario">{selectedRouteId !== null && <ScenarioPanel key={`${selectedRouteId}-${horizon}`} routeId={selectedRouteId} horizon={horizon} />}</div>
              </section>
              <footer className="data-note" id="data"><Map />Синтетические демоданные · качество модели на реальных данных не подтверждено · версия {data.model_version}</footer>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
