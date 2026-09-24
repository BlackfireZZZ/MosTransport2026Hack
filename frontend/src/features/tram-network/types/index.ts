import type { components } from "@/api/schema.generated"

type Schemas = components["schemas"]

export type GeoJsonMetadata = Schemas["GeoJsonMetadataResponse"]
export type NetworkComponent = Schemas["NetworkComponentResponse"]
export type NetworkStats = Schemas["NetworkStatsResponse"]
export type OverpassStatus = Schemas["OverpassStatusResponse"]
export type RouteDetail = Schemas["RouteDetailResponse"]
export type SegmentFeature = Schemas["SegmentFeature"]
export type StopDetail = Schemas["StopDetailResponse"]
export type StopFeature = Schemas["StopFeature"]
export type StopNeighbour = Schemas["StopNeighbourResponse"]
export type TramEdge = Schemas["TramEdgeResponse"]
export type TramGraphGeoJson = Schemas["TramGraphGeoJson"]
export type TramPath = Schemas["TramPathResponse"]
export type TramRoute = Schemas["TramRouteResponse"]
export type TramStop = Schemas["TramStopResponse"]

/** GeoJSON order: longitude first. The stop fields read the other way round. */
export type LngLat = readonly [number, number]

export interface StopRef {
  readonly id: number
  readonly name: string
  readonly latitude: number
  readonly longitude: number
}


export interface ForecastMarker {
  readonly stopId: number
  readonly longitude: number
  readonly latitude: number
  readonly value: number
  readonly label: string
  readonly selected: boolean
  readonly synthetic: boolean
}
