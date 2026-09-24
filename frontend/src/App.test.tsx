import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, beforeEach, expect, it, vi } from "vitest"

import { ApiError, api } from "@/api/client"
import App from "./App"
import { forecastResponse, routes } from "../e2e/forecast-fixtures"

vi.mock("@/api/client", () => ({ ApiError: class extends Error { status: number; constructor(message: string, status: number) { super(message); this.status = status } }, api: { routes: vi.fn(), routeStops: vi.fn(), forecast: vi.fn() } }))
vi.mock("@/features/forecast/components/forecast-chart", () => ({ ForecastChart: () => <p>Тестовый график</p> }))
vi.mock("@/features/forecast/components/scenario-panel", () => ({ ScenarioPanel: () => <p>Тестовый сценарий</p> }))
beforeEach(() => { vi.mocked(api.routeStops).mockResolvedValue([]) })
afterEach(() => { cleanup(); vi.resetAllMocks() })
function mount() {
  const client = new QueryClient({ defaultOptions: { queries: { retry: false, gcTime: 0 } } })
  render(<QueryClientProvider client={client}><App /></QueryClientProvider>)
  return client
}

it("shows waiting then a scoped route error without requesting forecasts", async () => {
  let reject!: (error: Error) => void
  vi.mocked(api.routes).mockImplementationOnce(() => new Promise((_resolve, fail) => { reject = fail }))
  mount()
  expect(screen.getByText("Ожидание демоданных")).toBeInTheDocument()
  expect(screen.getByRole("combobox", { name: "Маршрут" })).toBeDisabled()
  expect(api.forecast).not.toHaveBeenCalled()
  await act(async () => { reject(new Error("offline")); await Promise.resolve() })
  await screen.findByText("Маршруты временно недоступны")
  expect(api.forecast).not.toHaveBeenCalled()
  vi.mocked(api.routes).mockResolvedValueOnce([])
  fireEvent.click(screen.getByRole("button", { name: "Повторить загрузку маршрутов" }))
  await screen.findByText("Маршруты не найдены")
  expect(api.forecast).not.toHaveBeenCalled()
  expect(screen.queryByText("Модель доступна")).not.toBeInTheDocument()
})

it("distinguishes initial failure from retained demo data and recovers", async () => {
  vi.mocked(api.routes).mockResolvedValue([...routes])
  vi.mocked(api.forecast).mockRejectedValueOnce(new Error("offline"))
  mount()
  await screen.findByText("Прогноз временно недоступен")
  expect(screen.queryByRole("region", { name: "Ключевые показатели" })).not.toBeInTheDocument()
  vi.mocked(api.forecast).mockResolvedValueOnce(forecastResponse(1, "day"))
  fireEvent.click(screen.getByRole("button", { name: "Повторить прогноз" }))
  await screen.findByText("Тестовый график")
  expect(screen.getByText(/Синтетические демоданные/)).toBeInTheDocument()
  expect(screen.getByText("Прогноз сформирован · МСК")).toBeInTheDocument()
  vi.mocked(api.forecast).mockRejectedValueOnce(new Error("offline"))
  fireEvent.click(screen.getByRole("button", { name: "Обновить прогноз" }))
  await screen.findByText("Показан сохранённый демопрогноз")
  expect(screen.getByText("Тестовый график")).toBeInTheDocument()
  expect(screen.getByRole("region", { name: "Ключевые показатели" })).toHaveTextContent("600")
  vi.mocked(api.forecast).mockResolvedValueOnce(forecastResponse(1, "day"))
  fireEvent.click(screen.getByRole("button", { name: "Повторить прогноз" }))
  await waitFor(() => expect(screen.queryByText("Показан сохранённый демопрогноз")).not.toBeInTheDocument())
})

it("shows unknown capacity without inventing a zero percentage", async () => {
  vi.mocked(api.routes).mockResolvedValue([...routes])
  const response = forecastResponse(1, "day")
  vi.mocked(api.forecast).mockResolvedValue({ ...response, peak_load_percent: null,
    points: response.points.map((point) => ({ ...point, capacity: null, lower_bound: null, upper_bound: null })),
    stops: response.stops.map((stop) => ({ ...stop, load_percent: null })),
  })
  mount()
  await screen.findByText("Тестовый график")
  const kpis = screen.getByRole("region", { name: "Ключевые показатели" })
  expect(kpis).toHaveTextContent("вместимость неизвестна")
  expect(kpis).not.toHaveTextContent("0%")
  expect(kpis).not.toHaveTextContent("в пределах вместимости")
})


it.each([[404, "Нет прогноза для выбранных параметров"], [422, "Интервал недоступен"], [409, "Данные прогноза несовместимы"]] as const)("explains selection error %i and hides retry on invalid draft", async (status, heading) => {
  vi.mocked(api.routes).mockResolvedValue([...routes])
  vi.mocked(api.forecast).mockRejectedValue(new ApiError("selection", status))
  mount()
  await screen.findByRole("heading", { name: heading })
  fireEvent.change(screen.getByLabelText("Начало · МСК"), { target: { value: "2026-10-01T00:00" } })
  expect(screen.queryByRole("button", { name: "Повторить прогноз" })).not.toBeInTheDocument()
  expect(screen.getByText("Запрос не выполнен: исправьте интервал.")).toBeInTheDocument()
})

it("recovers the stop catalog without losing the route forecast", async () => {
  vi.mocked(api.routes).mockResolvedValue([...routes])
  vi.mocked(api.forecast).mockResolvedValue(forecastResponse(1, "day"))
  vi.mocked(api.routeStops).mockRejectedValueOnce(new Error("offline"))
  mount()
  await screen.findByRole("button", { name: "Повторить остановки" })
  expect(screen.getByRole("combobox", { name: "Остановка" })).toBeDisabled()
  await screen.findByText("Тестовый график")
  vi.mocked(api.routeStops).mockResolvedValueOnce([...forecastResponse(1, "day").stops])
  fireEvent.click(screen.getByRole("button", { name: "Повторить остановки" }))
  await waitFor(() => expect(screen.getByRole("combobox", { name: "Остановка" })).not.toBeDisabled())
  expect(screen.getByText("Тестовый график")).toBeInTheDocument()
})
