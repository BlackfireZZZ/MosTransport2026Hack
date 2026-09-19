# MosTransport2026Hack

Working repo for the Moscow transport hackathon: a self-hosted OpenStreetMap data
API, and datasets extracted from it.

## Overpass API

`http://204.168.155.177/api/interpreter`

Covers Moscow and Moscow oblast, refreshed from Geofabrik daily diffs. No auth, no
rate limit beyond 4 concurrent queries server-wide. Use it rather than the public
`overpass-api.de`, which will throttle the whole team from one address.

```bash
curl -G http://204.168.155.177/api/interpreter --data-urlencode '
[out:json][timeout:60];
area["name"="Москва"]["admin_level"="4"]->.moscow;
node["station"="subway"](area.moscow);
out tags;
'
```

- [docs/overpass-api.md](docs/overpass-api.md) — endpoints, limits, error handling,
  query recipes, and how Moscow transport is tagged in OSM
- [docs/deployment.md](docs/deployment.md) — how the server is built and rebuilt

One thing to know before writing a client: **Overpass returns runtime errors as an
HTML page with HTTP 200**, so a bare `.json()` blows up with a decode error instead
of the actual message. Handling is in the API doc.

## Datasets

| Dataset | Docs | Files |
|---|---|---|
| Moscow tram network as a routable graph — 856 stops, 919 edges, 377 km of track | [docs/tram-graph.md](docs/tram-graph.md) | `data/tram_graph.{graphml,json,geojson}`, `data/tram_{stops,edges}.csv` |

Edge lengths follow the real rail geometry rather than straight lines between
stops. Regenerate with:

```bash
python3 scripts/fetch_tram_graph.py --out-dir data
```

Standard library only — no install step.

## Layout

```
docs/       API reference, deployment, dataset schemas
infra/      docker-compose for the Overpass server
scripts/    extraction scripts, stdlib-only, each runnable on its own
data/       generated datasets, committed so nobody has to re-run the extraction
```

Data is OpenStreetMap, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) —
attribution required on anything published from it.
