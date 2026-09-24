from typing import Protocol

from app.domain.forecast import (
    ForecastHorizon,
    ForecastSnapshot,
    RouteSummary,
    ScenarioParameters,
    ScenarioResult,
    StopLoad,
)


class ForecastRepository(Protocol):
    async def list_routes(self) -> list[RouteSummary]: ...

    async def get_snapshot(
        self, route_id: int, horizon: ForecastHorizon
    ) -> ForecastSnapshot | None: ...


class ForecastService:
    def __init__(self, repository: ForecastRepository) -> None:
        self._repository = repository

    async def list_routes(self) -> list[RouteSummary]:
        return await self._repository.list_routes()

    async def get_forecast(
        self, route_id: int, horizon: ForecastHorizon
    ) -> ForecastSnapshot | None:
        return await self._repository.get_snapshot(route_id, horizon)

    async def evaluate_scenario(
        self,
        route_id: int,
        horizon: ForecastHorizon,
        parameters: ScenarioParameters,
    ) -> ScenarioResult | None:
        snapshot = await self.get_forecast(route_id, horizon)
        if snapshot is None:
            return None

        demand_factor = max(0.1, 1 + parameters.demand_change_percent / 100)
        capacity_factor = max(
            0.25,
            1 + parameters.additional_vehicles * 0.08 - parameters.interval_change_percent / 100,
        )
        scenario_load = (
            snapshot.peak_load_percent * demand_factor / capacity_factor
            if snapshot.peak_load_percent is not None
            else None
        )
        baseline_total = sum(point.predicted_passengers for point in snapshot.points)

        return ScenarioResult(
            baseline_peak_load_percent=snapshot.peak_load_percent,
            scenario_peak_load_percent=scenario_load,
            passenger_delta=baseline_total * (demand_factor - 1),
            capacity_delta=(capacity_factor - 1) * 100,
            affected_stops=[
                StopLoad(
                    id=stop.id,
                    name=stop.name,
                    latitude=stop.latitude,
                    longitude=stop.longitude,
                    predicted_passengers=stop.predicted_passengers * demand_factor,
                    load_percent=(
                        stop.load_percent * demand_factor / capacity_factor
                        if stop.load_percent is not None
                        else None
                    ),
                    sequence=stop.sequence,
                )
                for stop in snapshot.stops
            ],
        )
