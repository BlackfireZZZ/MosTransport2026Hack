from fastapi import APIRouter, HTTPException, Query, status

from app.api.dependencies import ForecastServiceDep
from app.domain.forecast import ForecastHorizon, ScenarioParameters
from app.schemas.forecast import (
    ForecastResponse,
    RouteResponse,
    ScenarioRequest,
    ScenarioResponse,
)

router = APIRouter(tags=["forecast"])


@router.get("/routes", response_model=list[RouteResponse])
async def list_routes(service: ForecastServiceDep) -> list[RouteResponse]:
    routes = await service.list_routes()
    return [RouteResponse.model_validate(route) for route in routes]


@router.get("/forecasts", response_model=ForecastResponse)
async def get_forecast(
    service: ForecastServiceDep,
    route_id: int = Query(gt=0),
    horizon: ForecastHorizon = ForecastHorizon.DAY,
) -> ForecastResponse:
    snapshot = await service.get_forecast(route_id, horizon)
    if snapshot is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Forecast not found for the selected route and horizon",
        )
    return ForecastResponse.model_validate(snapshot)


@router.post("/scenarios/evaluate", response_model=ScenarioResponse)
async def evaluate_scenario(
    request: ScenarioRequest, service: ForecastServiceDep
) -> ScenarioResponse:
    result = await service.evaluate_scenario(
        request.route_id,
        request.horizon,
        ScenarioParameters(
            additional_vehicles=request.additional_vehicles,
            interval_change_percent=request.interval_change_percent,
            demand_change_percent=request.demand_change_percent,
        ),
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Baseline forecast not found for the scenario",
        )
    return ScenarioResponse.model_validate(result)
