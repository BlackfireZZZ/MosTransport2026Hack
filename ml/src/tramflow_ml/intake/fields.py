"""Per-field accumulators. What a field's classification allows is what gets printed.

An identifier accumulator keeps truncated digests rather than values, so it is not
merely a promise that no identifier is emitted: the accumulator holds nothing that
could be.
"""

import hashlib
from collections import Counter
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import date, datetime
from typing import Protocol
from zoneinfo import ZoneInfo

from tramflow_ml.ingestion.records import MOSCOW, ColumnAdapter
from tramflow_ml.intake.records import (
    DIGEST_BYTES,
    ENUMERATED_FIELDS,
    OTHER_VALUE,
    Classification,
    FormatSignature,
    classify,
    rate,
)

MISSING: object = object()
_IDENTIFIER_PUNCTUATION = frozenset("_.:/-")
_TRUE_STRINGS = frozenset({"true", "1"})
_FALSE_STRINGS = frozenset({"false", "0"})


def lookup(adapter: ColumnAdapter, name: str, row: Mapping[str, object]) -> object:
    column = adapter.source_column(name)
    if column in row:
        return row[column]
    return adapter.constants.get(name, MISSING)


def is_missing(raw: object) -> bool:
    """One definition across encodings: absent, null, or a blank string.

    A CSV carries every column on every row, so without the blank case a CSV could
    never reconcile against a JSON Lines file that simply omits the key.
    """
    if raw is MISSING or raw is None:
        return True
    return isinstance(raw, str) and not raw.strip()


def parse_instant(raw: object, pattern: str | None, zone: ZoneInfo | None) -> datetime | None:
    if not isinstance(raw, str):
        return None
    try:
        parsed = datetime.strptime(raw, pattern) if pattern else datetime.fromisoformat(raw)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        if zone is None:
            return None
        parsed = parsed.replace(tzinfo=zone)
    try:
        return parsed.astimezone(MOSCOW)
    except OverflowError:
        return None


def as_number(raw: object, coerce: bool) -> float | int | None:
    if isinstance(raw, bool):
        return None
    if isinstance(raw, int | float):
        return raw
    if coerce and isinstance(raw, str):
        try:
            return int(raw) if raw.lstrip("-").isdigit() else float(raw)
        except ValueError:
            return None
    return None


def as_flag(raw: object, coerce: bool) -> bool | None:
    if isinstance(raw, bool):
        return raw
    if coerce and isinstance(raw, str):
        lowered = raw.lower()
        if lowered in _TRUE_STRINGS:
            return True
        if lowered in _FALSE_STRINGS:
            return False
    return None


def signature(text: str) -> FormatSignature:
    if text.isdigit():
        return "digits"
    if text.isalpha():
        return "letters"
    if text.isalnum():
        return "alnum"
    if all(character.isalnum() or character in _IDENTIFIER_PUNCTUATION for character in text):
        return "alnum_punct"
    return "other"


def digest(text: str) -> bytes:
    return hashlib.sha256(text.encode("utf-8")).digest()[:DIGEST_BYTES]


class Accumulator(Protocol):
    classification: Classification

    def observe(self, raw: object, coerce: bool) -> None: ...

    def summary(self, rows: int) -> dict[str, object]: ...


@dataclass
class IdentifierProfile:
    """Cardinality, null rate and shape. Never a value, a sample or a frequency."""

    classification: Classification = "identifier"
    present: int = 0
    min_length: int | None = None
    max_length: int | None = None
    digests: set[bytes] = field(default_factory=set)
    signatures: Counter[str] = field(default_factory=Counter)

    def observe(self, raw: object, coerce: bool) -> None:
        text = raw if isinstance(raw, str) else str(raw)
        self.present += 1
        length = len(text)
        self.min_length = length if self.min_length is None else min(self.min_length, length)
        self.max_length = length if self.max_length is None else max(self.max_length, length)
        self.digests.add(digest(text))
        self.signatures[signature(text)] += 1

    def summary(self, rows: int) -> dict[str, object]:
        return {
            **_presence(self.classification, self.present, rows),
            "distinct_values": len(self.digests),
            "min_length": self.min_length,
            "max_length": self.max_length,
            "format_signatures": dict(sorted(self.signatures.items())),
        }


