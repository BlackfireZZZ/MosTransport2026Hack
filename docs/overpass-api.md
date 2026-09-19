# Overpass API

Self-hosted [Overpass API](https://wiki.openstreetmap.org/wiki/Overpass_API) over
OpenStreetMap data for Moscow and Moscow oblast. Use it instead of the public
instances at `overpass-api.de` — those rate-limit aggressively and will throttle a
team hammering them from one address during a hackathon.

| | |
|---|---|
| Interpreter | `http://204.168.155.177/api/interpreter` |
| Status | `http://204.168.155.177/api/status` |
| Coverage | Central Federal District extract — Moscow and Moscow oblast in full |
| Freshness | Geofabrik daily diffs, polled hourly |
| Auth | none |
| Transport | HTTP only, no TLS |
| Licence | OpenStreetMap contributors, [ODbL 1.0](https://opendatacommons.org/licenses/odbl/) — attribution required if you publish anything derived from it |

Deployment and operations live in [deployment.md](deployment.md).

## Making a request

The query goes in a `data` parameter, by GET or POST. Use POST for anything long —
some clients and proxies truncate long query strings.

```bash
curl -G http://204.168.155.177/api/interpreter --data-urlencode '
[out:json][timeout:60];
area["name"="Москва"]["admin_level"="4"]->.moscow;
node["station"="subway"](area.moscow);
out tags;
'
```

```python
import requests

OVERPASS = "http://204.168.155.177/api/interpreter"

def query(ql: str, timeout: int = 60) -> dict:
    r = requests.post(OVERPASS, data={"data": ql}, timeout=timeout + 30)
    r.raise_for_status()
    return r.json()   # raises on the HTML error page described below
```

The query language itself is Overpass QL; the
[QL reference](https://wiki.openstreetmap.org/wiki/Overpass_API/Overpass_QL) and
[overpass turbo](https://overpass-turbo.eu/) (point it at this server under
Settings) are the places to learn it.

## Limits

These are the dispatcher settings on this instance, not Overpass defaults.

| Limit | Value | Meaning |
|---|---|---|
| `[timeout:]` ceiling | 300 s | largest value a single query may ask for |
| Time pool | 3600 units | shared across all in-flight queries |
| `[maxsize:]` default | 512 MiB | memory one query may claim |
| Space pool | 2 GiB | shared across all in-flight queries |
| Concurrency | 4 | queries running at once, server-wide |

The host has 2 vCPU and 3.8 GB RAM, so the ceiling is the whole team's, not each
person's. Two practical consequences:

- **Ask for the timeout you need, not the maximum.** `[timeout:]` is a claim against
  the shared pool for the duration of the query. Four people each asking
  `[timeout:300]` out of habit will shed each other's requests.
- **Filter by area or bbox before filtering by tag.** `node["highway"="bus_stop"]`
  unbounded scans the whole extract; bounded by a bbox it is near-instant.

## Errors

Overpass reports runtime errors as an **HTML page with HTTP 200**, so a bare
`response.json()` raises a decode error rather than telling you what went wrong.
Parse out the message before reporting failures:

```python
import re

def query(ql: str, timeout: int = 60) -> dict:
    r = requests.post(OVERPASS, data={"data": ql}, timeout=timeout + 30)
    r.raise_for_status()
    body = r.text
    if not body.lstrip().startswith("{"):
        m = re.search(r"runtime error[^<]*", body)
        raise RuntimeError(m.group(0) if m else body[:300])
    return json.loads(body)
```

| Message | Cause | Fix |
|---|---|---|
| `request_read_and_idx::timeout` … `server is probably too busy` | the query claimed more of the time or space pool than was free, and was shed | lower `[timeout:]`, narrow the query, or retry — it is not a hard failure |
| `runtime error: Query timed out` | the query genuinely exceeded its own `[timeout:]` | bound it by area or bbox before filtering on tags |
| `request_read_and_idx::duplicate_query` | should not occur — duplicate blocking is off | if it appears, `OVERPASS_ALLOW_DUPLICATE_QUERIES` has been reset to something other than `yes` |

Transient `request_read_and_idx::timeout` for a minute or two after a server
restart is expected: the area index rebuilds on startup and briefly blocks
readers. Retry rather than treating it as an outage.

`GET /api/status` reports the live picture — free slots, pool usage, and a
`load shedded requests` counter that rises when queries are being rejected for
asking too much.

## Recipes

Snippets below assume the area prelude:

```
area["name"="Москва"]["admin_level"="4"]->.moscow;
```

**Stops of one mode**

```
[out:json][timeout:60];
area["name"="Москва"]["admin_level"="4"]->.moscow;
node["public_transport"="stop_position"]["tram"="yes"](area.moscow);
out body;
```

**Routes with their members resolved** — relations, then the nodes and ways they
reference, then the geometry of those ways. This is the shape
[fetch_tram_graph.py](../scripts/fetch_tram_graph.py) uses.

```
[out:json][timeout:300];
area["name"="Москва"]["admin_level"="4"]->.moscow;
relation["type"="route"]["route"="tram"](area.moscow)->.routes;
.routes out body;
node(r.routes);
out body;
way(r.routes);
out body;
node(w);
out skel qt;
```

**Counting before downloading** — cheap way to size a query before running it for
real:

```
[out:json][timeout:60];
area["name"="Москва"]["admin_level"="4"]->.moscow;
relation["type"="route"]["route"~"^(bus|tram|trolleybus|subway)$"](area.moscow);
out count;
```

**A bbox instead of an area** — faster, and works without the area index:

```
node["highway"="bus_stop"](55.1,36.0,56.9,39.0);
```

Bounding box order is `(south, west, north, east)`. The one above covers Moscow
and the oblast.

## What the data looks like

Moscow public transport is mapped to the
[PTv2 scheme](https://wiki.openstreetmap.org/wiki/Public_transport), which is worth
knowing before writing queries against it:

- A route relation is **one direction** of one route. A there-and-back service is
  two relations, usually collected in a `type=route_master`.
- Members carry roles. `stop`, `stop_entry_only` and `stop_exit_only` are
  `stop_position` nodes **on the track itself**; `platform*` is where passengers
  wait, beside the track. The two are separate objects for the same stop.
- Members with an empty role are the track ways, in travel order. Individual ways
  may be stored reversed, so orientation has to be worked out by matching endpoints.

Because stop nodes sit on the track, distance between consecutive stops can be
measured along the real geometry instead of as a straight line — see
[tram-graph.md](tram-graph.md).

Counts as of the 2026-09-18 extract:

| | |
|---|---|
| Route relations in Moscow | 3387 (bus 2269, train 1006, tram 73, subway 34, trolleybus 5) |
| Bus stops and stop positions, Moscow + oblast | 49 696 |
| Metro stations, Moscow | 279 |
