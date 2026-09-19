"""FastAPI backend for the Moscow tram graph.

Serves the committed graph in data/ as a read-only API, plus a passthrough to the
upstream Overpass server for anything the graph does not answer. The Vite
production build in app/frontend/dist is mounted at / so one uvicorn command
gives a working app; in development the frontend runs on its own port and reaches
this API through the CORS middleware below.
"""

from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

import overpass
import tramgraph

# The Vite build output, not the source tree: app/frontend holds .jsx and a
# config that a browser cannot execute. Absent until `npm run build` has run.
FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"


@asynccontextmanager
async def lifespan(app: FastAPI):
    tramgraph.get_graph()  # parse the graph once, not per request
    yield


app = FastAPI(
    title="Moscow tram graph API",
    description="Routable graph of the Moscow tram network, extracted from OpenStreetMap.",
    lifespan=lifespan,
)

# In production the frontend is served from the same origin, but the Vite dev
# server runs on its own port -- and a teammate opening a file off the filesystem
# should not have to think about CORS either.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class OverpassRequest(BaseModel):
    query: str = Field(..., description="Overpass QL")


@app.get("/api/health")
async def health():
    g = tramgraph.get_graph()
    reachable, detail = await overpass.check_status()
    return {
        "status": "ok",
        "graph": {
            "stops": len(g.stops),
            "edges": len(g.edges),
            "generated_at": g.metadata.get("generated_at"),
            "osm_data_timestamp": g.metadata.get("osm_data_timestamp"),
        },
        "overpass": {"reachable": reachable, "url": overpass.status_url(), "detail": detail},
    }


@app.get("/api/stats")
async def stats():
    return tramgraph.get_graph().stats()


@app.get("/api/routes")
async def routes():
    g = tramgraph.get_graph()
    return [
        {"ref": r["ref"], "stop_count": len(r["stop_ids"]),
         "length_m": r["length_m"], "component": r["component"]}
        for r in g.routes.values()
    ]


@app.get("/api/routes/{ref}")
async def route_detail(ref: str):
    g = tramgraph.get_graph()
    route = g.routes.get(ref)
    if route is None:
        raise HTTPException(
            404,
            f"unknown route ref {ref!r}; see /api/routes for the 38 refs "
            "(73 is the PTv2 route-relation count, one per direction; /api/stats "
            "reports it as route_relations)",
        )
    return {
        "ref": route["ref"],
        "stops": [g.stops[nid] for nid in route["stop_ids"]],
        "edges": route["edges"],
        "length_m": route["length_m"],
    }


@app.get("/api/stops")
async def stops(q: str | None = None, limit: int = Query(50, ge=1, le=1000)):
    return tramgraph.get_graph().search_stops(q, limit)


@app.get("/api/stops/{stop_id}")
async def stop_detail(stop_id: int):
    g = tramgraph.get_graph()
    stop = g.stops.get(stop_id)
    if stop is None:
        raise HTTPException(404, f"unknown stop id {stop_id}; ids are OSM stop_position node ids")
    return {**stop, "neighbours": g.neighbours(stop_id)}


@app.get("/api/edges")
async def edges(route: str | None = None):
    g = tramgraph.get_graph()
    if route is None:
        return g.edges
    if route not in g.routes:
        raise HTTPException(404, f"unknown route ref {route!r}; see /api/routes")
    return g.routes[route]["edges"]


@app.get("/api/graph.geojson")
async def graph_geojson(route: str | None = None):
    g = tramgraph.get_graph()
    if route is not None and route not in g.routes:
        raise HTTPException(404, f"unknown route ref {route!r}; see /api/routes")
    return g.route_geojson(route)


@app.get("/api/path")
async def path(
    from_: int = Query(..., alias="from", description="source stop id"),
    to: int = Query(..., description="target stop id"),
):
    # Unreachable is an answer, not an error: the network really is in two pieces.
    return tramgraph.get_graph().shortest_path(from_, to)


@app.post("/api/overpass")
async def overpass_proxy(body: OverpassRequest):
    limit = overpass.max_query_chars()
    if len(body.query) > limit:
        return JSONResponse(
            {"error": f"query is {len(body.query)} characters, limit is {limit}"},
            status_code=400,
        )
    try:
        return await overpass.run_query(body.query)
    except overpass.OverpassError as exc:
        return JSONResponse({"error": str(exc)}, status_code=502)


# Mounted last: a mount at / swallows everything that did not match above.
# Guarded, so uvicorn still starts when the frontend has not been built yet.
if FRONTEND_DIST.is_dir():
    app.mount("/", StaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")
