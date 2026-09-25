"""Run one fold set past every model, in that order.

The fold set is built once, before any model is consulted, and the loop is folds outside
and models inside. A model is handed a ``FoldData`` that was already cut at the fold's
cutoff: it never receives the observation set, the coverage calendar or anything else it
could build a different fold from, so "both models saw the same folds" is a property of
what they are given rather than a rule they are asked to follow.
"""

import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import UTC

from tramflow_ml.backtest.config import BacktestConfig, FoldRules
from tramflow_ml.backtest.data import BacktestData
from tramflow_ml.backtest.folds import FoldSet, build_fold_set
from tramflow_ml.backtest.manifest import ModelVersion, build_manifest
from tramflow_ml.backtest.metrics import FoldMetrics, combine, fold_metrics
from tramflow_ml.backtest.records import BacktestError, Fold
from tramflow_ml.backtest.results import BacktestOutcome, FoldResult, HorizonOutcome
from tramflow_ml.features import (
    CoverageView,
    EntityKey,
    FeatureRequest,
    FeatureTable,
    HorizonPolicy,
    Observation,
    build_features,
)
from tramflow_ml.features.records import digest_of

EMPTY_METRICS = FoldMetrics(0, 0.0, 0.0)


@dataclass(frozen=True, slots=True)
class FoldData:
    """Everything a model may see for one fold, and nothing else.

    ``test_features`` holds the model-visible part of the feature rows only; the labels
    stay with the runner, so a model cannot read the value it is asked to predict.
    """

    fold: Fold
    policy: HorizonPolicy
    entities: tuple[EntityKey, ...]
    coverage: CoverageView
    train_observations: tuple[Observation, ...]
    validation_observations: tuple[Observation, ...]
    test_features: tuple[Mapping[str, object], ...]
    feature_names: tuple[str, ...]
    feature_digest: str

    @property
    def rows(self) -> int:
        return len(self.test_features)


class FoldModel:
    """The interface a candidate or a baseline implements.

    Subclassing is not required; any object carrying ``name``, ``version`` and ``predict``
    is accepted. The base exists so the contract has one place to be read.
    """

    name: str
    version: str

    def predict(self, fold: Fold, data: FoldData) -> Sequence[float]:
        raise NotImplementedError


@dataclass(frozen=True, slots=True)
class _Prepared:
    data: FoldData
    labels: tuple[float, ...]


def fold_data_for(
    config: BacktestConfig, data: BacktestData, rules: FoldRules, fold: Fold
) -> FoldData:
    """The cutoff-restricted view of one fold, built the way the runner builds it."""
    return _prepare(config, data, rules, fold).data


def run_backtest(
    config: BacktestConfig, data: BacktestData, models: Sequence[FoldModel]
) -> BacktestOutcome:
    """Build the folds once, then score every model on them."""
    versions = _model_versions(models)
    fold_set = build_fold_set(config, data.coverage)
    outcomes = {
        rules.horizon: _run_horizon(config, data, rules, fold_set, models)
        for rules in config.rules
    }
    manifest = build_manifest(
        target=config.target,
        unit=config.unit,
        config_hash=config.config_hash,
        data_hash=data.data_hash,
        fold_hash=fold_set.fold_hash,
        models=versions,
        horizons=[outcome.to_dict() for outcome in outcomes.values()],
    )
    return BacktestOutcome(outcomes, fold_set, manifest)


def _model_versions(models: Sequence[FoldModel]) -> tuple[ModelVersion, ...]:
    if not models:
        raise BacktestError("a backtest compares at least one model against its folds")
    versions = tuple(ModelVersion(model.name, model.version) for model in models)
    names = [version.name for version in versions]
    if len(set(names)) != len(names):
        raise BacktestError("model names must be unique within one backtest")
    return versions


def _run_horizon(
    config: BacktestConfig,
    data: BacktestData,
    rules: FoldRules,
    fold_set: FoldSet,
    models: Sequence[FoldModel],
) -> HorizonOutcome:
    folds = fold_set.for_horizon(rules.horizon)
    fold_ids = tuple(fold.fold_id for fold in folds)
    if len(folds) < rules.minimum_origins:
        return _refused(rules, fold_ids, models, _history_reason(rules, fold_set))
    scored: dict[str, list[FoldResult]] = {model.name: [] for model in models}
    with_demand = 0
    for fold in folds:
        prepared = _prepare(config, data, rules, fold)
        with_demand += 1 if sum(prepared.labels) > 0 else 0
        for model in models:
            scored[model.name].append(_score(fold, model, prepared))
    results = {name: tuple(items) for name, items in scored.items()}
    totals = {name: combine(item.metrics for item in items) for name, items in results.items()}
    return _verdict(rules, fold_ids, with_demand, results, totals)


def _verdict(
    rules: FoldRules,
    fold_ids: tuple[str, ...],
    with_demand: int,
    results: Mapping[str, tuple[FoldResult, ...]],
    totals: Mapping[str, FoldMetrics],
) -> HorizonOutcome:
    enough_demand = with_demand >= rules.minimum_origins
    reason = (
        ""
        if enough_demand
        else (
            f"{rules.horizon}: only {with_demand} of {len(fold_ids)} eligible origins carry "
            f"any demand, {rules.minimum_origins} required; WAPE is undefined on the rest"
        )
    )
    return HorizonOutcome(
        horizon=rules.horizon,
        status="evaluated" if enough_demand else "insufficient_signal",
        required_origins=rules.minimum_origins,
        eligible_origins=len(fold_ids),
        origins_with_demand=with_demand,
        reason=reason,
        fold_ids=fold_ids,
        results=results,
        totals=totals,
    )


