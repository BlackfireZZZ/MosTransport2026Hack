from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from app.domain.forecast import ForecastHorizon


class RouteResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    number: str
    name: str
    color: str


class ForecastPointResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    timestamp: datetime
    predicted_passengers: float = Field(ge=0)
    lower_bound: float = Field(ge=0)
    upper_bound: float = Field(ge=0)
    capacity: float = Field(gt=0)


class StopLoadResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    latitude: float
    longitude: float
    predicted_passengers: float = Field(ge=0)
    load_percent: float = Field(ge=0)
    sequence: int = Field(ge=1)


class ForecastResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    route: RouteResponse
    horizon: ForecastHorizon
    generated_at: datetime
    model_version: str
    peak_passengers: float
    peak_load_percent: float
    points: list[ForecastPointResponse]
    stops: list[StopLoadResponse]


class ScenarioRequest(BaseModel):
    route_id: int = Field(gt=0)
    horizon: ForecastHorizon = ForecastHorizon.DAY
    additional_vehicles: int = Field(default=0, ge=-5, le=20)
    interval_change_percent: float = Field(default=0, ge=-75, le=200)
    demand_change_percent: float = Field(default=0, ge=-90, le=300)


class ScenarioResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    baseline_peak_load_percent: float
    scenario_peak_load_percent: float
    passenger_delta: float
    capacity_delta: float
    affected_stops: list[StopLoadResponse]
    solver_version: str
