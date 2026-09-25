"""What one slice measured, and what it refused to measure.

Error totals come from ``backtest.metrics`` unchanged, so WAPE has one definition in
this repository's offline path and zero demand yields ``None`` here for the same reason
it does there. Interval quality is the interval (Winkler) score reported beside coverage
and width: coverage alone rewards ``[0, inf)``, which is perfectly covered and says
nothing. Overload is a fraction of capacity, so it is absent -- with the reason -- unless
the target is an occupancy and the capacity is actually known.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from typing import Literal

from tramflow_ml.backtest.metrics import FoldMetrics, fold_metrics
from tramflow_ml.slices.records import IntervalBounds, ScoredPoint, SliceError, SliceKey

LOAD_TARGET = "onboard_load"
LOAD_UNIT = "passengers"
RATIO_UNIT = "ratio"

SliceStatus = Literal[
    "evaluated",
    "insufficient_history",
    "insufficient_samples",
    "insufficient_signal",
]
PASSING_STATUS: SliceStatus = "evaluated"


def interval_score(bounds: IntervalBounds, actual: float) -> float:
    """Winkler score: width plus ``2/alpha`` times the distance missed, lower is better.

    In the target's unit, so it is comparable with MAE and with mean demand. A wider
    interval can only lower this by the coverage it buys, which is what makes it a
    proper rule and coverage on its own not one.
    """
    alpha = 1.0 - bounds.level
    below = max(bounds.lower - actual, 0.0)
    above = max(actual - bounds.upper, 0.0)
    return bounds.width + (2.0 / alpha) * (below + above)


@dataclass(frozen=True, slots=True)
class IntervalQuality:
    """Coverage, width and score together; none of the three is reportable alone."""

    level: float
    method: str
    samples: int
    covered: int
    width_total: float
    score_total: float

    def __post_init__(self) -> None:
        if self.samples < 1:
            raise SliceError("interval quality needs at least one bounded point")
        if not 0 <= self.covered <= self.samples:
            raise SliceError("covered points must lie within the bounded points")

    @property
    def coverage(self) -> float:
        return self.covered / self.samples

    @property
    def mean_width(self) -> float:
        return self.width_total / self.samples

    @property
    def mean_score(self) -> float:
        return self.score_total / self.samples

    def to_dict(self) -> dict[str, object]:
        return {
            "level": self.level,
            "method": self.method,
            "samples": self.samples,
            "covered": self.covered,
            "coverage": self.coverage,
            "mean_width": self.mean_width,
            "mean_interval_score": self.mean_score,
        }


@dataclass(frozen=True, slots=True)
class OverloadQuality:
    """Only ever built where a capacity was known; there is no default capacity here."""

    samples: int
    actual_overloaded: int
    predicted_overloaded: int

    @property
    def actual_rate(self) -> float:
        return self.actual_overloaded / self.samples

    @property
    def predicted_rate(self) -> float:
        return self.predicted_overloaded / self.samples

    def to_dict(self) -> dict[str, object]:
        return {
            "samples": self.samples,
            "actual_overloaded": self.actual_overloaded,
            "predicted_overloaded": self.predicted_overloaded,
            "actual_overload_rate": self.actual_rate,
            "predicted_overload_rate": self.predicted_rate,
        }


def interval_quality(points: Sequence[ScoredPoint]) -> tuple[IntervalQuality | None, str]:
    bounded = [point for point in points if point.interval is not None]
    if not bounded:
        return None, "no point in this slice carries an interval"
    if len(bounded) != len(points):
        return None, (
            f"only {len(bounded)} of {len(points)} points carry an interval; "
            "a partial coverage figure would describe a different slice"
        )
    levels = sorted({point.interval.level for point in bounded if point.interval})
    if len(levels) > 1:
        return None, f"points declare different interval levels: {levels}"
    methods = sorted({point.interval.method for point in bounded if point.interval})
    if len(methods) > 1:
        return None, f"points declare different interval methods: {methods}"
    covered = 0
    width_total = 0.0
    score_total = 0.0
    for point in bounded:
        bounds = point.interval
        if bounds is None:
            raise SliceError("unreachable: bounded points carry an interval")
        covered += bounds.covers(point.actual)
        width_total += bounds.width
        score_total += interval_score(bounds, point.actual)
    return (
        IntervalQuality(levels[0], methods[0], len(bounded), covered, width_total, score_total),
        "",
    )


def overload_quality(points: Sequence[ScoredPoint]) -> tuple[OverloadQuality | None, str]:
    target = points[0].target
    unit = points[0].unit
    if target != LOAD_TARGET:
        return None, (
            f"target {target!r} is not an occupancy; a fraction of capacity is defined "
            f"only for {LOAD_TARGET!r}"
        )
    if unit != LOAD_UNIT:
        return None, f"unit {unit!r} is not {LOAD_UNIT!r}, so it cannot be divided by a capacity"
    unknown = sum(1 for point in points if point.capacity is None)
    if unknown:
        return None, (
            f"capacity is unknown for {unknown} of {len(points)} points; overload is not "
            "computed against a guessed capacity"
        )
    actual = 0
    predicted = 0
    for point in points:
        capacity = point.capacity
        if capacity is None:
            raise SliceError("unreachable: every point was checked for a capacity")
        actual += point.actual > capacity
        predicted += point.predicted > capacity
    return OverloadQuality(len(points), actual, predicted), ""


@dataclass(frozen=True, slots=True)
class SliceMetrics:
    """One slice's numbers, each inseparable from its unit, samples and folds."""

    key: SliceKey
    unit: str
    samples: int
    folds: int
    totals: FoldMetrics
    baseline: FoldMetrics | None
    interval: IntervalQuality | None
    interval_absent_reason: str
    overload: OverloadQuality | None
    overload_absent_reason: str
    status: SliceStatus
    status_reason: str

    @property
    def mae(self) -> float | None:
        return self.totals.mae

    @property
    def wape(self) -> float | None:
        return self.totals.wape

    @property
    def baseline_wape(self) -> float | None:
        return None if self.baseline is None else self.baseline.wape

    @property
    def mean_actual(self) -> float:
        return self.totals.actual_total / self.samples

    @property
    def relative_interval_width(self) -> float | None:
        if self.interval is None or self.totals.actual_total == 0:
            return None
        return self.interval.mean_width / self.mean_actual

    def to_dict(self) -> dict[str, object]:
        return {
            **self.key.to_dict(),
            "unit": self.unit,
            "samples": self.samples,
            "folds": self.folds,
            "status": self.status,
            "status_reason": self.status_reason,
            "actual_total": self.totals.actual_total,
            "error_total": self.totals.error_total,
            "mae": self.mae,
            "wape": self.wape,
            "mean_actual": self.mean_actual,
            "baseline_wape": self.baseline_wape,
            "relative_interval_width": self.relative_interval_width,
            "interval": None if self.interval is None else self.interval.to_dict(),
            "interval_absent_reason": self.interval_absent_reason,
            "overload": None if self.overload is None else self.overload.to_dict(),
            "overload_absent_reason": self.overload_absent_reason,
        }


def error_totals(points: Sequence[ScoredPoint]) -> FoldMetrics:
    return fold_metrics(
        [point.actual for point in points], [point.predicted for point in points]
    )


def baseline_totals(points: Sequence[ScoredPoint]) -> FoldMetrics | None:
    """``None`` unless every point in the slice carries a baseline to compare against."""
    baselines = [point.baseline for point in points]
    if any(value is None for value in baselines):
        return None
    return fold_metrics(
        [point.actual for point in points],
        [value for value in baselines if value is not None],
    )
