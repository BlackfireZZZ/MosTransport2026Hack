"""Routing over the tram network.

Separated from `tram_graph`, which holds the graph and its indexes. This module
is the one place with an algorithm, and the multimodal graph in the product
concept will only grow it. The dependency runs one way -- routing knows the
network, the network does not know routing -- so there is no import cycle.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass

from app.domain.tram_graph import Coordinate, TramEdge, TramNetwork, TramStop, sorted_refs


@dataclass(frozen=True, slots=True)
class TramPath:
    """The result of a routing request.

    `found=False` with a populated `reason` is a successful answer describing the
    absence of a route, not a failure: the network genuinely has unreachable pairs.
    """

    found: bool
    reason: str | None
    stops: tuple[TramStop, ...]
    total_length_m: float
    geometry: tuple[Coordinate, ...]
    routes: tuple[str, ...]


def absent_path(reason: str) -> TramPath:
    return TramPath(
        found=False, reason=reason, stops=(), total_length_m=0.0, geometry=(), routes=()
    )


def find_path(network: TramNetwork, source: int, target: int) -> TramPath:
    for label, stop_id in (("from", source), ("to", target)):
        if stop_id not in network.stops:
            return absent_path(f"unknown stop id {stop_id} in '{label}'")

    if network.component_of[source] != network.component_of[target]:
        return absent_path(
            f"{network.stops[source].name} and {network.stops[target].name} are in different "
            "parts of the tram network; there is no track connecting them"
        )

    chain = _cheapest_chain(network, source, target)
    if chain is None:
        # Same component, so the track exists; the direction of travel does not.
        return absent_path(
            f"no route from {network.stops[source].name} to {network.stops[target].name} in the "
            "direction of travel; the track exists but only the other way round"
        )

    stops = [network.stops[source]] + [network.stops[edge.target] for edge in chain]
    total = 0.0
    routes: set[str] = set()
    geometry: list[Coordinate] = []
    for edge in chain:
        total += edge.length_m
        routes.update(edge.routes)
        coordinates = list(network.track_coordinates(edge))
        if geometry and coordinates and geometry[-1] == coordinates[0]:
            coordinates = coordinates[1:]
        geometry.extend(coordinates)
    if not geometry:
        geometry = [(stops[0].longitude, stops[0].latitude)]

    return TramPath(
        found=True,
        reason=None,
        stops=tuple(stops),
        total_length_m=round(total, 1),
        geometry=tuple(geometry),
        routes=sorted_refs(routes),
    )

def _cheapest_chain(network: TramNetwork, source: int, target: int) -> list[TramEdge] | None:
    """Dijkstra over `length_m`, returning the edges travelled, or None."""
    if source == target:
        return []
    distances: dict[int, float] = {source: 0.0}
    arrival: dict[int, TramEdge] = {}
    visited: set[int] = set()
    queue: list[tuple[float, int]] = [(0.0, source)]
    while queue:
        distance, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)
        if current == target:
            break
        for edge in network.outgoing.get(current, ()):
            candidate = distance + edge.length_m
            if candidate < distances.get(edge.target, float("inf")):
                distances[edge.target] = candidate
                arrival[edge.target] = edge
                heapq.heappush(queue, (candidate, edge.target))

    if target not in arrival:
        return None
    chain: list[TramEdge] = []
    cursor = target
    while cursor != source:
        edge = arrival[cursor]
        chain.append(edge)
        cursor = edge.source
    chain.reverse()
    return chain
