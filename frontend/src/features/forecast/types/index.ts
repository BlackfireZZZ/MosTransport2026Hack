export type ForecastHorizon = "day" | "month" | "year"

export interface RouteSummary {
  id: number
  number: string
  name: string
  color: string
}

export interface ForecastPoint {
  timestamp: string
  predicted_passengers: number
  lower_bound: number
  upper_bound: number
  capacity: number
}

export interface StopLoad {
  id: number
  name: string
  latitude: number
  longitude: number
  predicted_passengers: number
  load_percent: number
  sequence: number
}

export interface ForecastResponse {
  route: RouteSummary
  horizon: ForecastHorizon
  generated_at: string
  model_version: string
  peak_passengers: number
  peak_load_percent: number
  points: ForecastPoint[]
  stops: StopLoad[]
}

export interface ScenarioRequest {
  route_id: number
  horizon: ForecastHorizon
  additional_vehicles: number
  interval_change_percent: number
  demand_change_percent: number
}

export interface ScenarioResponse {
  baseline_peak_load_percent: number
  scenario_peak_load_percent: number
  passenger_delta: number
  capacity_delta: number
  affected_stops: StopLoad[]
  solver_version: string
}
