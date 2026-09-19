from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.forecast import (
    ForecastHorizon,
    ForecastPoint,
    ForecastSnapshot,
    RouteSummary,
    StopLoad,
)
from app.infrastructure.db.models import (
    ForecastPointModel,
    RouteModel,
    RouteStopModel,
    StopModel,
)


class SqlAlchemyForecastRepository:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_routes(self) -> list[RouteSummary]:
        result = await self._session.execute(select(RouteModel).order_by(RouteModel.number))
        return [
            RouteSummary(id=row.id, number=row.number, name=row.name, color=row.color)
            for row in result.scalars()
        ]

    async def get_snapshot(
        self, route_id: int, horizon: ForecastHorizon
    ) -> ForecastSnapshot | None:
        route = await self._session.get(RouteModel, route_id)
        if route is None:
            return None

        points_result = await self._session.execute(
            select(ForecastPointModel)
            .where(
                ForecastPointModel.route_id == route_id,
                ForecastPointModel.stop_id.is_(None),
                ForecastPointModel.horizon == horizon.value,
            )
            .order_by(ForecastPointModel.bucket_start)
        )
        point_rows = list(points_result.scalars())
        if not point_rows:
            return None

        stops_result = await self._session.execute(
            select(RouteStopModel, StopModel, ForecastPointModel)
            .join(StopModel, StopModel.id == RouteStopModel.stop_id)
            .join(
                ForecastPointModel,
                (ForecastPointModel.stop_id == StopModel.id)
                & (ForecastPointModel.route_id == route_id)
                & (ForecastPointModel.horizon == horizon.value),
            )
            .where(RouteStopModel.route_id == route_id)
            .order_by(RouteStopModel.sequence)
        )

        stops = [
            StopLoad(
                id=stop.id,
                name=stop.name,
                latitude=stop.latitude,
                longitude=stop.longitude,
                predicted_passengers=forecast.predicted_passengers,
                load_percent=forecast.predicted_passengers / forecast.capacity * 100,
                sequence=route_stop.sequence,
            )
            for route_stop, stop, forecast in stops_result.all()
        ]

        return ForecastSnapshot(
            route=RouteSummary(
                id=route.id, number=route.number, name=route.name, color=route.color
            ),
            horizon=horizon,
            generated_at=point_rows[0].generated_at,
            model_version=point_rows[0].model_version,
            points=[
                ForecastPoint(
                    timestamp=row.bucket_start,
                    predicted_passengers=row.predicted_passengers,
                    lower_bound=row.lower_bound,
                    upper_bound=row.upper_bound,
                    capacity=row.capacity,
                )
                for row in point_rows
            ],
            stops=stops,
        )
