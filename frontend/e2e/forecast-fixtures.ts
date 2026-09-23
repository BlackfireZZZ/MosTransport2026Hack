import type { ForecastHorizon, ForecastResponse, RouteSummary } from "../src/features/forecast/types"

export const routes: readonly RouteSummary[] = [
  { id: 1, number: "Т1", name: "Белорусский вокзал — Каланчёвская", color: "#d9342b" },
  { id: 2, number: "Т2", name: "Черёмушки — Университет", color: "#246b88" },
]

export function forecastResponse(routeId: number, horizon: ForecastHorizon): ForecastResponse {
  const route = routes.find((candidate) => candidate.id === routeId)
  if (!route) throw new Error(`Unknown fixture route: ${routeId}`)
  const targetPeak = route.id === 2 ? 820 : horizon === "month" ? 710 : horizon === "year" ? 760 : 600
  const count = horizon === "day" ? 24 : horizon === "month" ? 31 : 12
  const points = Array.from({ length: count }, (_, index) => {
    const date = horizon === "day"
      ? new Date(Date.UTC(2026, 9, 1, index - 3))
      : horizon === "month"
        ? new Date(Date.UTC(2026, 9, index + 1, -3))
        : new Date(Date.UTC(2026, index, 1, -3))
    const predicted = targetPeak - Math.abs(index - Math.floor(count / 2)) * 10
    return {
      timestamp: date.toISOString(), capacity: 1000, predicted_passengers: predicted,
      lower_bound: predicted - 80, upper_bound: predicted + 90,
    }
  })
  const peak = Math.max(...points.map((point) => point.predicted_passengers))
  return {
    generated_at: "2025-12-31T21:00:00Z", horizon, model_version: "demo-e2e-fixture-v1",
    peak_load_percent: Math.max(...points.map((point) => point.predicted_passengers / point.capacity * 100)),
    peak_passengers: peak, points, route,
    stops: [{ id: route.id * 10 + 1, latitude: 55.776, longitude: 37.583,
      name: "Тестовая остановка", sequence: 1, load_percent: peak / 10, predicted_passengers: peak }],
  }
}
