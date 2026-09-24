"""Entity × calendar-bucket counts. Cells are sparse; missing buckets are answered live."""

from collections import Counter
from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from tramflow_ml.features.coverage import CoverageCalendar
from tramflow_ml.features.periods import bucket_from_start, bucket_start_of, service_date
from tramflow_ml.features.records import (
    AggregateCell,
    EntityKey,
    FeatureError,
    Granularity,
    Observation,
)

CellKey = tuple[EntityKey, datetime]


@dataclass(frozen=True, slots=True)
class AggregateIndex:
    """Counts for the buckets that carry events; every other bucket is derived on demand.

    Materialising a dense entity × bucket grid over years of hourly buckets is not
    affordable, so the index stores only what happened and resolves any queried bucket
    against the coverage calendar.
    """

    granularity: Granularity
    target: str
    unit: str
    coverage: CoverageCalendar
    totals: Mapping[CellKey, int]

    def cell(self, entity: EntityKey, start: datetime) -> AggregateCell:
        """An uncovered bucket is missing with no value; a covered empty bucket is zero."""
        bucket = bucket_from_start(start, self.granularity)
        covered, total = self.coverage.units(bucket)
        if covered == 0:
            return AggregateCell(entity, bucket, None, "missing", 0, total)
        counted = self.totals.get((entity, bucket.start))
        return AggregateCell(
            entity, bucket, 0 if counted is None else counted, "observed", covered, total
        )

    def cells(self) -> tuple[AggregateCell, ...]:
        """Only the buckets that carry events, ordered for a reproducible reconciliation."""
        return tuple(
            self.cell(entity, start) for entity, start in sorted(self.totals, key=_cell_order)
        )

    @property
    def total(self) -> int:
        return sum(self.totals.values())


def _cell_order(key: CellKey) -> tuple[str, str, str, datetime]:
    entity, start = key
    return entity.route_id, entity.direction_id, entity.stop_id, start


def aggregate(
    observations: Iterable[Observation],
    granularity: Granularity,
    coverage: CoverageCalendar,
    target: str,
    unit: str,
) -> AggregateIndex:
    """Count matching observations per entity and bucket; inputs are never mutated."""
    totals: Counter[CellKey] = Counter()
    for observation in observations:
        if observation.target != target or observation.unit != unit:
            continue
        day = service_date(observation.event_at)
        if not coverage.covers(day):
            raise FeatureError(f"coverage calendar excludes {day.isoformat()}, which has events")
        totals[(observation.entity, bucket_start_of(observation.event_at, granularity))] += 1
    return AggregateIndex(granularity, target, unit, coverage, MappingProxyType(dict(totals)))
