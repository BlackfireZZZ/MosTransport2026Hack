import AxeBuilder from "@axe-core/playwright"
import { expect, test, type Page, type Route } from "@playwright/test"

import type {
  ForecastHorizon,
  ForecastResponse,
  RouteSummary,
  ScenarioRequest,
  ScenarioResponse,
} from "../src/features/forecast/types"

const routes: readonly RouteSummary[] = [
  { id: 1, number: "Т1", name: "Белорусский вокзал — Каланчёвская", color: "#d9342b" },
  { id: 2, number: "Т2", name: "Черёмушки — Университет", color: "#246b88" },
]

function forecastResponse(routeId: number, horizon: ForecastHorizon): ForecastResponse {
  const route = routes.find((candidate) => candidate.id === routeId) ?? routes[0]
  const peak = route.id === 2 ? 820 : horizon === "month" ? 710 : horizon === "year" ? 760 : 600
  const timestamp = horizon === "day" ? "2026-09-19T06:00:00Z" : "2026-10-01T00:00:00Z"

  return {
    generated_at: "2026-09-19T06:00:00Z",
    horizon,
    model_version: "e2e-fixture-v1",
    peak_load_percent: peak / 10,
    peak_passengers: peak,
    points: [
      {
        capacity: 1_000,
        lower_bound: peak - 80,
        predicted_passengers: peak,
        timestamp,
        upper_bound: peak + 90,
      },
      {
        capacity: 1_000,
        lower_bound: peak - 40,
        predicted_passengers: peak + 20,
        timestamp: "2026-09-19T07:00:00Z",
        upper_bound: peak + 110,
      },
    ],
    route,
    stops: [
      {
        id: route.id * 10 + 1,
        latitude: 55.776,
        load_percent: peak / 10,
        longitude: 37.583,
        name: "Тестовая остановка",
        predicted_passengers: peak,
        sequence: 1,
      },
    ],
  }
}

function scenarioResponse(): ScenarioResponse {
  return {
    affected_stops: [],
    baseline_peak_load_percent: 80,
    capacity_delta: 16,
    passenger_delta: 120,
    scenario_peak_load_percent: 68,
    solver_version: "e2e-solver-v1",
  }
}

async function fulfillJson(route: Route, body: unknown, status = 200) {
  await route.fulfill({
    body: JSON.stringify(body),
    contentType: "application/json",
    status,
  })
}

async function mockDashboardApi(
  page: Page,
  options: {
    forecastHandler?: (route: Route) => Promise<void>
    scenarioRequests?: ScenarioRequest[]
  } = {},
) {
  await page.route("**/api/v1/routes", (route) => fulfillJson(route, routes))
  await page.route("**/api/v1/forecasts?*", async (route) => {
    if (options.forecastHandler) {
      await options.forecastHandler(route)
      return
    }
    const url = new URL(route.request().url())
    const routeId = Number(url.searchParams.get("route_id"))
    const horizon = (url.searchParams.get("horizon") ?? "day") as ForecastHorizon
    await fulfillJson(route, forecastResponse(routeId, horizon))
  })
  await page.route("**/api/v1/scenarios/evaluate", async (route) => {
    options.scenarioRequests?.push(route.request().postDataJSON() as ScenarioRequest)
    await fulfillJson(route, scenarioResponse())
  })
}

test("loads the dashboard and refreshes forecast by route and horizon", async ({ page }) => {
  await mockDashboardApi(page)
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "Пассажиропоток трамвайной сети" })).toBeVisible()
  await expect(page.getByRole("heading", { name: "Почасовой прогноз" })).toBeVisible()
  await expect(page.locator("article.kpi", { hasText: "Пиковый поток" })).toContainText("600")

  const routeSelect = page.getByRole("combobox", { name: "Маршрут" })
  await routeSelect.focus()
  await page.keyboard.press("Enter")
  const secondRoute = page.getByRole("option", { name: /Т2/ })
  await expect(secondRoute).toBeVisible()
  await secondRoute.press("Enter")
  await expect(routeSelect).toContainText("Т2")
  await expect(page.locator("article.kpi", { hasText: "Пиковый поток" })).toContainText("820")

  await page.getByRole("tab", { name: "1 день" }).focus()
  await page.keyboard.press("ArrowRight")
  await expect(page.getByRole("tab", { name: "1 месяц" })).toHaveAttribute("aria-selected", "true")
  await expect(page.getByRole("heading", { name: "Прогноз по дням" })).toBeVisible()

  const accessibility = await new AxeBuilder({ page }).analyze()
  expect(accessibility.violations).toEqual([])
})

test("submits a what-if scenario and clears stale output when context changes", async ({ page }) => {
  const scenarioRequests: ScenarioRequest[] = []
  await mockDashboardApi(page, { scenarioRequests })
  await page.goto("/")

  await page.getByRole("slider", { name: /Дополнительные трамваи/ }).fill("4")
  await page.getByRole("button", { name: "Рассчитать сценарий" }).click()

  await expect(page.getByTestId("scenario-result")).toContainText("80%")
  await expect(page.getByTestId("scenario-result")).toContainText("68%")
  expect(scenarioRequests).toEqual([
    expect.objectContaining({ additional_vehicles: 4, horizon: "day", route_id: 1 }),
  ])

  await page.getByRole("tab", { name: "1 год" }).click()
  await expect(page.getByTestId("scenario-result")).toHaveCount(0)
})

test("shows an API error and recovers through retry", async ({ page }) => {
  let attempts = 0
  await mockDashboardApi(page, {
    forecastHandler: async (route) => {
      attempts += 1
      if (attempts <= 2) {
        await fulfillJson(route, { detail: "temporary outage" }, 503)
        return
      }
      await fulfillJson(route, forecastResponse(1, "day"))
    },
  })
  await page.goto("/")

  await expect(page.getByRole("heading", { name: "Прогноз временно недоступен" })).toBeVisible()
  await page.getByRole("button", { name: "Повторить" }).click()
  await expect(page.getByRole("heading", { name: "Почасовой прогноз" })).toBeVisible()
  expect(attempts).toBeGreaterThanOrEqual(3)
})
