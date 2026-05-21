"""Integration tests for ``koru local-serve`` (in-process HTTP server)."""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.request

import pytest

from koru.local_service import LocalServiceConfig, start_local_service_background


def _urlopen_json(url: str, *, data: bytes | None = None, method: str = "GET") -> dict:
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=5) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _urlopen_bytes(url: str) -> bytes:
    with urllib.request.urlopen(url, timeout=5) as resp:
        return resp.read()


@pytest.fixture
def local_service_server():
    cfg = LocalServiceConfig(host="127.0.0.1", port=0, max_events=16)
    server, thread, port = start_local_service_background(cfg)
    base = f"http://127.0.0.1:{port}"
    time.sleep(0.08)
    try:
        yield base
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=10)
        assert not thread.is_alive()


def test_health_returns_ok_and_version(local_service_server: str) -> None:
    data = _urlopen_json(f"{local_service_server}/health")
    assert data.get("ok") is True
    assert isinstance(data.get("version"), str)
    assert data["version"]


def test_post_event_roundtrip_and_ndjson_events(local_service_server: str) -> None:
    body = json.dumps({"hello": "koru", "n": 1}).encode("utf-8")
    posted = _urlopen_json(
        f"{local_service_server}/event",
        data=body,
        method="POST",
    )
    eid = posted["id"]
    assert isinstance(eid, str) and len(eid) == 32

    raw = _urlopen_bytes(f"{local_service_server}/events").decode("utf-8")
    lines = [ln for ln in raw.splitlines() if ln.strip()]
    assert lines
    last = json.loads(lines[-1])
    assert last["id"] == eid
    assert last["payload"] == {"hello": "koru", "n": 1}
    assert last["received_at"].endswith("Z")


def test_post_enqueue_alias(local_service_server: str) -> None:
    body = json.dumps({"via": "enqueue"}).encode("utf-8")
    posted = _urlopen_json(
        f"{local_service_server}/enqueue",
        data=body,
        method="POST",
    )
    raw = _urlopen_bytes(f"{local_service_server}/events").decode("utf-8")
    assert json.loads(raw.strip().splitlines()[-1])["payload"]["via"] == "enqueue"
    assert posted["id"]


def test_enqueue_adds_single_queue_item(local_service_server: str) -> None:
    body = json.dumps(
        {"type": "install", "package": "koru", "requires": ["installer"]},
    ).encode("utf-8")
    posted = _urlopen_json(
        f"{local_service_server}/enqueue",
        data=body,
        method="POST",
    )

    queue = _urlopen_json(f"{local_service_server}/queue")
    assert queue["counts"] == {"queued": 1}
    assert queue["items"][0]["id"] == posted["id"]
    assert queue["items"][0]["type"] == "install"
    assert queue["items"][0]["required_capabilities"] == ["installer"]


def test_queue_claim_and_complete_with_lease(local_service_server: str) -> None:
    posted = _urlopen_json(
        f"{local_service_server}/enqueue",
        data=json.dumps({"type": "upgrade", "requires": ["installer"]}).encode("utf-8"),
        method="POST",
    )
    claimed = _urlopen_json(
        f"{local_service_server}/queue/claim",
        data=json.dumps(
            {"worker_id": "koru-2", "capabilities": ["installer"], "lease_seconds": 60},
        ).encode("utf-8"),
        method="POST",
    )
    assert claimed["status"] == "leased"
    assert claimed["item"]["id"] == posted["id"]
    assert claimed["item"]["claimed_by"] == "koru-2"
    assert claimed["item"]["lease_expires_at"].endswith("Z")

    completed = _urlopen_json(
        f"{local_service_server}/queue/complete",
        data=json.dumps(
            {
                "action_id": posted["id"],
                "worker_id": "koru-2",
                "status": "completed",
                "result": {"ok": True},
            },
        ).encode("utf-8"),
        method="POST",
    )
    assert completed["status"] == "completed"

    queue = _urlopen_json(f"{local_service_server}/queue")
    assert queue["counts"] == {"completed": 1}
    assert queue["items"][0]["completed_by"] == "koru-2"


