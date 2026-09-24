"""Lags, rolling and seasonal statistics, every one of them clipped at the cutoff."""

from datetime import datetime

from tramflow_ml.features.aggregate import AggregateIndex
from tramflow_ml.features.periods import bucket_from_start, bucket_start_of, step
from tramflow_ml.features.policy import HorizonPolicy
from tramflow_ml.features.records import EntityKey, FeatureValue

ROLLING_STATISTICS = ("sum", "mean", "max", "coverage")
SEASONAL_STATISTICS = ("mean", "coverage")


def lag_name(policy: HorizonPolicy, steps: int) -> str:
    return f"lag_{steps}{policy.suffix}"


def lag_names(policy: HorizonPolicy) -> tuple[str, ...]:
    return tuple(lag_name(policy, steps) for steps in policy.lags)


def rolling_prefix(policy: HorizonPolicy, window: int) -> str:
    return f"roll_{window}{policy.suffix}"


def rolling_names(policy: HorizonPolicy) -> tuple[str, ...]:
    return tuple(
        f"{rolling_prefix(policy, window)}_{statistic}"
        for window in policy.rolling_windows
        for statistic in ROLLING_STATISTICS
    )


def seasonal_prefix(policy: HorizonPolicy) -> str:
    return f"seasonal_{policy.season_periods}x{policy.season_step}{policy.suffix}"


def seasonal_names(policy: HorizonPolicy) -> tuple[str, ...]:
    return tuple(f"{seasonal_prefix(policy)}_{statistic}" for statistic in SEASONAL_STATISTICS)


def available_value(
    index: AggregateIndex, entity: EntityKey, start: datetime, cutoff: datetime
) -> FeatureValue:
    """A bucket still running at the cutoff is missing, never a partial sum."""
    if not bucket_from_start(start, index.granularity).ends_by(cutoff):
        return None
    cell = index.cell(entity, start)
    return None if cell.value is None else float(cell.value)


def anchor_start(policy: HorizonPolicy, cutoff: datetime) -> datetime:
    """Start of the last bucket that has fully elapsed at the cutoff."""
    return step(bucket_start_of(cutoff, policy.granularity), policy.granularity, -1)


def lag_features(
    index: AggregateIndex,
    entity: EntityKey,
    target_start: datetime,
    policy: HorizonPolicy,
    cutoff: datetime,
) -> dict[str, FeatureValue]:
    """Whole-bucket offsets from the target; a lag inside the horizon stays missing."""
    return {
        lag_name(policy, steps): available_value(
            index, entity, step(target_start, policy.granularity, -steps), cutoff
        )
        for steps in policy.lags
    }


def rolling_features(
    index: AggregateIndex, entity: EntityKey, policy: HorizonPolicy, cutoff: datetime
) -> dict[str, FeatureValue]:
    """Windows end at the cutoff, so no anchor can reach into the forecast horizon."""
    anchor = anchor_start(policy, cutoff)
    features: dict[str, FeatureValue] = {}
    for window in policy.rolling_windows:
        starts = [step(anchor, policy.granularity, -offset) for offset in range(window - 1, -1, -1)]
        values = [available_value(index, entity, start, cutoff) for start in starts]
        features.update(_statistics(rolling_prefix(policy, window), values, window))
    return features


def seasonal_features(
    index: AggregateIndex,
    entity: EntityKey,
    target_start: datetime,
    policy: HorizonPolicy,
    cutoff: datetime,
) -> dict[str, FeatureValue]:
    """The same calendar phase in earlier periods: whole seasons back, never 30 days."""
    starts = [
        step(target_start, policy.granularity, -policy.season_step * period)
        for period in range(policy.season_periods, 0, -1)
    ]
    values = [available_value(index, entity, start, cutoff) for start in starts]
    statistics = _statistics(seasonal_prefix(policy), values, policy.season_periods)
    return {name: statistics[name] for name in seasonal_names(policy)}


def _statistics(prefix: str, values: list[FeatureValue], window: int) -> dict[str, FeatureValue]:
    """Summed in chronological order so the float result is reproducible."""
    observed = [value for value in values if value is not None]
    coverage = len(observed) / window
    if not observed:
        return {
            f"{prefix}_sum": None,
            f"{prefix}_mean": None,
            f"{prefix}_max": None,
            f"{prefix}_coverage": coverage,
        }
    total = 0.0
    for value in observed:
        total += value
    return {
        f"{prefix}_sum": total,
        f"{prefix}_mean": total / len(observed),
        f"{prefix}_max": max(observed),
        f"{prefix}_coverage": coverage,
    }
