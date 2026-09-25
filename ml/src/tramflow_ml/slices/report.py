"""The slice report and the verdict it produces.

Two rules carry the whole design. Every slice the data can judge is judged, so a bad
slice cannot escape by nobody having listed it; and a *required* slice must additionally
exist and be judgeable, so it cannot escape by disappearing. ``passed`` is therefore
``not failures and not unproven``: an excellent overall number buys nothing.

A slice too small or too short to judge is reported in full with its support and marked,
never suppressed and never silently averaged into a pooled ratio.
"""

from collections.abc import Iterable, Mapping, Sequence
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Literal

from tramflow_ml.features.records import digest_of
from tramflow_ml.slices.metrics import (
    PASSING_STATUS,
    RATIO_UNIT,
    SliceMetrics,
    SliceStatus,
    baseline_totals,
    error_totals,
    interval_quality,
    overload_quality,
)
from tramflow_ml.slices.records import OVERALL_VALUE, ScoredPoint, SliceError, SliceKey
from tramflow_ml.slices.thresholds import GateThresholds

OVERALL_KEY = SliceKey("overall", OVERALL_VALUE)
Direction = Literal["at_most", "at_least"]


@dataclass(frozen=True, slots=True)
class SliceFailure:
    """A judged slice that breached a threshold, with everything needed to check it."""

    key: SliceKey
    metric: str
    unit: str
    observed: float
    limit: float
    direction: Direction
    threshold_name: str
    threshold_value: float
    samples: int
    folds: int

    def message(self) -> str:
        relation = "exceeds" if self.direction == "at_most" else "falls below"
        return (
            f"{self.key}: {self.metric} {self.observed:.6g} {self.unit} {relation} "
            f"{self.limit:.6g} ({self.threshold_name}={self.threshold_value:.6g}) "
            f"on {self.samples} samples across {self.folds} folds"
        )

    def to_dict(self) -> dict[str, object]:
        return {
            **self.key.to_dict(),
            "metric": self.metric,
            "unit": self.unit,
            "observed": self.observed,
            "limit": self.limit,
            "direction": self.direction,
            "threshold_name": self.threshold_name,
            "threshold_value": self.threshold_value,
            "samples": self.samples,
            "folds": self.folds,
            "message": self.message(),
        }


@dataclass(frozen=True, slots=True)
class UnprovenSlice:
    """A required slice the data could not judge. Absence never buys a pass."""

    key: SliceKey
    status: SliceStatus
    reason: str
    samples: int
    folds: int

    def message(self) -> str:
        return f"{self.key}: required slice is {self.status}: {self.reason}"

    def to_dict(self) -> dict[str, object]:
        return {
            **self.key.to_dict(),
            "status": self.status,
            "reason": self.reason,
            "samples": self.samples,
            "folds": self.folds,
            "message": self.message(),
        }


@dataclass(frozen=True, slots=True)
class SliceReport:
    target: str
    unit: str
    points: int
    folds: int
    thresholds: GateThresholds
    required: tuple[SliceKey, ...]
    metrics: tuple[SliceMetrics, ...]
    failures: tuple[SliceFailure, ...]
    unproven: tuple[UnprovenSlice, ...]
    by_key: Mapping[SliceKey, SliceMetrics] = field(init=False)

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "by_key", MappingProxyType({item.key: item for item in self.metrics})
        )

    @property
    def passed(self) -> bool:
        return not self.failures and not self.unproven

    def verdict(self) -> str:
        if self.passed:
            return f"PASS: {len(self.metrics)} slices judged against uncertified thresholds"
        lines = [f"FAIL: {len(self.failures)} breached, {len(self.unproven)} unproven"]
        lines.extend(failure.message() for failure in self.failures)
        lines.extend(item.message() for item in self.unproven)
        return "\n".join(lines)

    def to_dict(self) -> dict[str, object]:
        return {
            "passed": self.passed,
            "target": self.target,
            "unit": self.unit,
            "points": self.points,
            "folds": self.folds,
            "thresholds": self.thresholds.to_dict(),
            "required": [key.to_dict() for key in self.required],
            "slices": [item.to_dict() for item in self.metrics],
            "failures": [failure.to_dict() for failure in self.failures],
            "unproven": [item.to_dict() for item in self.unproven],
        }

    @property
    def digest(self) -> str:
        return digest_of(self.to_dict())


def build_report(
    points: Iterable[ScoredPoint],
    *,
    required: Iterable[SliceKey] = (),
    thresholds: GateThresholds | None = None,
) -> SliceReport:
    limits = GateThresholds() if thresholds is None else thresholds
    ordered = _canonical(points)
    target, unit = _single_quantity(ordered)
    groups = _group(ordered)
    metrics = tuple(_measure(key, groups[key], limits) for key in sorted(groups))
    demanded = tuple(sorted({*required, OVERALL_KEY}))
    by_key = {item.key: item for item in metrics}
    failures = tuple(
        failure
        for item in metrics
        if item.status == PASSING_STATUS
        for failure in _judge(item, limits)
    )
    unproven = tuple(
        _unproven(key, by_key.get(key))
        for key in demanded
        if _is_unproven(by_key.get(key))
    )
    return SliceReport(
        target=target,
        unit=unit,
        points=len(ordered),
        folds=len({point.fold_id for point in ordered}),
        thresholds=limits,
        required=demanded,
        metrics=metrics,
        failures=failures,
        unproven=unproven,
    )


