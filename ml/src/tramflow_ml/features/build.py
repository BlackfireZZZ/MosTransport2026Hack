"""Assemble one deterministic feature table for one horizon and one cutoff."""

from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import datetime
from types import MappingProxyType

from tramflow_ml.features.aggregate import AggregateIndex, aggregate
from tramflow_ml.features.calendar_features import calendar_feature_names, calendar_features
from tramflow_ml.features.coverage import CoverageCalendar
from tramflow_ml.features.history import (
    lag_features,
    lag_names,
    rolling_features,
    rolling_names,
    seasonal_features,
    seasonal_names,
)
from tramflow_ml.features.periods import horizon_buckets
from tramflow_ml.features.policy import HorizonPolicy
from tramflow_ml.features.records import (
    FEATURE_VERSION,
    Bucket,
    EntityKey,
    FeatureError,
    FeatureHeader,
    FeatureRow,
    FeatureTable,
    FeatureValue,
    Observation,
)

HORIZON_INDEX = "horizon_index"
ENTITY_CAPACITY = "entity_capacity"


@dataclass(frozen=True, slots=True)
class FeatureRequest:
    """One horizon at one origin. Capacities absent from the mapping stay missing."""

    policy: HorizonPolicy
    origin: datetime
    entities: tuple[EntityKey, ...]
    observations: tuple[Observation, ...]
    coverage: CoverageCalendar
    target: str
    unit: str
    capacities: Mapping[EntityKey, float] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not self.entities:
            raise FeatureError("a feature request needs at least one entity")
        if not self.target or not self.unit:
            raise FeatureError("target and unit must be non-empty")


def feature_names(policy: HorizonPolicy) -> tuple[str, ...]:
    """The column order of every table this policy produces."""
    return (
        *calendar_feature_names(policy.granularity),
        HORIZON_INDEX,
        *lag_names(policy),
        *rolling_names(policy),
        *seasonal_names(policy),
        ENTITY_CAPACITY,
    )


def build_features(request: FeatureRequest) -> FeatureTable:
    """History is the cutoff-visible slice; labels come from the full series separately."""
    policy = request.policy
    cutoff = policy.cutoff(request.origin)
    visible = tuple(
        observation for observation in request.observations if observation.visible_at(cutoff)
    )
    history = _index(request, visible)
    labels = _index(request, request.observations)
    buckets = horizon_buckets(request.origin, policy.horizon)
    entities = tuple(sorted(set(request.entities)))
    names = feature_names(policy)
    rows = tuple(
        _row(request, history, labels, entity, bucket, index, cutoff, names)
        for entity in entities
        for index, bucket in enumerate(buckets)
    )
    return FeatureTable(_header(request, cutoff, names, len(entities), len(buckets)), rows)


def _index(request: FeatureRequest, observations: tuple[Observation, ...]) -> AggregateIndex:
    return aggregate(
        observations,
        request.policy.granularity,
        request.coverage,
        request.target,
        request.unit,
    )


def _header(
    request: FeatureRequest,
    cutoff: datetime,
    names: tuple[str, ...],
    entities: int,
    buckets: int,
) -> FeatureHeader:
    return {
        "feature_version": FEATURE_VERSION,
        "policy": request.policy.name,
        "horizon": request.policy.horizon,
        "granularity": request.policy.granularity,
        "timezone": "Europe/Moscow",
        "forecast_origin": request.origin.isoformat(),
        "cutoff": cutoff.isoformat(),
        "target": request.target,
        "unit": request.unit,
        "feature_names": list(names),
        "entities": entities,
        "buckets": buckets,
    }


def _row(
    request: FeatureRequest,
    history: AggregateIndex,
    labels: AggregateIndex,
    entity: EntityKey,
    bucket: Bucket,
    index: int,
    cutoff: datetime,
    names: tuple[str, ...],
) -> FeatureRow:
    policy = request.policy
    values: dict[str, FeatureValue] = {
        **calendar_features(bucket, policy.granularity),
        HORIZON_INDEX: float(index),
        **lag_features(history, entity, bucket.start, policy, cutoff),
        **rolling_features(history, entity, policy, cutoff),
        **seasonal_features(history, entity, bucket.start, policy, cutoff),
        ENTITY_CAPACITY: request.capacities.get(entity),
    }
    if tuple(values) != names:
        raise FeatureError("feature values disagree with the declared column order")
    label = labels.cell(entity, bucket.start)
    return FeatureRow(
        entity=entity,
        bucket=bucket,
        cutoff=cutoff,
        target=request.target,
        unit=request.unit,
        target_value=label.value,
        target_coverage=label.coverage,
        target_covered_units=label.covered_units,
        target_total_units=label.total_units,
        features=MappingProxyType(values),
    )
