"""Tests for :mod:`koru.agent_backend_runtime`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from koru.agent_backend_runtime import PluginSocketBackend


def test_plugin_socket_backend_forwards_send_chat_to_drive() -> None:
    client = MagicMock()
    client.drive.return_value = {"ok": True, "backend": "mock"}
    backend = PluginSocketBackend(client)
    project = Path("/tmp/koru-proj")
    out = backend.send_chat(
        project,
        "hello agent",
        ide="windsurf",
        submit=True,
        ticket_id="PLF-1",
    )
    client.drive.assert_called_once_with("hello agent", submit=True, ide="windsurf")
    assert out == {"ok": True, "backend": "mock"}
