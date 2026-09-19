import type {
  ForecastHorizon,
  ForecastResponse,
  RouteSummary,
  ScenarioRequest,
  ScenarioResponse,
} from "@/features/forecast/types"

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
  ) {
    super(message)
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  })
  if (!response.ok) {
    throw new ApiError(`API request failed: ${response.status}`, response.status)
  }
  return (await response.json()) as T
}

export const api = {
  routes: () => request<RouteSummary[]>("/api/v1/routes"),
  forecast: (routeId: number, horizon: ForecastHorizon) =>
    request<ForecastResponse>(`/api/v1/forecasts?route_id=${routeId}&horizon=${horizon}`),
  evaluateScenario: (body: ScenarioRequest) =>
    request<ScenarioResponse>("/api/v1/scenarios/evaluate", {
      method: "POST",
      body: JSON.stringify(body),
    }),
}
