"""API tests. The upstream Overpass server is always mocked -- it is a shared
hackathon box and tests must not depend on it being up."""

from urllib.parse import quote

import httpx
import pytest
from fastapi.testclient import TestClient

import main
import overpass
import tramgraph

OVERPASS_HTML_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<html><body>
<p><strong style="color:#FF0000">Error</strong>: line 3: parse error: Unknown type "nodz" </p>
<p>runtime error: Query timed out in "query" at line 3 after 60 seconds.</p>
</body></html>"""

# The same page shape, but carrying only the <strong>-wrapped parse error: no
# "runtime error" line to fall back on.
OVERPASS_HTML_PARSE_ERROR = """<?xml version="1.0" encoding="UTF-8"?>
<html><body>
<p><strong style="color:#FF0000">Error</strong>: line 3: parse error: Unknown type "nodz" </p>
</body></html>"""


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


@pytest.fixture(scope="module")
def graph():
    return tramgraph.get_graph()


@pytest.fixture
def mock_overpass(monkeypatch):
    """Point overpass.client at an httpx.MockTransport returning `handler`."""
    def install(handler):
        def factory(timeout):
            return httpx.AsyncClient(transport=httpx.MockTransport(handler), timeout=timeout)
        monkeypatch.setattr(overpass, "client", factory)
    return install


def test_health(client, mock_overpass):
    mock_overpass(lambda request: httpx.Response(200, text="Connected as: 1\n"))
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert body["graph"]["stops"] == 856
    assert body["graph"]["edges"] == 919
    assert body["graph"]["osm_data_timestamp"]
    assert body["graph"]["generated_at"]
    assert body["overpass"] == {"reachable": True, "url": overpass.status_url(), "detail": None}


def test_health_survives_dead_overpass(client, mock_overpass):
    def boom(request):
        raise httpx.ConnectError("connection refused", request=request)
    mock_overpass(boom)
    resp = client.get("/api/health")
    assert resp.status_code == 200
    overpass_status = resp.json()["overpass"]
    assert overpass_status["reachable"] is False
    assert "ConnectError" in overpass_status["detail"]


def test_stats(client):
    body = client.get("/api/stats").json()
    assert body["stops"] == 856
    assert body["edges"] == 919
    assert body["total_length_km"] == pytest.approx(377.0, abs=0.5)
    assert [c["size"] for c in body["components"]] == [694, 162]
    assert "6" in body["components"][1]["routes"]
    assert sum(body["degree_histogram"].values()) == 856
    seg = body["segment_length_m"]
    assert seg["min"] < seg["median"] <= seg["mean"] < seg["max"]


def test_routes_sorted_naturally(client):
    body = client.get("/api/routes").json()
    refs = [r["ref"] for r in body]
    assert refs[:3] == ["1", "2", "4"]
    assert refs.index("10") > refs.index("2")
    assert refs.index("А") > refs.index("50")
    assert all(r["stop_count"] > 0 and r["length_m"] > 0 for r in body)
    assert {r["component"] for r in body} == {0, 1}


@pytest.mark.parametrize("ref", ["1", "А", "т1", "39а"])
def test_route_detail(client, ref):
    resp = client.get(f"/api/routes/{quote(ref)}")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["ref"] == ref
    assert body["stops"] and body["edges"]
    assert all(ref in s["routes"] for s in body["stops"])
    assert all(ref in e["routes"] for e in body["edges"])
    assert body["length_m"] == pytest.approx(sum(e["length_m"] for e in body["edges"]), abs=0.5)


def test_route_unknown(client):
    resp = client.get("/api/routes/999")
    assert resp.status_code == 404
    assert "999" in resp.json()["detail"]


def test_stops_search(client):
    body = client.get("/api/stops", params={"q": "курский"}).json()
    assert body
    assert all("курский" in s["name"].casefold() for s in body)
    assert set(body[0]) == {"id", "name", "lat", "lon", "routes"}
    assert len(client.get("/api/stops").json()) == 50
    assert len(client.get("/api/stops", params={"limit": 3}).json()) == 3


def test_stop_detail(client, graph):
    stop_id = 472373305  # Курский вокзал
    body = client.get(f"/api/stops/{stop_id}").json()
    assert body["name"] == "Курский вокзал"
    assert body["neighbours"]
    directions = {n["direction"] for n in body["neighbours"]}
    assert directions <= {"in", "out"}
    for n in body["neighbours"]:
        assert n["id"] in graph.stops
        assert n["length_m"] > 0


def test_stop_unknown(client):
    resp = client.get("/api/stops/1")
    assert resp.status_code == 404
    assert "1" in resp.json()["detail"]


def test_edges(client):
    assert len(client.get("/api/edges").json()) == 919
    filtered = client.get("/api/edges", params={"route": "т1"}).json()
    assert filtered and all("т1" in e["routes"] for e in filtered)
    assert client.get("/api/edges", params={"route": "nope"}).status_code == 404


def test_geojson(client):
    body = client.get("/api/graph.geojson").json()
    assert body["type"] == "FeatureCollection"
    assert len(body["features"]) == 856 + 919
    one = client.get("/api/graph.geojson", params={"route": "А"}).json()
    assert 0 < len(one["features"]) < len(body["features"])
    assert all("А" in f["properties"]["routes"] for f in one["features"])
    lines = [f for f in one["features"] if f["geometry"]["type"] == "LineString"]
    assert lines and len(lines[0]["geometry"]["coordinates"]) >= 2


def test_path(client):
    body = client.get("/api/path", params={"from": 1377188043, "to": 472373305}).json()
    assert body["found"] is True
    assert body["reason"] is None
    assert body["stops"][0]["id"] == 1377188043
    assert body["stops"][-1]["name"] == "Курский вокзал"
    assert body["total_length_m"] == pytest.approx(32014, abs=50)
    assert len(body["geometry"]) > len(body["stops"])
    assert all(len(c) == 2 for c in body["geometry"])
    assert body["routes"]


def test_path_across_components(client, graph):
    a = sorted(graph.components[0])[0]
    b = sorted(graph.components[1])[0]
    resp = client.get("/api/path", params={"from": a, "to": b})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert body["stops"] == [] and body["geometry"] == []
    assert "different parts" in body["reason"]


def test_path_unknown_stop(client):
    resp = client.get("/api/path", params={"from": 1, "to": 472373305})
    assert resp.status_code == 200
    body = resp.json()
    assert body["found"] is False
    assert "unknown stop id 1" in body["reason"]


def test_overpass_proxy(client, mock_overpass):
    seen = {}

    def handler(request):
        seen["body"] = request.content.decode()
        return httpx.Response(200, json={"elements": [{"id": 1}]})

    mock_overpass(handler)
    resp = client.post("/api/overpass", json={"query": "[out:json];node(1);out;"})
    assert resp.status_code == 200
    assert resp.json() == {"elements": [{"id": 1}]}
    assert "data=" in seen["body"]


def test_overpass_html_error_is_unwrapped(client, mock_overpass):
    # HTTP 200 with an HTML body is how Overpass reports runtime errors.
    mock_overpass(lambda request: httpx.Response(200, text=OVERPASS_HTML_ERROR))
    resp = client.post("/api/overpass", json={"query": "[out:json];nodz(1);out;"})
    assert resp.status_code == 502
    error = resp.json()["error"]
    assert "Query timed out" in error
    # Both errors on the page survive; keeping only the first loses half of it.
    assert 'parse error: Unknown type "nodz"' in error


def test_overpass_parse_error_without_runtime_error(client, mock_overpass):
    # A page whose only message is the <strong>-wrapped parse error: matching
    # around the markup collapses this one to the useless string "Error".
    mock_overpass(lambda request: httpx.Response(200, text=OVERPASS_HTML_PARSE_ERROR))
    resp = client.post("/api/overpass", json={"query": "[out:json];nodz(1);out;"})
    assert resp.status_code == 502
    error = resp.json()["error"]
    assert error != "Error"
    assert 'line 3: parse error: Unknown type "nodz"' in error
    assert "<" not in error and ">" not in error


def test_overpass_http_400_keeps_the_page_message(client, mock_overpass):
    # The real server answers a parse error with HTTP 400 and this page, so the
    # message is in a body that raise_for_status would otherwise throw away.
    mock_overpass(lambda request: httpx.Response(400, text=OVERPASS_HTML_ERROR))
    resp = client.post("/api/overpass", json={"query": "[out:json];nodz(1);out;"})
    assert resp.status_code == 502
    error = resp.json()["error"]
    assert "HTTP 400" in error
    assert 'parse error: Unknown type "nodz"' in error


def test_overpass_unreachable(client, mock_overpass):
    def boom(request):
        raise httpx.ConnectTimeout("timed out", request=request)
    mock_overpass(boom)
    resp = client.post("/api/overpass", json={"query": "[out:json];node(1);out;"})
    assert resp.status_code == 502
    assert "could not reach" in resp.json()["error"]


def test_overpass_query_too_long(client, monkeypatch):
    monkeypatch.setenv("OVERPASS_MAX_QUERY_CHARS", "10")
    resp = client.post("/api/overpass", json={"query": "x" * 11})
    assert resp.status_code == 400
    assert "limit is 10" in resp.json()["error"]
