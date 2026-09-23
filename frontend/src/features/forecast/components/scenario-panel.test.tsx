import { QueryClient, QueryClientProvider } from "@tanstack/react-query"
import { act, cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react"
import { afterEach, expect, it, vi } from "vitest"

import { api } from "@/api/client"
import type { ScenarioResponse } from "@/features/forecast/types"
import { ScenarioPanel } from "./scenario-panel"

vi.mock("@/api/client", () => ({ api: { evaluateScenario: vi.fn() } }))
afterEach(() => { cleanup(); vi.resetAllMocks() })
const response: ScenarioResponse = { affected_stops: [], baseline_peak_load_percent: 80, scenario_peak_load_percent: 68, capacity_delta: 16, passenger_delta: 120, solver_version: "demo" }
function mount() {
  const client = new QueryClient({ defaultOptions: { mutations: { retry: false } } })
  render(<QueryClientProvider client={client}><ScenarioPanel routeId={1} horizon="day" /></QueryClientProvider>)
}

it("invalidates submitted output on any input edit", async () => {
  vi.mocked(api.evaluateScenario).mockResolvedValue(response)
  mount()
  for (const name of [/Дополнительные трамваи/, /Изменение интервала/, /Импульс спроса/]) {
    fireEvent.click(screen.getByRole("button", { name: "Рассчитать сценарий" }))
    await screen.findByTestId("scenario-result")
    fireEvent.change(screen.getByRole("slider", { name }), { target: { value: "5" } })
    expect(screen.queryByTestId("scenario-result")).not.toBeInTheDocument()
  }
})

it.each(["reset", "edit"])("detaches a pending result after %s", async (action) => {
  let resolve!: (value: ScenarioResponse) => void
  vi.mocked(api.evaluateScenario).mockImplementationOnce(() => new Promise((done) => { resolve = done }))
  mount()
  fireEvent.click(screen.getByRole("button", { name: "Рассчитать сценарий" }))
  await waitFor(() => expect(api.evaluateScenario).toHaveBeenCalledTimes(1))
  if (action === "reset") fireEvent.click(screen.getByRole("button", { name: "Сбросить сценарий" }))
  else fireEvent.change(screen.getByRole("slider", { name: /Дополнительные трамваи/ }), { target: { value: "5" } })
  vi.mocked(api.evaluateScenario).mockResolvedValueOnce({ ...response, scenario_peak_load_percent: 42 })
  fireEvent.click(screen.getByRole("button", { name: "Рассчитать сценарий" }))
  await screen.findByTestId("scenario-result")
  await act(async () => { resolve(response); await Promise.resolve() })
  expect(screen.getByTestId("scenario-result")).toHaveTextContent("42%")
  expect(screen.getByTestId("scenario-result")).not.toHaveTextContent("68%")
})

it("shows a failure and retries the current parameters", async () => {
  vi.mocked(api.evaluateScenario).mockRejectedValueOnce(new Error("offline")).mockResolvedValueOnce(response)
  mount()
  fireEvent.click(screen.getByRole("button", { name: "Рассчитать сценарий" }))
  await screen.findByText("Не удалось рассчитать сценарий. Повторите запрос.")
  fireEvent.click(screen.getByRole("button", { name: "Рассчитать сценарий" }))
  await screen.findByTestId("scenario-result")
  expect(screen.queryByText("Не удалось рассчитать сценарий. Повторите запрос.")).not.toBeInTheDocument()
})
