import type { components } from "@/api/schema.generated"

type Schemas = components["schemas"]

export type ForecastHorizon = Schemas["ForecastHorizon"]
export type ForecastPoint = Schemas["ForecastPointResponse"]
export type ForecastResponse = Schemas["ForecastResponse"]
export type RouteSummary = Schemas["RouteResponse"]
export type ScenarioRequest = Schemas["ScenarioRequest"]
export type ScenarioResponse = Schemas["ScenarioResponse"]
export type StopLoad = Schemas["StopLoadResponse"]

export type RouteStop = Schemas["RouteStopResponse"]

export type StopForecastPoint = Schemas["StopForecastPointResponse"]
export type ForecastMapPosition = Schemas["ForecastMapPositionResponse"]
