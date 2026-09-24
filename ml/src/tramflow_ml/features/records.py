"""Immutable feature records. ``None`` is the only representation of missing."""

import json
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from hashlib import sha256
from types import MappingProxyType
from typing import Literal, TypedDict
from zoneinfo import ZoneInfo

FEATURE_VERSION = "features.v1"
MOSCOW = ZoneInfo("Europe/Moscow")
SECONDS_PER_HOUR = 3600

Horizon = Literal["day", "month", "year"]
Granularity = Literal["hourly", "daily", "monthly"]
Coverage = Literal["observed", "missing"]
FeatureValue = float | None

GRANULARITY_FOR_HORIZON: Mapping[Horizon, Granularity] = MappingProxyType(
    {"day": "hourly", "month": "daily", "year": "monthly"}
)
GRANULARITY_SUFFIX: Mapping[Granularity, str] = MappingProxyType(
    {"hourly": "h", "daily": "d", "monthly": "m"}
)


class FeatureError(ValueError):
    """Configuration or input defect that makes a feature table unsafe to produce."""


def require_aware(value: datetime, name: str) -> datetime:
    """Reject naive timestamps at the boundary; the layer has no default timezone."""
    if value.tzinfo is None or value.utcoffset() is None:
        raise FeatureError(f"{name} must be timezone-aware")
    try:
        value.astimezone(UTC)
    except OverflowError as error:
        raise FeatureError(f"{name} exceeds the supported datetime range") from error
    return value


@dataclass(frozen=True, slots=True, order=True)
class EntityKey:
    """Route, direction and stop; direction is never collapsed away."""

    route_id: str
    direction_id: str
    stop_id: str

    def to_dict(self) -> dict[str, str]:
        return {
            "route_id": self.route_id,
            "direction_id": self.direction_id,
            "stop_id": self.stop_id,
        }


@dataclass(frozen=True, slots=True)
class Observation:
    """One ingested event reduced to what aggregation needs."""

    entity: EntityKey
    event_at: datetime
    available_at: datetime
    target: str
    unit: str

    def __post_init__(self) -> None:
        require_aware(self.event_at, "event_at")
        require_aware(self.available_at, "available_at")
        if self.available_at.astimezone(UTC) < self.event_at.astimezone(UTC):
            raise FeatureError("available_at cannot precede event_at")

    def visible_at(self, cutoff: datetime) -> bool:
        """The ``data.v1`` availability rule: the event happened and is published."""
        instant = self.event_at.astimezone(UTC)
        published = self.available_at.astimezone(UTC)
        limit = cutoff.astimezone(UTC)
        return instant < limit and published <= limit


@dataclass(frozen=True, slots=True)
class Bucket:
    """Half-open Europe/Moscow interval."""

    start: datetime
    end: datetime

    def __post_init__(self) -> None:
        require_aware(self.start, "bucket start")
        require_aware(self.end, "bucket end")
        if self.end.astimezone(UTC) <= self.start.astimezone(UTC):
            raise FeatureError("a bucket must be a nonempty half-open interval")

    @property
    def elapsed_hours(self) -> float:
        """Measured on the instants, so a DST day is 23 or 25 hours, never 24."""
        delta = self.end.astimezone(UTC) - self.start.astimezone(UTC)
        return delta.total_seconds() / SECONDS_PER_HOUR

    def ends_by(self, cutoff: datetime) -> bool:
        return self.end.astimezone(UTC) <= cutoff.astimezone(UTC)


@dataclass(frozen=True, slots=True)
class AggregateCell:
    """``coverage == "missing"`` exactly when ``value is None``, as ObservedAggregate needs."""

    entity: EntityKey
    bucket: Bucket
    value: int | None
    coverage: Coverage
    covered_units: int
    total_units: int

    def to_dict(self) -> dict[str, object]:
        return {
            **self.entity.to_dict(),
            "bucket_start": self.bucket.start.isoformat(),
            "bucket_end": self.bucket.end.isoformat(),
            "value": self.value,
            "coverage": self.coverage,
            "covered_units": self.covered_units,
            "total_units": self.total_units,
        }


@dataclass(frozen=True, slots=True)
class FeatureRow:
    entity: EntityKey
    bucket: Bucket
    cutoff: datetime
    target: str
    unit: str
    target_value: int | None
    target_coverage: Coverage
    target_covered_units: int
    target_total_units: int
    features: Mapping[str, FeatureValue]

    def feature_dict(self) -> dict[str, object]:
        """Everything a model may consume; no label, so leakage is testable on its own."""
        return {
            **self.entity.to_dict(),
            "bucket_start": self.bucket.start.isoformat(),
            "bucket_end": self.bucket.end.isoformat(),
            "cutoff": self.cutoff.isoformat(),
            "features": dict(self.features),
        }

    def to_dict(self) -> dict[str, object]:
        return {
            **self.feature_dict(),
            "target": self.target,
            "unit": self.unit,
            "target_value": self.target_value,
            "target_coverage": self.target_coverage,
            "target_covered_units": self.target_covered_units,
            "target_total_units": self.target_total_units,
        }


class FeatureHeader(TypedDict):
    feature_version: str
    policy: str
    horizon: str
    granularity: str
    timezone: str
    forecast_origin: str
    cutoff: str
    target: str
    unit: str
    feature_names: list[str]
    entities: int
    buckets: int


@dataclass(frozen=True, slots=True)
class FeatureTable:
    header: FeatureHeader
    rows: tuple[FeatureRow, ...]

    @property
    def feature_names(self) -> tuple[str, ...]:
        return tuple(self.header["feature_names"])

    def to_dict(self) -> dict[str, object]:
        return {"header": dict(self.header), "rows": [row.to_dict() for row in self.rows]}

    @property
    def digest(self) -> str:
        """SHA-256 over the whole table, observed labels included."""
        return digest_of(self.to_dict())

    @property
    def feature_digest(self) -> str:
        """SHA-256 over the model-visible part only; the leakage guarantee is about this."""
        payload = {
            "header": dict(self.header),
            "rows": [row.feature_dict() for row in self.rows],
        }
        return digest_of(payload)


def encode(value: object) -> bytes:
    """Canonical JSON: sorted keys, compact separators, UTF-8, no NaN."""
    return json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")


def digest_of(payload: object) -> str:
    return sha256(encode(payload)).hexdigest()
