"""Overpass contracts, independent of any HTTP library.

Overpass has five response shapes and only one of them is the obvious one, so the
result type below keeps `remark` separate from the payload: a query that hits its
own `[timeout:]` answers HTTP 200 with valid JSON and a `remark` key holding
*partial* results. Dropping the key is the easiest way to ship wrong numbers.
See `docs/overpass-api.md`.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


class OverpassError(RuntimeError):
    """The upstream Overpass server did not answer with a usable result."""


class OverpassQueryTooLongError(OverpassError):
    """The query exceeds the configured budget, so it is rejected before it is sent.

    The instance is shared by the whole team; an oversized query is refused locally
    rather than spending a slot of the dispatcher's time pool on it.
    """


@dataclass(frozen=True, slots=True)
class OverpassStatus:
    url: str
    reachable: bool
    detail: str | None = None


@dataclass(frozen=True, slots=True)
class OverpassResult:
    payload: Mapping[str, Any]
    remark: str | None = None
