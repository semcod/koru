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
