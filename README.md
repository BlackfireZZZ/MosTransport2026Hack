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

One thing to know before writing a client: **Overpass has five response shapes and
only one is the obvious one.** A query that hits its own timeout comes back as
HTTP 200 with valid JSON and quietly fewer elements than exist — the only signal is
a `remark` key. Malformed QL is HTTP 400 with an HTML body, and an overloaded or
over-claimed request is HTTP 504, also HTML. A copy-paste client that handles all of
them is in the API doc; do not write one from scratch.

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

## Running it

The app is one container: FastAPI serves the JSON API and the built React SPA from
the same origin.

```bash
docker compose up --build          # http://localhost:8080
APP_PORT=8099 docker compose up -d # if 8080 is taken
```

`data/` is bind-mounted read-only, so re-running the extraction does not need an
image rebuild. Verified with Podman 6.1 on arm64; the image is 224 MB and runs as a
non-root uid.

The Overpass server is **not** part of this stack — it is a separate deployment
with its own 12 GB database. Point the app at a different one with
`OVERPASS_URL=... docker compose up`.

Without containers, two processes:

```bash
cd app/backend  && pip install -r requirements.txt && uvicorn main:app --port 8010 --reload
cd app/frontend && npm install && npm run dev       # http://localhost:5173, proxies /api to 8010
```

Port 8010 rather than the conventional 8000, which is commonly occupied.

## Layout

```
app/backend/    FastAPI: graph API + an Overpass passthrough
app/frontend/   React + Vite + TypeScript map UI
app/Dockerfile  two stages -- node builds the SPA, python serves it with the API
docker-compose.yml
docs/           API reference, deployment, dataset schemas
infra/          docker-compose for the Overpass server (separate deployment)
scripts/        extraction scripts, stdlib-only, each runnable on its own
data/           generated datasets, committed so nobody has to re-run the extraction
```

Data is OpenStreetMap, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) —
attribution required on anything published from it.
