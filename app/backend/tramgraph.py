"""Loading and querying the Moscow tram graph.

Everything here operates on the node-link JSON in data/, which keeps stop ids as
ints; the GraphML copy of the same graph stringifies them, which then leaks into
every id comparison. The GeoJSON is loaded alongside it purely for the per-edge
track polylines -- the graph itself carries no geometry beyond stop coordinates.
"""

from __future__ import annotations

import json
import os
import statistics
from collections import Counter
from pathlib import Path

import networkx as nx

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_GRAPH_JSON = REPO_ROOT / "data" / "tram_graph.json"
DEFAULT_GRAPH_GEOJSON = REPO_ROOT / "data" / "tram_graph.geojson"


def route_sort_key(ref: str):
    """Sort refs 1, 2, 10 rather than 1, 10, 2, with non-numeric ones last.

    Same ordering scripts/fetch_tram_graph.py uses, so refs read the same way in
    the API as they do in the committed CSVs.
    """
    return (0, int(ref), "") if ref.isdigit() else (1, 0, ref)


def sorted_routes(refs) -> list[str]:
    return sorted(set(refs), key=route_sort_key)


class TramGraph:
    """The graph plus the indexes the API needs, built once at startup."""

    def __init__(self, doc: dict, geo: dict | None = None):
        self.metadata: dict = doc.get("metadata", {})
        # multigraph=False is not the default: node_link_graph assumes a multigraph
        # unless the document says otherwise, and this one only sets "directed".
        self.G: nx.DiGraph = nx.node_link_graph(doc, edges="links", multigraph=False)
        self.UG = self.G.to_undirected(as_view=True)

        self.stops: dict[int, dict] = {
            nid: {"id": nid, "name": d["name"], "lat": d["lat"], "lon": d["lon"],
                  "routes": list(d["routes"])}
            for nid, d in self.G.nodes(data=True)
        }
        self.edges: list[dict] = [
            {"source": a, "target": b, "length_m": d["length_m"], "routes": list(d["routes"])}
            for a, b, d in self.G.edges(data=True)
        ]

        # Components are ranked by size so component 0 is always the main network.
        components = sorted(nx.connected_components(self.UG), key=len, reverse=True)
        self.components: list[set[int]] = [set(c) for c in components]
        self.component_of: dict[int, int] = {
            nid: i for i, comp in enumerate(self.components) for nid in comp
        }

        self.routes: dict[str, dict] = self._index_routes()

        # Track polylines, keyed by directed edge; used for /api/path geometry.
        self.geojson: dict | None = geo
        self.edge_geometry: dict[tuple[int, int], list[list[float]]] = {}
        if geo:
            for feature in geo.get("features", []):
                if feature.get("geometry", {}).get("type") != "LineString":
                    continue
                props = feature["properties"]
                key = (props["source"], props["target"])
                self.edge_geometry[key] = feature["geometry"]["coordinates"]

    def _index_routes(self) -> dict[str, dict]:
        stops_by_route: dict[str, set[int]] = {}
        edges_by_route: dict[str, list[dict]] = {}
        for stop in self.stops.values():
            for ref in stop["routes"]:
                stops_by_route.setdefault(ref, set()).add(stop["id"])
        for edge in self.edges:
            for ref in edge["routes"]:
                edges_by_route.setdefault(ref, []).append(edge)

        routes: dict[str, dict] = {}
        for ref in sorted(stops_by_route, key=route_sort_key):
            stop_ids = stops_by_route[ref]
            edges = edges_by_route.get(ref, [])
            comps = {self.component_of[nid] for nid in stop_ids}
            routes[ref] = {
                "ref": ref,
                "stop_ids": sorted(stop_ids),
                "edges": edges,
                "length_m": round(sum(e["length_m"] for e in edges), 1),
                # A route lives in one component in practice; report the main one
                # rather than pretending a split route is impossible.
                "component": min(comps) if comps else -1,
            }
        return routes

    def stats(self) -> dict:
        lengths = [e["length_m"] for e in self.edges]
        degrees = Counter(dict(self.UG.degree()).values())
        component_entries = []
        for comp in self.components:
            refs = {ref for nid in comp for ref in self.stops[nid]["routes"]}
            component_entries.append({"size": len(comp), "routes": sorted_routes(refs)})
        return {
            "stops": len(self.stops),
            "edges": len(self.edges),
            "routes": len(self.routes),
            # 73 route relations in OSM, but PTv2 maps each direction separately,
            # so they collapse to ~38 distinct refs.
            "route_relations": self.metadata.get("routes_used"),
            "total_length_km": round(sum(lengths) / 1000, 2),
            "components": component_entries,
            "degree_histogram": {str(k): degrees[k] for k in sorted(degrees)},
            "segment_length_m": {
                "min": round(min(lengths), 1),
                "median": round(statistics.median(lengths), 1),
                "mean": round(statistics.mean(lengths), 1),
                "max": round(max(lengths), 1),
            },
        }

    def search_stops(self, q: str | None, limit: int) -> list[dict]:
        if not q:
            return list(self.stops.values())[:limit]
        # casefold, not lower: the names are Cyrillic and mixed case.
        needle = q.casefold()
        out = []
        for stop in self.stops.values():
            if needle in stop["name"].casefold():
                out.append(stop)
                if len(out) >= limit:
                    break
        return out

    def neighbours(self, stop_id: int) -> list[dict]:
        out = []
        for nbr in self.G.successors(stop_id):
            d = self.G[stop_id][nbr]
            out.append({"id": nbr, "name": self.stops[nbr]["name"],
                        "length_m": d["length_m"], "routes": list(d["routes"]),
                        "direction": "out"})
        for nbr in self.G.predecessors(stop_id):
            d = self.G[nbr][stop_id]
            out.append({"id": nbr, "name": self.stops[nbr]["name"],
                        "length_m": d["length_m"], "routes": list(d["routes"]),
                        "direction": "in"})
        return out

    def route_geojson(self, ref: str | None) -> dict:
        """The GeoJSON FeatureCollection, optionally cut down to one route."""
        if self.geojson is None:
            return {"type": "FeatureCollection", "metadata": self.metadata, "features": []}
        if ref is None:
            return self.geojson
        features = [f for f in self.geojson["features"] if ref in f["properties"].get("routes", [])]
        return {"type": "FeatureCollection",
                "metadata": {**self.geojson.get("metadata", {}), "filtered_to_route": ref},
                "features": features}

    def shortest_path(self, source: int, target: int) -> dict:
        empty = {"found": False, "reason": None, "stops": [], "total_length_m": 0.0,
                 "geometry": [], "routes": []}
        for label, nid in (("from", source), ("to", target)):
            if nid not in self.stops:
                return {**empty, "reason": f"unknown stop id {nid} in '{label}'"}

        if self.component_of[source] != self.component_of[target]:
            # Two components with no rail between them -- see docs/tram-graph.md.
            return {**empty, "reason": (
                f"{self.stops[source]['name']} and {self.stops[target]['name']} are in "
                "different parts of the tram network; there is no track connecting them")}

        try:
            path = nx.shortest_path(self.G, source, target, weight="length_m")
        except nx.NetworkXNoPath:
            return {**empty, "reason": (
                f"no route from {self.stops[source]['name']} to {self.stops[target]['name']} "
                "in the direction of travel; the track exists but only the other way round")}

        stops = [self.stops[nid] for nid in path]
        total = 0.0
        routes: set[str] = set()
        geometry: list[list[float]] = []
        for a, b in zip(path, path[1:]):
            d = self.G[a][b]
            total += d["length_m"]
            routes.update(d["routes"])
            coords = self.edge_geometry.get((a, b))
            if coords is None:
                coords = [[self.stops[a]["lon"], self.stops[a]["lat"]],
                          [self.stops[b]["lon"], self.stops[b]["lat"]]]
            if geometry and geometry[-1] == coords[0]:
                coords = coords[1:]
            geometry.extend(coords)
        if not geometry and stops:
            geometry = [[stops[0]["lon"], stops[0]["lat"]]]

        return {"found": True, "reason": None, "stops": stops,
                "total_length_m": round(total, 1), "geometry": geometry,
                "routes": sorted_routes(routes)}


def load(graph_path: Path | None = None, geojson_path: Path | None = None) -> TramGraph:
    graph_path = graph_path or Path(os.getenv("TRAM_GRAPH_JSON", DEFAULT_GRAPH_JSON))
    geojson_path = geojson_path or Path(os.getenv("TRAM_GRAPH_GEOJSON", DEFAULT_GRAPH_GEOJSON))
    doc = json.loads(graph_path.read_text(encoding="utf-8"))
    geo = json.loads(geojson_path.read_text(encoding="utf-8")) if geojson_path.exists() else None
    return TramGraph(doc, geo)


_graph: TramGraph | None = None


def get_graph() -> TramGraph:
    """The process-wide graph. Loaded by the app's lifespan; this is the fallback
    for anything that reaches a handler without the lifespan having run."""
    global _graph
    if _graph is None:
        _graph = load()
    return _graph
