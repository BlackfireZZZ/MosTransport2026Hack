# Moscow tram network — frontend

React + TypeScript + Vite. Renders the tram graph served by the FastAPI backend in
`app/backend` on a MapLibre GL map, with route filtering, stop inspection and
shortest-path routing.

## Running it

The backend and the dev server run side by side. The backend listens on **port 8010**
— *not* 8000, which an unrelated app owns on this machine:

```bash
# terminal 1 — API
cd app/backend
uvicorn main:app --reload --port 8010

# terminal 2 — frontend
cd app/frontend
npm install
npm run dev          # http://localhost:5173
```

`npm run dev` proxies `/api` to the backend, so no host or port is ever hardcoded in
the client — it only ever fetches relative `/api/...` paths.

### Pointing at a different backend

| Variable | Default | Meaning |
| --- | --- | --- |
| `VITE_API_PROXY_TARGET` | `http://127.0.0.1:8010` | Backend origin the dev server proxies `/api` to |
| `VITE_DEV_PORT` | `5173` | Port for the Vite dev server |

Set them inline or in `.env.local` (see `.env.example`):

```bash
VITE_API_PROXY_TARGET=http://127.0.0.1:9001 npm run dev
```

## Production build

```bash
npm run build        # tsc -b && vite build  ->  dist/
```

The backend mounts `app/frontend/dist` at `/`, so after a build a single uvicorn
process serves both the API and the UI on port 8010. `npm run build` type-checks
first and fails the build on any TypeScript error.

## What the app does

- **Map** — every stop and every piece of track from `/api/graph.geojson`, drawn with
  the real OSM geometry over the keyless CARTO Positron basemap.
- **Route filter** — one ref at a time, fetched from `/api/graph.geojson?route=<ref>`;
  the selected route is drawn in tram red over the dimmed rest of the network.
- **Stop inspector** — click any stop (or a search result) for its name, OSM node id,
  coordinates, the routes calling there, and its neighbours. Onward and arriving
  neighbours are listed separately because the graph is directed.
- **Shortest path** — pick two stops, get the route by track distance from
  `/api/path`, drawn on the map with distance and stop count.
- **Provenance** — the OSM extract timestamp from `/api/health` and the ODbL
  attribution, which is a licence condition, not decoration.

## Things about the data the UI has to respect

- **The graph is directed.** 856 stops, 919 edges, 377 km. A→B and B→A are different
  questions: Курский вокзал → Дом Культуры Метростроя is 3 stops and 775 m, the
  reverse is 46 stops and 15.6 km round the Lefortovo loop. The inspector splits
  neighbours by direction and the path panel has a `swap` button for this reason.
- **The network is in two disconnected pieces** (694 and 162 stops). The northern
  section around Timiryazevskaya has no track joining it to the rest. `/api/path`
  answers those requests with `200 {found: false, reason: "..."}` — an answer, not an
  error — and the UI shows it as a plain notice rather than a failure.
- **Route refs are strings, not numbers.** `"А"`, `"1а"`, `"39а"`, `"47а"`, `"т1"`,
  `"т2"` sit alongside `"1"` and `"16"`. `parseInt` would collapse `"1а"` onto `"1"`,
  so `compareRouteRefs` in `src/format.ts` sorts fully-numeric refs numerically and
  everything else as a string after them, mirroring `route_sort_key` in
  `app/backend/tramgraph.py`.
- **`/api/routes` returns 38 refs, not 73.** OSM has 73 route *relations*, but PTv2
  maps each direction as its own relation, so they collapse to 38 distinct refs. The
  73 is reported as `route_relations` in `/api/stats`.
- **10 stops have no name upstream** and arrive as the literal string `node/<id>`.
  Those render as an italic "Unnamed stop" with the OSM id in the tooltip.
- **One physical stop is usually several nodes**, one per direction, with different
  ids and slightly different coordinates. Searching "Войковская" returns four.

## Layout

```
src/
  api.ts                    typed fetch client; every path relative to /api
  types.ts                  response shapes from app/backend
  format.ts                 route-ref sorting, unnamed-stop fallback, units, dates
  App.tsx                   state container and data flow
  index.css                 single stylesheet
  components/
    MapCanvas.tsx           MapLibre map: sources, layers, hover, click
    RoutePanel.tsx          route chips and filter
    StopSearch.tsx          debounced /api/stops search
    PathPanel.tsx           from/to pickers, results, the no-path notice
    StopInspector.tsx       stop detail overlay
    Provenance.tsx          dataset timestamps and ODbL attribution
    TopBar.tsx              health indicator
```

### One non-obvious build detail

maplibre-gl locates its web worker with `new URL('./maplibre-gl-worker.mjs',
import.meta.url)`. Neither Vite's dep pre-bundling nor the production build preserves
that base, and when the worker 404s **maplibre fails silently** — the canvas, controls
and attribution all appear and nothing is ever painted, with no console error. The
`maplibre-worker-assets` plugin in `vite.config.ts` copies the worker and its shared
chunk out of `node_modules` to a fixed unhashed path in both dev and build, and
`MapCanvas.tsx` calls `setWorkerUrl()` to point at them. The two files must stay
adjacent: the worker imports `./maplibre-gl-shared.mjs` relatively.

## Attribution

Data © OpenStreetMap contributors, ODbL 1.0. Basemap © CARTO.
