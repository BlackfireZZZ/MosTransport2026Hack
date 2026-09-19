from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path

from pydantic import BaseModel, Field, model_validator


class ForecastCase(BaseModel):
    id: str
    horizon: str
    scenario: str
    actual: list[float]
    prediction: list[float]
    baseline_prediction: list[float]
    lower_bound: list[float]
    upper_bound: list[float]

    @model_validator(mode="after")
    def validate_series(self) -> ForecastCase:
        lengths = {
            len(self.actual),
            len(self.prediction),
            len(self.baseline_prediction),
            len(self.lower_bound),
            len(self.upper_bound),
        }
        if lengths != {len(self.actual)} or not self.actual:
            raise ValueError("all forecast series must have the same non-zero length")
        if any(value < 0 for series in self._series() for value in series):
            raise ValueError("passenger counts and interval bounds must be non-negative")
        if any(
            lower > prediction or prediction > upper
            for lower, prediction, upper in zip(
                self.lower_bound, self.prediction, self.upper_bound, strict=True
            )
        ):
            raise ValueError("prediction must be inside its uncertainty interval")
        return self

    def _series(self) -> tuple[list[float], ...]:
        return (
            self.actual,
            self.prediction,
            self.baseline_prediction,
            self.lower_bound,
            self.upper_bound,
        )


class SliceMetrics(BaseModel):
    observations: int = Field(gt=0)
    mae: float = Field(ge=0)
    wape: float = Field(ge=0)
    baseline_wape: float = Field(ge=0)
    interval_coverage: float = Field(ge=0, le=1)


class EvaluationSummary(BaseModel):
    passed: bool
    overall: SliceMetrics
    by_horizon: dict[str, SliceMetrics]
    thresholds: dict[str, float]


def load_cases(path: Path) -> list[ForecastCase]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("evaluation dataset must be a JSON list")
    return [ForecastCase.model_validate(item) for item in raw]


def evaluate(
    cases: list[ForecastCase],
    *,
    minimum_interval_coverage: float = 0.8,
) -> EvaluationSummary:
    if not cases:
        raise ValueError("at least one evaluation case is required")

    by_horizon: defaultdict[str, list[ForecastCase]] = defaultdict(list)
    for case in cases:
        by_horizon[case.horizon].append(case)

    overall = _metrics(cases)
    slices = {horizon: _metrics(items) for horizon, items in sorted(by_horizon.items())}
    passed = (
        overall.wape <= overall.baseline_wape
        and overall.interval_coverage >= minimum_interval_coverage
        and all(item.wape <= item.baseline_wape for item in slices.values())
    )
    return EvaluationSummary(
        passed=passed,
        overall=overall,
        by_horizon=slices,
        thresholds={"minimum_interval_coverage": minimum_interval_coverage},
    )


def _metrics(cases: list[ForecastCase]) -> SliceMetrics:
    actual: list[float] = []
    prediction: list[float] = []
    baseline: list[float] = []
    covered = 0
    for case in cases:
        actual.extend(case.actual)
        prediction.extend(case.prediction)
        baseline.extend(case.baseline_prediction)
        covered += sum(
            lower <= observed <= upper
            for observed, lower, upper in zip(
                case.actual, case.lower_bound, case.upper_bound, strict=True
            )
        )

    errors = [
        abs(observed - predicted)
        for observed, predicted in zip(actual, prediction, strict=True)
    ]
    baseline_errors = [
        abs(observed - predicted) for observed, predicted in zip(actual, baseline, strict=True)
    ]
    denominator = sum(actual)
    if math.isclose(denominator, 0):
        raise ValueError("evaluation slice must contain positive passenger demand")

    return SliceMetrics(
        observations=len(actual),
        mae=sum(errors) / len(errors),
        wape=sum(errors) / denominator,
        baseline_wape=sum(baseline_errors) / denominator,
        interval_coverage=covered / len(actual),
    )
