"""Strict v1 contracts for dataset manifests and published forecast artifacts.

This module is a repository-level reference validator. It is intentionally not
imported by the online worker yet: the publication task will decide how this
contract is packaged at the producer/consumer boundary.
"""

from datetime import datetime
from enum import StrEnum
from typing import Annotated, Literal
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, model_validator

MOSCOW = ZoneInfo("Europe/Moscow")
SchemaVersion = Literal["forecast.v1"]
Identifier = Annotated[str, Field(min_length=1, max_length=128, pattern=r"^[A-Za-z0-9_.:/-]+$")]
FiniteNonNegative = Annotated[float, Field(ge=0, allow_inf_nan=False)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)


class ForecastHorizon(StrEnum):
    DAY = "day"
    MONTH = "month"
    YEAR = "year"


class BucketGranularity(StrEnum):
    HOURLY = "hourly"
    DAILY = "daily"
    MONTHLY = "monthly"


class ForecastTarget(StrEnum):
    SYNTHETIC_BOARDINGS = "synthetic_boardings"
    VALIDATION_COUNT = "validation_count"
    BOARDING_COUNT = "boarding_count"
    ONBOARD_LOAD = "onboard_load"


class AggregationUnit(StrEnum):
    EVENT_COUNT = "event_count"
    PASSENGERS = "passengers"
    VEHICLES = "vehicles"


class DatasetManifest(ContractModel):
    schema_version: SchemaVersion
    dataset_id: Identifier
    source_version: Identifier
    source_hash: Annotated[str, Field(min_length=16, max_length=128, pattern=r"^[a-fA-F0-9]+$")]
    date_from: datetime
    date_to: datetime
    timezone: Literal["Europe/Moscow"] = "Europe/Moscow"
    feature_version: Identifier
    target: ForecastTarget
    unit: AggregationUnit
    entity_version: Identifier
    availability_policy: Identifier
    synthetic: bool

    @model_validator(mode="after")
    def validate_manifest(self) -> "DatasetManifest":
        _require_aware(self.date_from, "date_from")
        _require_aware(self.date_to, "date_to")
        if self.date_to <= self.date_from:
            raise ValueError("date_to must be after date_from")
        if self.synthetic and self.target != ForecastTarget.SYNTHETIC_BOARDINGS:
            raise ValueError("synthetic datasets must use synthetic_boardings target")
        if self.target == ForecastTarget.ONBOARD_LOAD and self.unit != AggregationUnit.PASSENGERS:
            raise ValueError("onboard_load requires passengers unit")
        expected_unit = {
            ForecastTarget.SYNTHETIC_BOARDINGS: AggregationUnit.EVENT_COUNT,
            ForecastTarget.VALIDATION_COUNT: AggregationUnit.EVENT_COUNT,
            ForecastTarget.BOARDING_COUNT: AggregationUnit.PASSENGERS,
            ForecastTarget.ONBOARD_LOAD: AggregationUnit.PASSENGERS,
        }[self.target]
        if self.unit != expected_unit:
            raise ValueError(f"{self.target.value} requires {expected_unit.value} unit")
        return self


class ForecastPoint(ContractModel):
    route_id: Identifier
    direction_id: Identifier
    stop_id: Identifier
    bucket_start: datetime
    bucket_end: datetime
    predicted: FiniteNonNegative
    lower_bound: FiniteNonNegative | None = None
    upper_bound: FiniteNonNegative | None = None

    @model_validator(mode="after")
    def validate_point(self) -> "ForecastPoint":
        _require_aware(self.bucket_start, "bucket_start")
        _require_aware(self.bucket_end, "bucket_end")
        if self.bucket_end <= self.bucket_start:
            raise ValueError("bucket_end must be after bucket_start")
        bounds = (self.lower_bound, self.upper_bound)
        if any(bound is None for bound in bounds) and any(bound is not None for bound in bounds):
            raise ValueError("lower_bound and upper_bound must be both present or absent")
        if self.lower_bound is not None and self.upper_bound is not None:
            if not self.lower_bound <= self.predicted <= self.upper_bound:
                raise ValueError("predicted must be inside uncertainty bounds")
        return self


class ForecastArtifact(ContractModel):
    schema_version: SchemaVersion
    run_id: Identifier
    dataset_id: Identifier
    target: ForecastTarget
    unit: AggregationUnit
    synthetic: bool
    horizon: ForecastHorizon
    bucket_granularity: BucketGranularity
    forecast_origin: datetime
    generated_at: datetime
    data_cutoff: datetime
    source_version: Identifier
    feature_version: Identifier
    model_version: Identifier
    graph_version: Identifier | None = None
    interval_level: Annotated[float, Field(gt=0, lt=1, allow_inf_nan=False)] | None = None
    interval_method: Identifier | None = None
    points: list[ForecastPoint] = Field(min_length=1)

    @model_validator(mode="after")
    def validate_artifact(self) -> "ForecastArtifact":
        for name in ("forecast_origin", "generated_at", "data_cutoff"):
            _require_aware(getattr(self, name), name)
        if self.data_cutoff > self.forecast_origin:
            raise ValueError("data_cutoff cannot be after forecast_origin")
        if self.generated_at < self.forecast_origin:
            raise ValueError("generated_at cannot be before forecast_origin")
        if self.synthetic and self.target != ForecastTarget.SYNTHETIC_BOARDINGS:
            raise ValueError("synthetic artifacts must use synthetic_boardings target")
        expected_unit = {
            ForecastTarget.SYNTHETIC_BOARDINGS: AggregationUnit.EVENT_COUNT,
            ForecastTarget.VALIDATION_COUNT: AggregationUnit.EVENT_COUNT,
            ForecastTarget.BOARDING_COUNT: AggregationUnit.PASSENGERS,
            ForecastTarget.ONBOARD_LOAD: AggregationUnit.PASSENGERS,
        }[self.target]
        if self.unit != expected_unit:
            raise ValueError(f"{self.target.value} requires {expected_unit.value} unit")
        expected_granularity = {
            ForecastHorizon.DAY: BucketGranularity.HOURLY,
            ForecastHorizon.MONTH: BucketGranularity.DAILY,
            ForecastHorizon.YEAR: BucketGranularity.MONTHLY,
        }[self.horizon]
        if self.bucket_granularity != expected_granularity:
            raise ValueError(
                f"{self.horizon.value} horizon requires {expected_granularity.value} buckets"
            )
        if (self.interval_level is None) != (self.interval_method is None):
            raise ValueError("interval_level and interval_method must be both present or absent")
        keys = [
            (point.route_id, point.direction_id, point.stop_id, point.bucket_start)
            for point in self.points
        ]
        if len(keys) != len(set(keys)):
            raise ValueError("forecast points must have unique route/direction/stop/bucket keys")
        for point in self.points:
            if point.bucket_start < self.forecast_origin:
                raise ValueError("forecast bucket cannot start before forecast_origin")
        return self


def _require_aware(value: datetime, name: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError(f"{name} must be timezone-aware")


def validate_forecast_json(payload: str) -> ForecastArtifact:
    """Validate the canonical JSON representation, including datetime strings."""
    return ForecastArtifact.model_validate_json(payload)
