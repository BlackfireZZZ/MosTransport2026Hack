from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import TramNetworkServiceDep
from app.schemas.tram_graph import (
    NetworkStatsResponse,
    RouteDetailResponse,
    StopDetailResponse,
    TramEdgeResponse,
    TramGraphGeoJson,
    TramPathResponse,
    TramRouteResponse,
    TramStopResponse,
)

# Mounted under its own prefix because `/routes` already belongs to forecast routes,
# which are a different concept: a forecast route is a dispatcher-facing service with
# a numeric id, a tram-graph route is an OSM `ref` over the physical network.
router = APIRouter(prefix="/tram-graph", tags=["tram-graph"])


def _unknown_route(ref: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=(
            f"Unknown tram route ref {ref!r}. GET /tram-graph/routes lists every ref the "
            "graph carries; the larger route_relations count in /tram-graph/stats counts "
            "PTv2 route relations, one per direction, and is not a list of refs"
        ),
    )


@router.get("/stats", response_model=NetworkStatsResponse)
async def get_stats(service: TramNetworkServiceDep) -> NetworkStatsResponse:
    return NetworkStatsResponse.model_validate(await service.stats())


@router.get("/routes", response_model=list[TramRouteResponse])
async def list_routes(service: TramNetworkServiceDep) -> list[TramRouteResponse]:
    routes = await service.list_routes()
    return [TramRouteResponse.from_domain(route) for route in routes]


@router.get("/routes/{ref}", response_model=RouteDetailResponse)
async def get_route(ref: str, service: TramNetworkServiceDep) -> RouteDetailResponse:
    route = await service.get_route(ref)
    if route is None:
        raise _unknown_route(ref)
    return RouteDetailResponse.from_domain(route)


@router.get("/stops", response_model=list[TramStopResponse])
async def search_stops(
    service: TramNetworkServiceDep,
    q: str | None = Query(default=None, description="Case-insensitive substring of the stop name"),
    limit: int = Query(default=50, ge=1, le=1000),
) -> list[TramStopResponse]:
    stops = await service.search_stops(q, limit)
    return [TramStopResponse.model_validate(stop) for stop in stops]


@router.get("/stops/{stop_id}", response_model=StopDetailResponse)
async def get_stop(stop_id: int, service: TramNetworkServiceDep) -> StopDetailResponse:
    detail = await service.get_stop(stop_id)
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Unknown tram stop id {stop_id}; ids are OSM stop_position node ids",
        )
    return StopDetailResponse.from_domain(detail)


@router.get("/edges", response_model=list[TramEdgeResponse])
async def list_edges(
    service: TramNetworkServiceDep,
    route: str | None = Query(default=None, description="Restrict to one route ref"),
) -> list[TramEdgeResponse]:
    edges = await service.list_edges(route)
    if edges is None:
        raise _unknown_route(route or "")
    return [TramEdgeResponse.model_validate(edge) for edge in edges]


@router.get("/geojson", response_model=TramGraphGeoJson)
async def get_geojson(
    service: TramNetworkServiceDep,
    route: str | None = Query(default=None, description="Restrict to one route ref"),
) -> TramGraphGeoJson:
    geometry = await service.geometry(route)
    if geometry is None:
        raise _unknown_route(route or "")
    return TramGraphGeoJson.from_domain(geometry)


@router.get("/path", response_model=TramPathResponse)
async def find_path(
    service: TramNetworkServiceDep,
    source: int = Query(alias="from", description="Source stop id"),
    target: int = Query(alias="to", description="Target stop id"),
) -> TramPathResponse:
    """Cheapest ride between two stops by track distance.

    An unreachable pair answers 200 with `found=false` and a `reason`. The network is
    genuinely in two disconnected pieces and its edges are directed, so "no such ride"
    is information about the city, not a client error.
    """
    return TramPathResponse.model_validate(await service.find_path(source, target))
