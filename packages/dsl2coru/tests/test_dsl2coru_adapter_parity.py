"""Parity: same command → same result across bus, URI, REST, protobuf."""

from __future__ import annotations

from fastapi.testclient import TestClient

from dsl2coru.bus import dispatch
from dsl2coru.codec import envelope_to_bytes
from rest2coru.app import create_app
from uri2coru.run import run_uri


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, f"ok:{argv[0]}", ""


def test_status_across_adapters(monkeypatch) -> None:
    monkeypatch.setattr("dsl2coru.handlers.runner.default_runner", _mock_runner)

    line = "STATUS"
    payload = {"verb": "STATUS"}
    uri = "coru://cmd/STATUS"

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
    assert r_text.action == r_dict.action == r_pb.action == r_uri.action == "status"
