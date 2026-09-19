"""File-backed implementation of the tram graph port.

The graph is a static committed asset, regenerated wholesale by
`scripts/fetch_tram_graph.py` and never mutated by the API, so it is read from
`data/` instead of PostgreSQL -- see
`docs/decisions/0003-tram-graph-file-repository.md`.

The node-link JSON is the source of truth because it keeps stop ids as ints; the
GraphML copy of the same graph stringifies them, which then leaks into every id
comparison. The GeoJSON is read alongside it purely for the per-edge track
polylines: the graph itself carries no geometry beyond stop coordinates.
"""

import asyncio
import json
from pathlib import Path
from typing import Any

from app.domain.tram_graph import (
    Coordinate,
    GraphMetadata,
    TramEdge,
    TramNetwork,
    TramStop,
)


class TramGraphDataError(RuntimeError):
    """The committed graph files are missing, unreadable or internally inconsistent."""


class FileTramGraphRepository:
    """Parses the committed graph once and hands out the same immutable network.

    Parsing is ~1 MB of JSON, so it runs in a worker thread and is guarded by a lock
    to keep concurrent first requests from parsing it several times over.
    """

    def __init__(self, graph_path: Path, geojson_path: Path) -> None:
        self._graph_path = graph_path
        self._geojson_path = geojson_path
        self._network: TramNetwork | None = None
        self._lock = asyncio.Lock()

    async def get_network(self) -> TramNetwork:
        if self._network is None:
            async with self._lock:
                if self._network is None:
                    self._network = await asyncio.to_thread(self.load)
        return self._network

    def load(self) -> TramNetwork:
        document = self._read_json(self._graph_path)
        metadata = self._read_metadata(document)
        stops = tuple(
            TramStop(
                id=int(node["id"]),
                name=str(node["name"]),
                latitude=float(node["lat"]),
                longitude=float(node["lon"]),
                routes=tuple(str(ref) for ref in node["routes"]),
            )
            for node in document["nodes"]
        )
        known = {stop.id for stop in stops}
        edges: list[TramEdge] = []
        for link in document["links"]:
            source, target = int(link["source"]), int(link["target"])
            if source not in known or target not in known:
                raise TramGraphDataError(
                    f"{self._graph_path}: edge {source}->{target} references an unknown stop"
                )
            edges.append(
                TramEdge(
                    source=source,
                    target=target,
                    length_m=float(link["length_m"]),
                    routes=tuple(str(ref) for ref in link["routes"]),
                )
            )
        return TramNetwork.build(metadata, stops, tuple(edges), self._read_track_geometry())

    def _read_metadata(self, document: dict[str, Any]) -> GraphMetadata:
        raw = document.get("metadata") or {}
        return GraphMetadata(
            source=raw.get("source"),
            license=raw.get("license"),
            area=raw.get("area"),
            osm_data_timestamp=raw.get("osm_data_timestamp"),
            generated_at=raw.get("generated_at"),
            # routes_used counts PTv2 route relations (73, one per direction), which
            # is a different number from the distinct refs the graph exposes.
            route_relations=raw.get("routes_used"),
        )

    def _read_track_geometry(self) -> dict[tuple[int, int], tuple[Coordinate, ...]]:
        """Per-edge polylines along the real track.

        A missing file raises rather than degrading. Both graph files come out of the
        same run of scripts/fetch_tram_graph.py, so one without the other is a broken
        deployment -- and the degraded mode is invisible: every endpoint still answers
        200 with plausible straight-line geometry, and the map quietly draws trams
        through buildings with nothing in the response to say so.
        """
        if not self._geojson_path.exists():
            raise TramGraphDataError(
                f"the tram graph geometry is missing at {self._geojson_path}; it is written "
                "alongside the graph JSON by scripts/fetch_tram_graph.py"
            )
        geometry: dict[tuple[int, int], tuple[Coordinate, ...]] = {}
        for feature in self._read_json(self._geojson_path).get("features", []):
            if feature.get("geometry", {}).get("type") != "LineString":
                continue
            properties = feature["properties"]
            key = (int(properties["source"]), int(properties["target"]))
            geometry[key] = tuple(
                (float(point[0]), float(point[1])) for point in feature["geometry"]["coordinates"]
            )
        return geometry

    @staticmethod
    def _read_json(path: Path) -> dict[str, Any]:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError as error:
            raise TramGraphDataError(f"cannot read the tram graph at {path}: {error}") from error
        try:
            document: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError as error:
            raise TramGraphDataError(f"{path} is not valid JSON: {error}") from error
        return document