def test_queue_claim_filters_action_types(local_service_server: str) -> None:
    _urlopen_json(
        f"{local_service_server}/enqueue",
        data=json.dumps({"type": "upgrade", "requires": ["installer"]}).encode("utf-8"),
        method="POST",
    )
    queue_action = _urlopen_json(
        f"{local_service_server}/enqueue",
        data=json.dumps({"type": "planfile.queue.run", "requires": ["planfile.queue"]}).encode(
            "utf-8",
        ),
        method="POST",
    )

    claimed = _urlopen_json(
        f"{local_service_server}/queue/claim",
        data=json.dumps(
            {
                "worker_id": "queue-worker",
                "capabilities": ["planfile.queue"],
                "action_types": ["planfile.queue.run"],
            },
        ).encode("utf-8"),
        method="POST",
    )
    assert claimed["status"] == "leased"
    assert claimed["item"]["id"] == queue_action["id"]
    assert claimed["item"]["type"] == "planfile.queue.run"


def test_worker_lifecycle_prefers_new_healthy_version(local_service_server: str) -> None:
    old = _urlopen_json(
        f"{local_service_server}/workers/register",
        data=json.dumps({"worker_id": "old", "version": "1.0.0", "health": "ok"}).encode(
            "utf-8",
        ),
        method="POST",
    )
    assert old["decision"]["action"] == "continue"
    assert old["decision"]["active_worker_id"] == "old"

    new = _urlopen_json(
        f"{local_service_server}/workers/register",
        data=json.dumps({"worker_id": "new", "version": "1.2.0", "health": "ok"}).encode(
            "utf-8",
        ),
        method="POST",
    )
    assert new["decision"]["action"] == "continue"
    assert new["decision"]["active_worker_id"] == "new"

    old_heartbeat = _urlopen_json(
        f"{local_service_server}/workers/heartbeat",
        data=json.dumps({"worker_id": "old", "health": "ok", "conflict": True}).encode("utf-8"),
        method="POST",
    )
    assert old_heartbeat["decision"]["action"] == "drain-and-exit"
    assert old_heartbeat["decision"]["active_worker_id"] == "new"

    workers = _urlopen_json(f"{local_service_server}/workers")
    states = {worker["worker_id"]: worker["state"] for worker in workers["workers"]}
    assert states == {"old": "draining", "new": "active"}


def test_worker_registration_keeps_manager_metadata(local_service_server: str) -> None:
    reply = _urlopen_json(
        f"{local_service_server}/workers/register",
        data=json.dumps(
            {
                "worker_id": "queue-worker",
                "kind": "koru.queue",
                "version": "3.0.0",
                "project": "/tmp/demo",
                "metadata": {"mode": "loop"},
                "capabilities": ["planfile.queue"],
            },
        ).encode("utf-8"),
        method="POST",
    )
    worker = reply["worker"]
    assert worker["kind"] == "koru.queue"
    assert worker["project"] == "/tmp/demo"
    assert worker["metadata"] == {"mode": "loop"}


def test_worker_with_bad_health_is_quarantined(local_service_server: str) -> None:
    reply = _urlopen_json(
        f"{local_service_server}/workers/register",
        data=json.dumps({"worker_id": "bad", "version": "9.9.9", "health": "bad"}).encode(
            "utf-8",
        ),
        method="POST",
    )
    assert reply["decision"]["action"] == "quarantine"
    assert reply["decision"]["active_worker_id"] is None


def test_lifecycle_decision_registers_unknown_worker(local_service_server: str) -> None:
    reply = _urlopen_json(
        f"{local_service_server}/lifecycle/decision",
        data=json.dumps({"worker_id": "fresh", "version": "2.0.0", "health": "ok"}).encode(
            "utf-8",
        ),
        method="POST",
    )
    assert reply["worker"]["worker_id"] == "fresh"
    assert reply["decision"] == {
        "worker_id": "fresh",
        "action": "continue",
        "state": "active",
        "active_worker_id": "fresh",
    }


def test_post_empty_body_is_400(local_service_server: str) -> None:
    req = urllib.request.Request(
        f"{local_service_server}/event",
        data=b"",
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with pytest.raises(urllib.error.HTTPError) as ei:
        urllib.request.urlopen(req, timeout=5)
    assert ei.value.code == 400


def test_unknown_path_404(local_service_server: str) -> None:
    with pytest.raises(urllib.error.HTTPError) as ei:
        _urlopen_json(f"{local_service_server}/nope")
    assert ei.value.code == 404