def _canonical(points: Iterable[ScoredPoint]) -> tuple[ScoredPoint, ...]:
    ordered = tuple(sorted(points, key=lambda point: point.sort_key))
    if not ordered:
        raise SliceError("a slice report needs at least one scored point")
    return ordered


def _single_quantity(points: Sequence[ScoredPoint]) -> tuple[str, str]:
    targets = sorted({point.target for point in points})
    units = sorted({point.unit for point in points})
    if len(targets) > 1 or len(units) > 1:
        raise SliceError(
            f"a report covers one quantity; got targets {targets} and units {units}"
        )
    return targets[0], units[0]


def _group(points: Sequence[ScoredPoint]) -> dict[SliceKey, list[ScoredPoint]]:
    groups: dict[SliceKey, list[ScoredPoint]] = {}
    for point in points:
        for key in point.keys:
            groups.setdefault(key, []).append(point)
    return groups


def _measure(
    key: SliceKey, points: Sequence[ScoredPoint], limits: GateThresholds
) -> SliceMetrics:
    totals = error_totals(points)
    folds = len({point.fold_id for point in points})
    interval, interval_reason = interval_quality(points)
    overload, overload_reason = overload_quality(points)
    status, status_reason = _status(len(points), folds, totals.wape is None, limits)
    return SliceMetrics(
        key=key,
        unit=points[0].unit,
        samples=len(points),
        folds=folds,
        totals=totals,
        baseline=baseline_totals(points),
        interval=interval,
        interval_absent_reason=interval_reason,
        overload=overload,
        overload_absent_reason=overload_reason,
        status=status,
        status_reason=status_reason,
    )


def _status(
    samples: int, folds: int, no_demand: bool, limits: GateThresholds
) -> tuple[SliceStatus, str]:
    """Support is checked before signal: three rows carry no verdict either way."""
    if folds < limits.min_folds:
        return "insufficient_history", (
            f"{folds} fold(s) is below MIN_FOLDS_FOR_GATE={limits.min_folds}; "
            "one origin is not a temporal generalisation"
        )
    if samples < limits.min_samples:
        return "insufficient_samples", (
            f"{samples} sample(s) is below MIN_SAMPLES_FOR_GATE={limits.min_samples}; "
            "reported in full and excluded from the gate"
        )
    if no_demand:
        return "insufficient_signal", (
            "the slice carries no demand, so WAPE is undefined and is reported as null "
            "rather than as a zero"
        )
    return PASSING_STATUS, ""


def _judge(item: SliceMetrics, limits: GateThresholds) -> list[SliceFailure]:
    failures: list[SliceFailure] = []
    wape = item.wape
    if wape is None:
        return failures
    if wape > limits.max_wape:
        failures.append(
            _failure(
                item, "wape", RATIO_UNIT, wape, limits.max_wape, "MAX_WAPE", limits.max_wape
            )
        )
    failures.extend(_judge_baseline(item, limits, wape))
    failures.extend(_judge_interval(item, limits))
    return failures


def _judge_baseline(
    item: SliceMetrics, limits: GateThresholds, wape: float
) -> list[SliceFailure]:
    baseline_wape = item.baseline_wape
    if baseline_wape is None:
        return []
    limit = baseline_wape * limits.max_wape_ratio_to_baseline
    if wape <= limit:
        return []
    return [
        _failure(
            item,
            "wape_vs_baseline",
            RATIO_UNIT,
            wape,
            limit,
            "MAX_WAPE_RATIO_TO_BASELINE",
            limits.max_wape_ratio_to_baseline,
        )
    ]


def _judge_interval(item: SliceMetrics, limits: GateThresholds) -> list[SliceFailure]:
    interval = item.interval
    if interval is None:
        return []
    failures: list[SliceFailure] = []
    coverage_limit = interval.level - limits.max_coverage_shortfall
    if interval.coverage < coverage_limit:
        failures.append(
            _failure(
                item,
                "interval_coverage",
                RATIO_UNIT,
                interval.coverage,
                coverage_limit,
                "MAX_COVERAGE_SHORTFALL",
                limits.max_coverage_shortfall,
                direction="at_least",
            )
        )
    score_limit = item.mean_actual * limits.max_interval_score_to_mean_actual
    if interval.mean_score > score_limit:
        failures.append(
            _failure(
                item,
                "mean_interval_score",
                item.unit,
                interval.mean_score,
                score_limit,
                "MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL",
                limits.max_interval_score_to_mean_actual,
            )
        )
    return failures


def _failure(
    item: SliceMetrics,
    metric: str,
    unit: str,
    observed: float,
    limit: float,
    threshold_name: str,
    threshold_value: float,
    *,
    direction: Direction = "at_most",
) -> SliceFailure:
    return SliceFailure(
        key=item.key,
        metric=metric,
        unit=unit,
        observed=observed,
        limit=limit,
        direction=direction,
        threshold_name=threshold_name,
        threshold_value=threshold_value,
        samples=item.samples,
        folds=item.folds,
    )


def _is_unproven(item: SliceMetrics | None) -> bool:
    return item is None or item.status != PASSING_STATUS


def _unproven(key: SliceKey, item: SliceMetrics | None) -> UnprovenSlice:
    if item is None:
        return UnprovenSlice(
            key=key,
            status="insufficient_samples",
            reason="no scored point falls in this slice",
            samples=0,
            folds=0,
        )
    return UnprovenSlice(
        key=key,
        status=item.status,
        reason=item.status_reason,
        samples=item.samples,
        folds=item.folds,
    )
