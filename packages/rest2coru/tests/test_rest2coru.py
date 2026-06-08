from fastapi.testclient import TestClient

from rest2coru.app import create_app


def test_health_and_dsl() -> None:
    client = TestClient(create_app())
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["status"] == "ok"

    resp = client.post(
        "/v1/dsl?project=.",
        content="STATUS",
        headers={"Content-Type": "text/plain"},
    )
    assert resp.status_code == 200
    assert resp.json()["ok"] is True