def _history_reason(rules: FoldRules, fold_set: FoldSet) -> str:
    refusals = fold_set.refusals_for(rules.horizon)
    counts: dict[str, int] = {}
    for item in refusals:
        counts[item.reason] = counts.get(item.reason, 0) + 1
    breakdown = ", ".join(f"{reason}={counts[reason]}" for reason in sorted(counts))
    eligible = len(fold_set.for_horizon(rules.horizon))
    return (
        f"{rules.horizon}: {eligible} eligible origins, {rules.minimum_origins} required; "
        f"{len(refusals)} candidate origins refused ({breakdown or 'none'}); "
        "no fold was scored"
    )


def _refused(
    rules: FoldRules, fold_ids: tuple[str, ...], models: Sequence[FoldModel], reason: str
) -> HorizonOutcome:
    return HorizonOutcome(
        horizon=rules.horizon,
        status="insufficient_history",
        required_origins=rules.minimum_origins,
        eligible_origins=len(fold_ids),
        origins_with_demand=0,
        reason=reason,
        fold_ids=fold_ids,
        results={model.name: () for model in models},
        totals={model.name: EMPTY_METRICS for model in models},
    )


def _prepare(config: BacktestConfig, data: BacktestData, rules: FoldRules, fold: Fold) -> _Prepared:
    table = build_features(
        FeatureRequest(
            policy=rules.effective_policy,
            origin=fold.origin,
            entities=data.entities,
            observations=data.observations,
            coverage=data.coverage,
            target=config.target,
            unit=config.unit,
            capacities=data.capacities,
        )
    )
    _require_same_cutoff(fold, table)
    train, validation = _partition(config, data, fold)
    view = FoldData(
        fold=fold,
        policy=rules.effective_policy,
        entities=data.entities,
        coverage=data.coverage.as_of(fold.cutoff),
        train_observations=train,
        validation_observations=validation,
        test_features=tuple(row.feature_dict() for row in table.rows),
        feature_names=table.feature_names,
        feature_digest=table.feature_digest,
    )
    return _Prepared(view, _labels(fold, table))


def _require_same_cutoff(fold: Fold, table: FeatureTable) -> None:
    """The fold's cutoff and the feature layer's must name one instant, not two."""
    if table.header["cutoff"] != fold.cutoff.isoformat():
        raise BacktestError(
            f"{fold.fold_id}: the feature layer applied cutoff {table.header['cutoff']}, "
            f"the fold declares {fold.cutoff.isoformat()}"
        )


def _labels(fold: Fold, table: FeatureTable) -> tuple[float, ...]:
    """An eligible fold has a label in every bucket; a missing one is a defect, not a gap."""
    values: list[float] = []
    for row in table.rows:
        if row.target_value is None:
            raise BacktestError(
                f"{fold.fold_id}: bucket {row.bucket.start.isoformat()} has no label, "
                "so the fold should never have been eligible"
            )
        values.append(float(row.target_value))
    return tuple(values)


def _partition(
    config: BacktestConfig, data: BacktestData, fold: Fold
) -> tuple[tuple[Observation, ...], tuple[Observation, ...]]:
    """Cutoff-visible observations split by window, ordered so a model's sums reproduce."""
    visible = [
        item
        for item in data.observations
        if item.target == config.target
        and item.unit == config.unit
        and item.visible_at(fold.cutoff)
    ]
    ordered = sorted(visible, key=_observation_order)
    train = tuple(item for item in ordered if fold.train.contains(item.event_at))
    validation = tuple(item for item in ordered if fold.validation.contains(item.event_at))
    return train, validation


def _observation_order(observation: Observation) -> tuple[object, ...]:
    return (
        observation.event_at.astimezone(UTC),
        observation.entity,
        observation.available_at.astimezone(UTC),
    )


def _score(fold: Fold, model: FoldModel, prepared: _Prepared) -> FoldResult:
    predictions = _validated(fold, model, prepared, model.predict(fold, prepared.data))
    return FoldResult(
        fold_id=fold.fold_id,
        model=ModelVersion(model.name, model.version),
        rows=len(predictions),
        predictions_digest=digest_of(
            {
                "fold_id": fold.fold_id,
                "model": model.name,
                "version": model.version,
                "predictions": list(predictions),
            }
        ),
        metrics=fold_metrics(prepared.labels, predictions),
    )


def _validated(
    fold: Fold, model: FoldModel, prepared: _Prepared, predictions: Sequence[float]
) -> tuple[float, ...]:
    """A prediction must be what ``forecast_v1`` accepts: finite and non-negative."""
    expected = prepared.data.rows
    if len(predictions) != expected:
        raise BacktestError(
            f"{fold.fold_id}: {model.name} returned {len(predictions)} predictions "
            f"for {expected} test rows"
        )
    return tuple(
        _number(fold, model, position, value) for position, value in enumerate(predictions)
    )


def _number(fold: Fold, model: FoldModel, position: int, value: float) -> float:
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise BacktestError(f"{fold.fold_id}: {model.name} prediction {position} is not a number")
    number = float(value)
    if not math.isfinite(number) or number < 0:
        raise BacktestError(
            f"{fold.fold_id}: {model.name} prediction {position} must be finite and "
            "non-negative, as a published forecast point must be"
        )
    return number
