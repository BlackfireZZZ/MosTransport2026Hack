"""Operational slice and interval-quality reporting for offline forecast evaluation."""

from tramflow_ml.slices.metrics import (
    LOAD_TARGET,
    LOAD_UNIT,
    IntervalQuality,
    OverloadQuality,
    SliceMetrics,
    SliceStatus,
    interval_score,
)
from tramflow_ml.slices.records import (
    EVENING_PEAK_HOURS,
    MORNING_PEAK_HOURS,
    DayPart,
    IntervalBounds,
    ScoredPoint,
    SliceAxis,
    SliceError,
    SliceKey,
)
from tramflow_ml.slices.report import (
    OVERALL_KEY,
    SliceFailure,
    SliceReport,
    UnprovenSlice,
    build_report,
)
from tramflow_ml.slices.thresholds import (
    MAX_COVERAGE_SHORTFALL,
    MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL,
    MAX_WAPE,
    MAX_WAPE_RATIO_TO_BASELINE,
    MIN_FOLDS_FOR_GATE,
    MIN_SAMPLES_FOR_GATE,
    GateThresholds,
)

__all__ = [
    "EVENING_PEAK_HOURS",
    "LOAD_TARGET",
    "LOAD_UNIT",
    "MAX_COVERAGE_SHORTFALL",
    "MAX_INTERVAL_SCORE_TO_MEAN_ACTUAL",
    "MAX_WAPE",
    "MAX_WAPE_RATIO_TO_BASELINE",
    "MIN_FOLDS_FOR_GATE",
    "MIN_SAMPLES_FOR_GATE",
    "MORNING_PEAK_HOURS",
    "OVERALL_KEY",
    "DayPart",
    "GateThresholds",
    "IntervalBounds",
    "IntervalQuality",
    "OverloadQuality",
    "ScoredPoint",
    "SliceAxis",
    "SliceError",
    "SliceFailure",
    "SliceKey",
    "SliceMetrics",
    "SliceReport",
    "SliceStatus",
    "UnprovenSlice",
    "build_report",
    "interval_score",
]
