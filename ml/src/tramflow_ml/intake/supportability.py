"""What the measured span and coverage can carry, and why not when they cannot.

The rule is stated once here rather than judged case by case: a horizon needs the
deepest reach its policy declares plus one forecast period of complete buckets, and
enough of the span's civil dates to have been observed at all. Every verdict is
reported next to the two numbers that produced it.

This derives eligibility from the data, not from a fold plan: the surplus is an upper
bound on evaluable buckets, and scheduling folds belongs to the backtest layer.
"""

from calendar import monthrange
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import date

from tramflow_ml.features.policy import POLICIES, HorizonPolicy
from tramflow_ml.features.records import Granularity
from tramflow_ml.ingestion.normalize import TARGETS, UNIT
from tramflow_ml.intake.records import (
    MIN_COVERAGE_RATIO,
    OTHER_VALUE,
    TARGET_BUCKETS,
    rate,
)

HOURS_PER_DAY = 24


@dataclass(frozen=True, slots=True)
class ObservedSpan:
    """First and last civil date carrying a row, and how many dates in between do."""

    first: date | None
    last: date | None
    observed_dates: int

    @property
    def span_days(self) -> int:
        if self.first is None or self.last is None:
            return 0
        return (self.last - self.first).days + 1

    @property
    def coverage_ratio(self) -> float:
        return rate(self.observed_dates, self.span_days)

    def to_dict(self) -> dict[str, object]:
        return {
            "coverage_ratio": self.coverage_ratio,
            "first_date": self.first.isoformat() if self.first else None,
            "last_date": self.last.isoformat() if self.last else None,
            "observed_dates": self.observed_dates,
            "span_days": self.span_days,
            "unobserved_dates_in_span": self.span_days - self.observed_dates,
        }


def horizon_support(span: ObservedSpan) -> dict[str, object]:
    return {policy.horizon: _policy_support(policy, span) for policy in _sorted_policies()}


def target_support(
    target_values: Mapping[str, int], unit_values: Mapping[str, int]
) -> dict[str, object]:
    producible = unit_values.get(UNIT, 0) > 0 and unit_values.get(OTHER_VALUE, 0) == 0
    return {
        "observed": {
            name: _target_verdict(name, target_values.get(name, 0), unit_values, producible)
            for name in sorted(TARGETS)
        },
        "unrecognised_target_rows": target_values.get(OTHER_VALUE, 0),
        "units": dict(sorted(unit_values.items())),
    }


def reach_buckets(policy: HorizonPolicy) -> int:
    """The oldest bucket any feature of this policy reads."""
    return max(
        max(policy.lags),
        max(policy.rolling_windows),
        policy.season_step * policy.season_periods,
    )


def complete_buckets(granularity: Granularity, span: ObservedSpan) -> int:
    if span.first is None or span.last is None:
        return 0
    if granularity == "hourly":
        return span.span_days * HOURS_PER_DAY
    if granularity == "daily":
        return span.span_days
    return _whole_months(span.first, span.last)


def _sorted_policies() -> list[HorizonPolicy]:
    return sorted(POLICIES.values(), key=lambda policy: policy.horizon)


def _policy_support(policy: HorizonPolicy, span: ObservedSpan) -> dict[str, object]:
    granularity = policy.granularity
    history = reach_buckets(policy)
    target = TARGET_BUCKETS[policy.horizon]
    required = history + target
    observed = complete_buckets(granularity, span)
    blockers: list[str] = []
    if observed < required:
        blockers.append(
            f"insufficient_history: policy {policy.name!r} reads {history} {granularity} "
            f"buckets of history and forecasts {target} more, so it needs {required}; "
            f"the observed span of {span.span_days} days yields {observed}"
        )
    if span.coverage_ratio < MIN_COVERAGE_RATIO:
        blockers.append(
            f"sparse_coverage: {span.observed_dates} of {span.span_days} civil dates in the "
            f"span carry rows (ratio {span.coverage_ratio}); at least {MIN_COVERAGE_RATIO} "
            "is required before a history window means anything"
        )
    return {
        "blockers": blockers,
        "evaluable_buckets_upper_bound": max(observed - required, 0),
        "granularity": granularity,
        "history_buckets": history,
        "observed_complete_buckets": observed,
        "policy": policy.name,
        "required_complete_buckets": required,
        "required_coverage_ratio": MIN_COVERAGE_RATIO,
        "supportable": not blockers,
        "target_buckets": target,
    }


def _target_verdict(
    name: str, rows: int, unit_values: Mapping[str, int], producible: bool
) -> dict[str, object]:
    blockers: list[str] = []
    if rows == 0:
        blockers.append(f"absent: no row declares the target {name!r}")
    elif not producible:
        blockers.append(
            f"unit_not_producible: this layer can only produce {UNIT!r}; the sample carries "
            f"{unit_values.get(OTHER_VALUE, 0)} rows with another unit"
        )
    return {"blockers": blockers, "rows": rows, "supportable": not blockers}


def _whole_months(first: date, last: date) -> int:
    """Calendar months fully inside the span; a part-month at either end does not count."""
    start = first if first.day == 1 else _next_month(first)
    end = last if last.day == monthrange(last.year, last.month)[1] else _previous_month_end(last)
    if end < start:
        return 0
    return (end.year * 12 + end.month) - (start.year * 12 + start.month) + 1


def _next_month(day: date) -> date:
    return date(day.year + day.month // 12, day.month % 12 + 1, 1)


def _previous_month_end(day: date) -> date:
    return date.fromordinal(day.replace(day=1).toordinal() - 1)
