from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Index, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.infrastructure.db.base import Base


class RouteModel(Base):
    __tablename__ = "routes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    number: Mapped[str] = mapped_column(String(16), unique=True)
    name: Mapped[str] = mapped_column(String(160))
    color: Mapped[str] = mapped_column(String(7), default="#d9342b")


class StopModel(Base):
    __tablename__ = "stops"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(160), unique=True)
    latitude: Mapped[float] = mapped_column(Float)
    longitude: Mapped[float] = mapped_column(Float)
    mode: Mapped[str] = mapped_column(String(24), default="tram")


class RouteStopModel(Base):
    __tablename__ = "route_stops"
    __table_args__ = (UniqueConstraint("route_id", "sequence"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"))
    sequence: Mapped[int] = mapped_column(Integer)


class NetworkEdgeModel(Base):
    __tablename__ = "network_edges"
    __table_args__ = (UniqueConstraint("source_stop_id", "target_stop_id", "mode"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    source_stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"))
    target_stop_id: Mapped[int] = mapped_column(ForeignKey("stops.id", ondelete="CASCADE"))
    mode: Mapped[str] = mapped_column(String(24))
    travel_time_minutes: Mapped[float] = mapped_column(Float)
    capacity_per_hour: Mapped[float] = mapped_column(Float)


class ForecastPointModel(Base):
    __tablename__ = "forecast_points"
    __table_args__ = (
        UniqueConstraint("route_id", "stop_id", "horizon", "bucket_start"),
        Index("ix_forecast_route_horizon_time", "route_id", "horizon", "bucket_start"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    route_id: Mapped[int] = mapped_column(ForeignKey("routes.id", ondelete="CASCADE"))
    stop_id: Mapped[int | None] = mapped_column(
        ForeignKey("stops.id", ondelete="CASCADE"), nullable=True
    )
    horizon: Mapped[str] = mapped_column(String(16))
    bucket_start: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    predicted_passengers: Mapped[float] = mapped_column(Float)
    lower_bound: Mapped[float] = mapped_column(Float)
    upper_bound: Mapped[float] = mapped_column(Float)
    capacity: Mapped[float] = mapped_column(Float, default=180.0)
    model_version: Mapped[str] = mapped_column(String(64))
    generated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
