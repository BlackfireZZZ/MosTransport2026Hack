"""Which Moscow civil dates the source covers. Absence of rows is not absence of demand."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta

from tramflow_ml.features.periods import bucket_dates
from tramflow_ml.features.records import Bucket, FeatureError


@dataclass(frozen=True, slots=True)
class CoverageCalendar:
    """The explicit set of covered dates; a date outside it makes a bucket missing.

    This is an input, never an inference: without it a bucket with no rows cannot be
    told apart from a bucket the source never delivered.
    """

    dates: frozenset[date]

    def __post_init__(self) -> None:
        if not self.dates:
            raise FeatureError("coverage calendar must name at least one covered date")
        if any(type(day) is not date for day in self.dates):
            raise FeatureError("coverage calendar holds non-date entries")

    @classmethod
    def from_dates(cls, days: Iterable[date]) -> "CoverageCalendar":
        return cls(frozenset(days))

    @classmethod
    def from_range(cls, start: date, end: date, gaps: Iterable[date] = ()) -> "CoverageCalendar":
        """Half-open ``[start, end)`` of civil dates minus the source's stated gaps."""
        if end <= start:
            raise FeatureError("coverage range end must be after start")
        excluded = frozenset(gaps)
        span = (end - start).days
        return cls(frozenset(start + timedelta(days=offset) for offset in range(span)) - excluded)

    def covers(self, day: date) -> bool:
        return day in self.dates

    def units(self, bucket: Bucket) -> tuple[int, int]:
        """Covered and total civil dates of a bucket; a month keeps its gap visible."""
        days = bucket_dates(bucket)
        return sum(1 for day in days if day in self.dates), len(days)
