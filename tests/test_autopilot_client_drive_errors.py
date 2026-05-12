"""AutopilotClient.drive must not raise when the unix socket is missing."""

from __future__ import annotations

from pathlib import Path

from koru.autopilot.client import AutopilotClient


def test_drive_missing_socket_returns_ok_false(tmp_path: Path) -> None:
    missing = tmp_path / "no-such.sock"
    client = AutopilotClient(socket_path=missing, timeout=0.2)
    reply = client.drive("hello", ide="vscode")
    assert reply.get("ok") is False
    assert "missing" in (reply.get("message") or "").lower()
