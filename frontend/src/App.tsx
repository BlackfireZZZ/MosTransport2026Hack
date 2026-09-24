import { Activity, Bell, Database, GitBranch, Map, Settings2, TramFront } from "lucide-react"
import { lazy, Suspense, useState } from "react"

import { ApiError } from "@/api/client"
import { Badge } from "@/components/ui/badge"
import { Button } from "@/components/ui/button"
import { Card, CardContent } from "@/components/ui/card"
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "@/components/ui/select"
import { Skeleton } from "@/components/ui/skeleton"
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { ProvenancePanel } from "@/features/forecast/components/provenance-panel"
import { dataKind } from "@/features/forecast/lib/provenance"
import { NetworkMap } from "@/features/forecast/components/network-map"
import { ScenarioPanel } from "@/features/forecast/components/scenario-panel"
import { useForecast, useRoutes, useRouteStops } from "@/features/forecast/hooks/use-forecast"
import type { ForecastHorizon } from "@/features/forecast/types"
import { bucketLabel, bucketScope, bucketStops, selectedBucket } from "@/features/forecast/lib/bucket"
import { toMoscowInput, validateWindow } from "@/features/forecast/lib/selection"
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
  const [bucketSelection, setBucketSelection] = useState<{ scope: string; timestamp: string } | null>(null)
  const [pollInterval, setPollInterval] = useState<number | false>(60_000)
  const [stopId, setStopId] = useState<number | null>(null)
  const [startInput, setStartInput] = useState("")
  const [endInput, setEndInput] = useState("")
  const routeStops = useRouteStops(selectedRouteId)
  const window = validateWindow(startInput, endInput, horizon)
  const validStop = stopId === null || Boolean(routeStops.data?.some((stop) => stop.id === stopId))
  const validSelection = !window.error && validStop
  const filters = { stop_id: stopId ?? undefined, start: window.start, end: window.end }
  const forecast = useForecast(selectedRouteId, horizon, filters, validSelection, pollInterval)
  const resetWindow = () => { setStartInput(""); setEndInput("") }
  const filtered = stopId !== null || Boolean(startInput || endInput)
  const data = validSelection ? forecast.data : undefined
  const timestamp = data ? selectedBucket(data, bucketSelection) : null
  const currentPoint = data?.points.find((point) => point.timestamp === timestamp)
  const currentStops = data ? bucketStops(data, timestamp) : []
  const selectTimestamp = (value: string) => { if (data) setBucketSelection({ scope: bucketScope(data), timestamp: value }) }
  const queryStatus = forecast.error instanceof ApiError ? forecast.error.status : null
  const selectionError = queryStatus === 404 ? "Нет прогноза для выбранных параметров" : queryStatus === 422 ? "Интервал недоступен" : queryStatus === 409 ? "Данные прогноза несовместимы" : null
  const busiestRow = currentStops.length ? currentStops.reduce((max, row) => row.predicted_passengers > max.predicted_passengers ? row : max) : undefined
  const busiestStop = data?.stops.find((stop) => stop.id === busiestRow?.stop_id)
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
          <span>{data ? dataKind(data) : forecast.isError ? "Прогноз недоступен" : "Ожидание данных"}<small>{data ? `сформирован ${generatedAt} МСК` : "качество модели не подтверждено"}</small></span>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div><p className="eyebrow">ДИСПЕТЧЕРСКИЙ ЦЕНТР</p><h1>{section === "network" ? "Граф трамвайной сети Москвы" : "Пассажиропоток трамвайной сети"}</h1></div>
          <div className="topbar-actions"><Badge>{section === "network" ? "Данные OpenStreetMap" : data ? dataKind(data) : "Нет данных"}</Badge><Button variant="ghost" size="icon" aria-label="Уведомления"><Bell /></Button></div>
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
              <Select value={selectedRouteId === null ? "" : String(selectedRouteId)} onValueChange={(value) => { setRouteId(Number(value)); setStopId(null); resetWindow() }}>
                <SelectTrigger id="route-select" disabled={!routes.data?.length}><SelectValue placeholder="Выберите маршрут" /></SelectTrigger>
                <SelectContent>
                  {routes.data?.map((route) => <SelectItem key={route.id} value={String(route.id)}>{route.number} · {route.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="filter-field horizon-field">
              <label>Горизонт планирования</label>
              <Tabs value={horizon} onValueChange={(value) => { setHorizon(value as ForecastHorizon); resetWindow() }}>
                <TabsList aria-label="Горизонт планирования">{horizons.map((item) => <TabsTrigger key={item.value} value={item.value}>{item.label}</TabsTrigger>)}</TabsList>
                {horizons.map((item) => (
                  <TabsContent key={item.value} value={item.value} className="sr-only">
                    Выбран горизонт: {item.label}
                  </TabsContent>
                ))}
              </Tabs>
            </div>
            <div className="filter-field">
              <label htmlFor="stop-select">Остановка</label>
              <Select value={stopId === null ? "all" : String(stopId)} onValueChange={(value) => setStopId(value === "all" ? null : Number(value))}>
                <SelectTrigger id="stop-select" disabled={!routeStops.data?.length}><SelectValue placeholder="Весь маршрут" /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">Весь маршрут</SelectItem>
                  {routeStops.data?.map((stop) => <SelectItem key={stop.id} value={String(stop.id)}>{stop.name}</SelectItem>)}
                </SelectContent>
              </Select>
              {routeStops.isLoading && <small role="status">Загрузка остановок…</small>}
              {routeStops.isError && <div role="alert">Список остановок недоступен. <Button variant="secondary" onClick={() => void routeStops.refetch()}>Повторить остановки</Button></div>}
            </div>
            <div className="filter-field">
              <label htmlFor="window-start">Начало · МСК</label>
              <input id="window-start" type="datetime-local" value={startInput} aria-describedby="window-help" aria-invalid={Boolean(window.error)} onChange={(event) => setStartInput(event.target.value)} />
            </div>
            <div className="filter-field">
              <label htmlFor="window-end">Конец (не включительно) · МСК</label>
              <input id="window-end" type="datetime-local" value={endInput} aria-describedby="window-help" aria-invalid={Boolean(window.error)} onChange={(event) => setEndInput(event.target.value)} />
            </div>
            <div className="filter-field"><label htmlFor="poll-interval">Автопроверка</label><select id="poll-interval" value={pollInterval === false ? "off" : String(pollInterval)} onChange={(event) => setPollInterval(event.target.value === "off" ? false : Number(event.target.value))}><option value="off">Вручную</option><option value="15000">Каждые 15 секунд</option><option value="60000">Каждую минуту</option><option value="300000">Каждые 5 минут</option></select></div>
            <div className="freshness"><span>Прогноз сформирован · МСК</span><strong>{generatedAt}</strong></div>
            <Button variant="secondary" disabled={selectedRouteId === null || !validSelection || forecast.isFetching} onClick={() => void forecast.refetch()}>Обновить прогноз</Button>
          </section>

          <div className="window-help" id="window-help">
            <p>{window.error ?? "Время Europe/Moscow. Пустые даты — опубликованный интервал целиком; конец не включается."}</p>
            {window.error && <span role="alert">Запрос не выполнен: исправьте интервал.</span>}
            {data?.selection && <p>Показано: {toMoscowInput(data.selection.start).replace("T", " ")} — {toMoscowInput(data.selection.end).replace("T", " ")} МСК (конец не включён).</p>}
            {!validStop && !routeStops.isLoading && <p role="alert">Остановка недоступна в текущем списке. Сбросьте выбор или повторите загрузку остановок.</p>}
            {filtered && <Button variant="secondary" onClick={() => { setStopId(null); resetWindow() }}>Сбросить остановку и интервал</Button>}
          </div>
          {(routes.isLoading || forecast.isLoading) && <DashboardSkeleton />}
          {routes.isError && (
            <Card className="error-state"><CardContent><h2>{routes.data ? "Список маршрутов не обновлён" : "Маршруты временно недоступны"}</h2><p>Повторите загрузку списка маршрутов.</p><Button onClick={() => void routes.refetch()}>Повторить загрузку маршрутов</Button></CardContent></Card>
          )}
          {forecast.isError && validSelection && selectedRouteId !== null && (
            <Card className="error-state"><CardContent><h2>{data ? "Показан сохранённый прогноз" : selectionError ?? "Прогноз временно недоступен"}</h2><p>{data ? `Не удалось обновить данные. Прогноз сформирован ${generatedAt} МСК; данные могут быть устаревшими.` : selectionError ? "Измените остановку или сократите интервал; можно сбросить фильтры." : "Проверьте соединение с API и повторите запрос."}</p><Button onClick={() => void forecast.refetch()}>Повторить прогноз</Button></CardContent></Card>
          )}
          {routes.data?.length === 0 && !routes.isLoading && (
            <Card className="error-state"><CardContent><h2>Маршруты не найдены</h2><p>Загрузите сетевой граф и опубликуйте прогноз.</p></CardContent></Card>
          )}
          {data && data.points.length === 0 && (
            <Card className="error-state"><CardContent><h2>Нет точек прогноза</h2><p>Для выбранной остановки и временного интервала нет значений. Измените или сбросьте фильтры.</p></CardContent></Card>
          )}
          {data && data.points.length > 0 && (
            <>
              <section className="kpi-grid" aria-label="Ключевые показатели">
                <article className="kpi"><span>Пиковый поток</span><strong>{formatPassengers(data.peak_passengers)}</strong><small>пассажиров / интервал</small></article>
                <article className="kpi"><span>Пиковая загрузка</span><strong className={(data.peak_load_percent ?? -1) >= 100 ? "is-critical" : ""}>{data.peak_load_percent == null ? "—" : `${data.peak_load_percent.toFixed(0)}%`}</strong><small>{data.peak_load_percent == null ? "вместимость неизвестна" : data.peak_load_percent >= 100 ? "выше вместимости" : "в пределах вместимости"}</small></article>
                <article className="kpi"><span>Напряжённый узел</span><strong className="kpi-text">{busiestStop?.name ?? "—"}</strong><small>{busiestRow ? `${formatPassengers(busiestRow.predicted_passengers)} в выбранном интервале` : "нет данных выбранного интервала"}</small></article>
                <article className="kpi"><span>{(reserve ?? 0) >= 0 ? "Резерв сети" : "Дефицит сети"}</span><strong className={(reserve ?? 0) < 0 ? "is-critical" : ""}>{reserve === null ? "—" : `${Math.abs(reserve).toFixed(0)}%`}</strong><small>{reserveLabel}</small></article>
              </section>

              <section className="bucket-selection" aria-label="Выбранный интервал прогноза">
                <div>
                  <label htmlFor="bucket-select">Интервал на графике и карте · МСК</label>
                  <select id="bucket-select" value={timestamp ?? ""} onChange={(event) => selectTimestamp(event.target.value)}>
                    {data.points.map((point) => <option key={point.timestamp} value={point.timestamp}>{bucketLabel(point.timestamp)}</option>)}
                  </select>
                  <div className="bucket-step-controls">
                    <Button variant="secondary" disabled={!timestamp || data.points[0].timestamp === timestamp} onClick={() => {
                      const index = data.points.findIndex((point) => point.timestamp === timestamp)
                      if (index > 0) selectTimestamp(data.points[index - 1].timestamp)
                    }}>Предыдущий интервал</Button>
                    <Button variant="secondary" disabled={!timestamp || data.points.at(-1)?.timestamp === timestamp} onClick={() => {
                      const index = data.points.findIndex((point) => point.timestamp === timestamp)
                      if (index >= 0 && index + 1 < data.points.length) selectTimestamp(data.points[index + 1].timestamp)
                    }}>Следующий интервал</Button>
                  </div>
                </div>
                <div aria-live="polite" data-testid="current-forecast-value"><span>Прогноз выбранного интервала</span><strong>{currentPoint ? formatPassengers(currentPoint.predicted_passengers) : "—"}</strong><span>{data.run?.unit ?? "единица не указана"}</span></div>
              </section>
              <Suspense fallback={<Skeleton className="h-[360px]" />}>
                <ForecastChart points={data.points} horizon={horizon} selectedTimestamp={timestamp} onSelectTimestamp={selectTimestamp} />
              </Suspense>
              <section className="lower-grid">
                <NetworkMap snapshot={data} timestamp={timestamp} selectedStopId={stopId} onStopSelect={setStopId} />
                <div id="scenario">{selectedRouteId !== null && !filtered && <ScenarioPanel key={`${selectedRouteId}-${horizon}`} routeId={selectedRouteId} horizon={horizon} />}{filtered && <p>Сценарный расчёт для выбранного среза недоступен.</p>}</div>
              </section>
              <div id="data"><ProvenancePanel forecast={data} updatedAt={forecast.dataUpdatedAt} failed={forecast.isRefetchError} fetching={forecast.isFetching} pollInterval={pollInterval} /></div>
              <footer className="data-note"><Map />{dataKind(data)} · качество модели на реальных данных не подтверждено · версия {data.model_version}</footer>
            </>
          )}
        </div>
      </main>
    </div>
  )
}

export default App
