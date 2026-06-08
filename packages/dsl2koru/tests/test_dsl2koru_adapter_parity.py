"""Parity: same command → same result across bus, URI, REST, protobuf."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dsl2koru.bus import dispatch
from dsl2koru.codec import envelope_to_bytes
from rest2koru.app import create_app
from uri2koru.run import run_uri


def test_validate_lane_across_adapters() -> None:
    line = "VALIDATE_LANE IDE auto INSTANCE default"
    payload = {"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"}
    uri = "koru://cmd/VALIDATE_LANE?ide=auto&instance=default"

    r_text = dispatch(line)
    r_dict = dispatch(payload)
    r_pb = dispatch(envelope_to_bytes(payload))
    r_uri = run_uri(uri)
    client = TestClient(create_app())
    r_rest = client.post(
        "/v1/dsl",
        content=line,
        headers={"Content-Type": "text/plain"},
    )

    assert r_text.ok is True
    assert r_dict.ok == r_text.ok
    assert r_pb.ok == r_text.ok
    assert r_uri.ok == r_text.ok
    assert r_rest.status_code == 200
    assert r_rest.json()["ok"] == r_text.ok
    assert r_text.verb == r_dict.verb == r_pb.verb == r_uri.verb == "VALIDATE_LANE"


def test_query_repair_history_text_vs_rest(tmp_path) -> None:
    line = f"QUERY_REPAIR_HISTORY PROJECT {tmp_path} LIMIT 2"
    r_bus = dispatch(line, default_project=str(tmp_path), project_root=tmp_path)
    client = TestClient(create_app())
    r_rest = client.post(
        f"/v1/commands?project={tmp_path}",
        json={"verb": "QUERY_REPAIR_HISTORY", "project": str(tmp_path), "limit": 2},
        headers={"Content-Type": "application/json"},
    )
    assert r_bus.ok is True
    assert r_rest.status_code == 200
    assert r_rest.json()["ok"] == r_bus.ok
    assert r_rest.json()["verb"] == r_bus.verb
