"""Column names are untrusted input, because a headerless file puts data where a
header belongs.

Intake cannot know that a CSV's first line is a header, and a JSON object can be
keyed by anything. So a name is quoted only when it is word-like; anything else is
described by shape at its position. The position is what keeps the checklist
actionable — the operator still learns which column needs mapping — while the cell
that was mistaken for a name is never printed.
"""

from dataclasses import dataclass

from tramflow_ml.intake.fields import signature
from tramflow_ml.intake.records import MAX_COLUMN_NAME_LENGTH

POSITIONAL_PREFIX = "column_"


@dataclass(frozen=True, slots=True)
class ColumnRef:
    """A source column: the real name for matching, a safe label for printing."""

    position: int
    name: str
    label: str

    @classmethod
    def of(cls, position: int, name: str) -> "ColumnRef":
        return cls(position, name, name if printable(name) else redaction(position, name))


def printable(name: str) -> bool:
    """Whether intake may quote this name.

    ``str.isidentifier`` is the conservative test: it accepts ``ticket_no`` and
    ``маршрут`` and rejects a card number, an ISO timestamp, ``T-2201`` and
    ``Chistye Prudy`` — the shapes a headerless extract puts in row one. A genuine
    header that is not word-like is described by shape instead, which costs a little
    readability and cannot leak a cell.
    """
    return bool(name) and len(name) <= MAX_COLUMN_NAME_LENGTH and name.isidentifier()


def redaction(position: int, name: str) -> str:
    return f"<column {position}: {len(name)} {signature(name)}>"


def describe(name: str) -> str:
    """A safe rendering for a name whose position is unknown, such as one a profile names."""
    return name if printable(name) else f"<declared column: {len(name)} {signature(name)}>"


def positional_names(count: int) -> tuple[str, ...]:
    """Names for a file declared to have no header; they are word-like by construction."""
    return tuple(f"{POSITIONAL_PREFIX}{index}" for index in range(1, count + 1))


def labels(columns: tuple[ColumnRef, ...]) -> list[str]:
    return [column.label for column in columns]
