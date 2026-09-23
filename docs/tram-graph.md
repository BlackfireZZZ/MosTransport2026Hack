# Moscow tram graph

A routable graph of the Moscow tram network, extracted from our
[Overpass API](overpass-api.md) by
[`scripts/fetch_tram_graph.py`](../scripts/fetch_tram_graph.py).

- **Nodes** — tram stops, keyed by OSM `stop_position` node id.
- **Edges** — directed, one per ordered pair of consecutive stops on at least one
  route. Two routes sharing a stretch of track share the edge; the `routes`
  attribute lists all of them.
- **Edge length** — measured **along the rails**, not as a straight line. PTv2 puts
  `stop_position` nodes on the track ways themselves, so the track is walked node
  by node between two stops and the per-segment distances summed.

## Regenerating

```bash
python3 scripts/fetch_tram_graph.py --out-dir data
```

Use the repository's Python 3.13; only the standard library is needed, with no
package installation. The script and the API share the graph validation and
publication helpers in `backend/app/infrastructure/`. Useful flags:
`--area` / `--admin-level` to target somewhere else,
`--api-url` to point at a different instance.

An HTTP-200 response carrying any `remark` is rejected, as are malformed payloads
and missing referenced nodes/ways. Such responses do not modify the current set.
Tests use mocked transport and committed data, never live Overpass load.

## Versioned publication and rollback

New exports produce `data/graph-store/tram_graph.manifest.json` and immutable
`data/graph-store/snapshots/<version>/` directories. Each snapshot includes the
five files below plus its manifest. The manifest schema is version 1; `source`
contains common extraction metadata (including source timestamp), `files` maps
the five fixed names to `sha256` and `size_bytes`, and `version` is the SHA-256
of the canonical manifest body without its own version field.

All graph values, geometry endpoints, metadata, CSV and GraphML projections must
match before activation. Files are staged and synchronized before the active
manifest changes atomically. First publication atomically installs the whole
store so an interrupted migration cannot disable the old flat files. Once a
store exists, missing or corrupt manifests/files are errors; the reader does not
silently select stale legacy files. See [ADR-0004](decisions/0004-atomic-graph-snapshots.md)
for local POSIX filesystem assumptions and the final-fsync durability limitation.

The existing `TRAM_GRAPH_JSON`/`TRAM_GRAPH_GEOJSON` settings and repository
constructor still work. With conventional filenames in one directory, the API
discovers its `graph-store/`, validates every file hash and loads one complete
snapshot. Before first publication, the existing committed flat files work as
before. Explicit alternate filenames load the supplied legacy pair directly.
The API caches its first valid network; restart API processes after activation
to serve the new snapshot. No public graph API fields change.

List saved versions and activate one without an Overpass request:

```bash
ls data/graph-store/snapshots
python3 scripts/fetch_tram_graph.py --out-dir data --rollback <version>
```

Rollback revalidates the selected set and changes the manifest; no versions are
deleted. Failed writes before the commit point leave the prior selection intact.
Interrupted processes can leave staging directories or unselected sealed sets;
these are never read as active. Inspect them before any manual cleanup.

To load the active JSON with an external tool, capture the manifest once:

```python
import json
from pathlib import Path

store = Path("data/graph-store")
manifest = json.loads((store / "tram_graph.manifest.json").read_text())
snapshot = store / "snapshots" / manifest["version"]
doc = json.loads((snapshot / "tram_graph.json").read_text())
```

For checksum/projection verification as well, use
`app.infrastructure.graph_artifacts.load_active_graph(Path("data"))` from the
backend workspace. Raw readers must verify the declared hashes themselves.

## Files

| File | Format | Use |
|---|---|---|
| `data/tram_graph.graphml` | GraphML | `networkx.read_graphml`, Gephi, igraph, yEd |
| `data/tram_graph.json` | node-link JSON | `networkx.node_link_graph`, or read it directly |
| `data/tram_graph.geojson` | GeoJSON | drop on a map — stops as points, tracks as lines with real geometry |
| `data/tram_stops.csv` | CSV | spreadsheets, pandas |
| `data/tram_edges.csv` | CSV | spreadsheets, pandas |

These paths describe the committed legacy set. After regeneration, use the
selected snapshot directory instead of the legacy `data/` prefix; the old flat
files are retained, not refreshed individually.

GraphML and node-link JSON carry the same graph. GeoJSON additionally carries the
full track polyline per edge, which is what makes it several times larger.

### Attributes

Node:

| Field | Type | |
|---|---|---|
| `id` / node id | int | OSM node id of the `stop_position` |
| `name` | string | stop name; falls back to the adjacent platform's name, then to `node/<id>` |
| `lat`, `lon` | float | WGS84 |
| `routes` | list / `;`-joined | route refs calling at this stop |

Edge:

| Field | Type | |
|---|---|---|
| `source`, `target` | int | stop node ids, directed |
| `length_m` | float | metres along the track |
| `routes` | list / `;`-joined | route refs using this segment |

Metadata — source, licence, area, the OSM extract timestamp and the extraction
counters — is in the `metadata` object of the JSON and GeoJSON, and in the
GraphML `<desc>` element.

## Loading it

```python
import networkx as nx

G = nx.read_graphml("data/tram_graph.graphml")
print(G.number_of_nodes(), G.number_of_edges())   # 856 919

# shortest path by track distance
path = nx.shortest_path(G, source="1377188043", target="472373305", weight="length_m")
metres = sum(float(G[a][b]["length_m"]) for a, b in zip(path, path[1:]))
print(len(path), round(metres / 1000, 2))         # 77 32.01
# Даниловская мануфактура -> Стадион «Труд» -> ... -> Курский вокзал
```

GraphML node ids are strings. From node-link JSON they stay integers:

```python
import json, networkx as nx

doc = json.load(open("data/tram_graph.json"))
G = nx.node_link_graph(doc, edges="links")
# edge data: {"length_m": 511.2, "routes": ["2", "4", "32"]}
```

Both examples were run against the committed files with networkx 3.6.1. Note the
`edges="links"` argument — without it, networkx 3.x looks for an `edges` key and
returns an empty graph.

Without networkx, both JSON files are a plain adjacency list away from any graph
library.

## The data

From the 2026-09-18 OSM extract:

| | |
|---|---|
| Route relations | 73, all usable |
| Stops | 856 |
| Edges | 919 unique, 2102 route-segments |
| Total track | 377 km |
| Segment length | median 387 m, mean 410 m, range 98–2112 m |
| Measured along the track | 2102 of 2102 segments |

### Two components, on purpose

Undirected, the graph splits into 694 stops and 162 stops with no rail between
them. That is not an extraction artefact — the northern network around
Timiryazevskaya, Bolshaya Akademicheskaya and Ulitsa Kostyakova (routes 6, 10, 15,
21, 23, 27, 28, 29, 30, 31) is physically separate from the rest of the Moscow
system. **Any routing over this graph has to handle an unreachable destination.**

### Other things worth knowing

- Degrees: 665 stops through-running, 136 junctions, 40 termini, 15 of degree 4.
- Directed edges. A stop pair served in both directions appears twice, and the two
  directions can differ in length where the tracks are not parallel.
- 10 stops have no name in OSM and fall back to `node/<id>`. They are real stops,
  just unnamed upstream.
- Route refs are not all numeric — `А`, `1а`, `39а`, `47а`, `т1`, `т2` exist. Sort
  and compare them as strings.
- A stop that is a single place on the ground may be two nodes, one per direction,
  with separate ids and slightly different coordinates. Merge by name and proximity
  if you need the physical stop rather than the stopping point.
