from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum


class ForecastHorizon(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


@dataclass(frozen=True, slots=True)
class RouteSummary:
    id: int
    number: str
    name: str
    color: str


@dataclass(frozen=True, slots=True)
class ForecastPoint:
    timestamp: datetime
    predicted_passengers: float
    lower_bound: float | None
    upper_bound: float | None
    capacity: float | None


@dataclass(frozen=True, slots=True)
class StopLoad:
    id: int
    name: str
    latitude: float
    longitude: float
    predicted_passengers: float
    load_percent: float | None
    sequence: int


@dataclass(frozen=True, slots=True)
class ForecastSnapshot:
    route: RouteSummary
    horizon: ForecastHorizon
    generated_at: datetime
    model_version: str
    points: list[ForecastPoint]
    stops: list[StopLoad]

    @property
    def peak_passengers(self) -> float:
        return max((point.predicted_passengers for point in self.points), default=0)

    @property
    def peak_load_percent(self) -> float | None:
        if not self.points or any(
            point.capacity is None or point.capacity <= 0 for point in self.points
        ):
            return None
        percentages = [
            point.predicted_passengers / point.capacity * 100
            for point in self.points
            if point.capacity
        ]
        return max(percentages)


@dataclass(frozen=True, slots=True)
class ScenarioParameters:
    additional_vehicles: int = 0
    interval_change_percent: float = 0
    demand_change_percent: float = 0


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    baseline_peak_load_percent: float | None
    scenario_peak_load_percent: float | None
    passenger_delta: float
    capacity_delta: float
    affected_stops: list[StopLoad]
    solver_version: str = "network-flow-baseline-v1"
