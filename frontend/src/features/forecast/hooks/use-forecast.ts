import { skipToken, useMutation, useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { ForecastHorizon, ScenarioRequest } from "@/features/forecast/types"

export function useRoutes() {
  return useQuery({ queryKey: ["routes"], queryFn: api.routes, staleTime: 5 * 60_000 })
}

export function useForecast(routeId: number | null, horizon: ForecastHorizon) {
  return useQuery({
    queryKey: ["forecast", routeId, horizon],
    queryFn: routeId !== null && Number.isInteger(routeId) && routeId > 0
      ? () => api.forecast(routeId, horizon)
      : skipToken,
    refetchInterval: 60_000,
  })
}

export function useScenario() {
  return useMutation({ mutationFn: (request: ScenarioRequest) => api.evaluateScenario(request) })
}
