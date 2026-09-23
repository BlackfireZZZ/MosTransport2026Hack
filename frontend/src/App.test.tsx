import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"

import { api } from "@/api/client"
import App from "./App"
import { forecastResponse, routes } from "../e2e/forecast-fixtures"

vi.mock("@/api/client", () => ({ api: { routes: vi.fn(), forecast: vi.fn() } }))
vi.mock("@/features/forecast/components/forecast-chart", () => ({ ForecastChart: () => <p>Тестовый график</p> }))
vi.mock("@/features/forecast/components/scenario-panel", () => ({ ScenarioPanel: () => <p>Тестовый сценарий</p> }))
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
