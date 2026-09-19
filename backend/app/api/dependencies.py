from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.services.forecast import ForecastService
from app.infrastructure.db.session import get_session
from app.infrastructure.repositories.forecast import SqlAlchemyForecastRepository

SessionDep = Annotated[AsyncSession, Depends(get_session)]


def get_forecast_service(session: SessionDep) -> ForecastService:
    return ForecastService(SqlAlchemyForecastRepository(session))


ForecastServiceDep = Annotated[ForecastService, Depends(get_forecast_service)]
