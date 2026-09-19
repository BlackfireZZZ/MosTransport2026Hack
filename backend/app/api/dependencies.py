from functools import lru_cache
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forecast import ForecastService
from app.application.services.overpass import OverpassService
from app.application.services.tram_graph import TramNetworkService
from app.core.config import settings
from app.infrastructure.db.session import get_session
from app.infrastructure.overpass import HttpOverpassGateway
from app.infrastructure.repositories.forecast import SqlAlchemyForecastRepository
from app.infrastructure.repositories.tram_graph import FileTramGraphRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_forecast_service(session: SessionDep) -> ForecastService:
    return ForecastService(SqlAlchemyForecastRepository(session))


ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]


@lru_cache
def get_tram_graph_repository() -> FileTramGraphRepository:
    """Cached so the ~1 MB of committed JSON is parsed once per process, not per request."""
    return FileTramGraphRepository(settings.tram_graph_json, settings.tram_graph_geojson)


def get_tram_network_service() -> TramNetworkService:
    return TramNetworkService(get_tram_graph_repository())


TramNetworkServiceDep = Annotated[TramNetworkService, Depends(get_tram_network_service)]


def get_overpass_service() -> OverpassService:
    return OverpassService(
        HttpOverpassGateway(
            interpreter_url=settings.overpass_url,
            status_url=settings.resolved_overpass_status_url,
            query_timeout=settings.overpass_timeout,
            health_timeout=settings.overpass_health_timeout,
        ),
        max_query_chars=settings.overpass_max_query_chars,
    )


OverpassServiceDep = Annotated[OverpassService, Depends(get_overpass_service)]
