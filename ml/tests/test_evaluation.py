from pathlib import Path

import pytest
from pydantic import ValidationError

from tramflow_ml.evaluation import ForecastCase, evaluate, load_cases


def test_golden_evaluation_beats_baseline_on_every_horizon() -> None:
    cases = load_cases(Path("ml/evals/golden_cases.json"))

    summary = evaluate(cases)

    assert summary.passed is True
    assert set(summary.by_horizon) == {"day", "month", "year"}
    assert summary.overall.interval_coverage >= 0.8


def test_case_rejects_misaligned_series() -> None:
    with pytest.raises(ValidationError, match="same non-zero length"):
        ForecastCase(
            id="broken",
            horizon="day",
            scenario="broken",
            actual=[1, 2],
            prediction=[1],
            baseline_prediction=[1],
            lower_bound=[0],
            upper_bound=[2],
        )
