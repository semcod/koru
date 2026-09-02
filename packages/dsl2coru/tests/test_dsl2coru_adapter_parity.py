"""Parity: same compatibility command → same result across bus input codecs."""

from __future__ import annotations

from dsl2coru.bus import dispatch
from dsl2coru.codec import envelope_to_bytes


def _mock_runner(argv: list[str]) -> tuple[int, str, str]:
    return 0, f"ok:{argv[0]}", ""


def test_status_across_adapters(monkeypatch) -> None:
    monkeypatch.setattr("dsl2coru.handlers.runner.default_runner", _mock_runner)

    line = "STATUS"
    payload = {"verb": "STATUS"}
    r_text = dispatch(line)
    r_dict = dispatch(payload)
    r_pb = dispatch(envelope_to_bytes(payload))
    assert r_text.ok is True
    assert r_dict.ok == r_text.ok
    assert r_pb.ok == r_text.ok
    assert r_text.action == r_dict.action == r_pb.action == "status"
