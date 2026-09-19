from fastapi.testclient import TestClient

from app.main import app


def test_liveness_does_not_require_database() -> None:
    with TestClient(app) as client:
        response = client.get(
            "/api/v1/health/live",
            headers={"X-Request-ID": "health-check-1"},
        )

    assert response.status_code == 200
    assert response.json() == {"status": "alive"}
    assert response.headers["X-Request-ID"] == "health-check-1"
