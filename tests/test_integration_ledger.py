from __future__ import annotations

import json

from koru.integration_ledger import DSL_VERSION, record_integration_action


def test_record_integration_action_writes_jsonl_and_returns_dsl(tmp_path, monkeypatch):
    monkeypatch.setenv("KORU_ACTIVITY_LOG", "0")

    line = record_integration_action(
        project=tmp_path,
        action="plugin.ack",
        intent="verify submit",
        actor="autopilot-daemon",
        target="vscodium",
        transport="plugin-socket",
        phase="submit_unverified",
        attempt=2,
        outcome="failed",
        reason="input still contains pasted text",
        evidence="winning_paste=host-clipboard",
        next_step="do not paste again",
        data={"verification": "submit_unverified"},
    )

    assert line.startswith(DSL_VERSION)
    assert "action=plugin.ack" in line
    assert 'reason="input still contains pasted text"' in line
    path = tmp_path / ".planfile" / ".koru" / "integration-actions.jsonl"
    rows = [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines()]
    assert rows[0]["dsl"] == line
    assert rows[0]["target"] == "vscodium"
    assert rows[0]["data"]["verification"] == "submit_unverified"


def test_record_integration_action_survives_bytes_payload(tmp_path, monkeypatch):
    """Regression (2026-07-05): a drive reply carrying raw ``bytes`` raised
    TypeError inside json.dumps and killed the whole autonomous loop. The
    ledger must degrade unserializable values, never crash."""
    monkeypatch.delenv("KORU_INTEGRATION_LEDGER_PATH", raising=False)
    monkeypatch.chdir(tmp_path)

    line = record_integration_action(
        project=tmp_path,
        action="drive.retry_decision",
        intent="decide whether another IDE interaction is safe",
        target="claude-code",
        outcome="stop",
        data={"reply": b"\xffraw vendor stdout", "assessment": object()},
        emit_activity=False,
    )

    assert line.startswith(DSL_VERSION)
    path = tmp_path / ".planfile" / ".koru" / "integration-actions.jsonl"
    rows = [json.loads(raw) for raw in path.read_text(encoding="utf-8").splitlines()]
    assert "raw vendor stdout" in rows[0]["data"]["reply"]
    assert isinstance(rows[0]["data"]["assessment"], str)