@dataclass
class TimestampProfile:
    classification: Classification = "timestamp"
    pattern: str | None = None
    zone: ZoneInfo | None = None
    present: int = 0
    unparsed: int = 0
    dates: set[date] = field(default_factory=set)
    first: datetime | None = None
    last: datetime | None = None

    def observe(self, raw: object, coerce: bool) -> None:
        self.present += 1
        instant = parse_instant(raw, self.pattern, self.zone)
        if instant is None:
            self.unparsed += 1
            return
        self.dates.add(instant.date())
        self.first = instant if self.first is None else min(self.first, instant)
        self.last = instant if self.last is None else max(self.last, instant)

    def summary(self, rows: int) -> dict[str, object]:
        return {
            **_presence(self.classification, self.present, rows),
            "unparsed": self.unparsed,
            "first": self.first.isoformat() if self.first else None,
            "last": self.last.isoformat() if self.last else None,
        }


@dataclass
class MeasureProfile:
    classification: Classification = "measure"
    present: int = 0
    unparsed: int = 0
    minimum: float | int | None = None
    maximum: float | int | None = None
    total: int = 0
    integral: bool = True

    def observe(self, raw: object, coerce: bool) -> None:
        self.present += 1
        value = as_number(raw, coerce)
        if value is None:
            self.unparsed += 1
            return
        self.minimum = value if self.minimum is None else min(self.minimum, value)
        self.maximum = value if self.maximum is None else max(self.maximum, value)
        if isinstance(value, int):
            self.total += value
        else:
            self.integral = False

    def summary(self, rows: int) -> dict[str, object]:
        return {
            **_presence(self.classification, self.present, rows),
            "unparsed": self.unparsed,
            "minimum": self.minimum,
            "maximum": self.maximum,
            "sum": self.total if self.integral else None,
        }


@dataclass
class EnumeratedProfile:
    """Counts per allowlisted member; a value outside it is counted, never quoted."""

    allowed: frozenset[str] = frozenset()
    boolean: bool = False
    classification: Classification = "enumerated"
    present: int = 0
    counts: Counter[str] = field(default_factory=Counter)

    def observe(self, raw: object, coerce: bool) -> None:
        self.present += 1
        self.counts[self._member(raw, coerce)] += 1

    def _member(self, raw: object, coerce: bool) -> str:
        if self.boolean:
            flag = as_flag(raw, coerce)
            return OTHER_VALUE if flag is None else str(flag).lower()
        text = raw if isinstance(raw, str) else str(raw)
        return text if text in self.allowed else OTHER_VALUE

    def summary(self, rows: int) -> dict[str, object]:
        values = {member: self.counts.get(member, 0) for member in sorted(self.allowed)}
        return {
            **_presence(self.classification, self.present, rows),
            "values": {**values, OTHER_VALUE: self.counts.get(OTHER_VALUE, 0)},
        }


def make_accumulator(name: str, adapter: ColumnAdapter, zone: ZoneInfo | None) -> Accumulator:
    kind = classify(name)
    if kind == "identifier":
        return IdentifierProfile()
    if kind == "timestamp":
        return TimestampProfile(pattern=adapter.timestamp_format, zone=zone)
    if kind == "enumerated":
        return EnumeratedProfile(allowed=ENUMERATED_FIELDS[name], boolean=name == "synthetic")
    return MeasureProfile()


def _presence(classification: Classification, present: int, rows: int) -> dict[str, object]:
    missing = rows - present
    return {
        "classification": classification,
        "present": present,
        "missing": missing,
        "missing_rate": rate(missing, rows),
    }
