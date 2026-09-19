import { useMutation, useQuery } from "@tanstack/react-query"

import { api } from "@/api/client"
import type { ForecastHorizon, ScenarioRequest } from "@/features/forecast/types"

export function useRoutes() {
  return useQuery({ queryKey: ["routes"], queryFn: api.routes, staleTime: 5 * 60_000 })
}

export function useForecast(routeId: number, horizon: ForecastHorizon) {
  return useQuery({
    queryKey: ["forecast", routeId, horizon],
    queryFn: () => api.forecast(routeId, horizon),
    enabled: routeId > 0,
    refetchInterval: 60_000,
  })
}

export function useScenario() {
  return useMutation({ mutationFn: (request: ScenarioRequest) => api.evaluateScenario(request) })
}
