"""Tests for multi-instance autopilot socket resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from koru.autopilot import default_socket_path
from koruide.socket import _autopilot_socket_basename


def test_explicit_socket_env_overrides_all(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    sock = tmp_path / "custom.sock"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_SOCKET", str(sock))
    assert default_socket_path() == sock.resolve()


def test_instance_env_changes_basename(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "Cursor : main")
    assert _autopilot_socket_basename() == "koru-autopilot-Cursor---main.sock"


def test_default_basename_legacy_when_no_instance(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    assert _autopilot_socket_basename() == "koru-autopilot.sock"


def test_auto_instance_uses_default_basename(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "auto")
    assert _autopilot_socket_basename() == "koru-autopilot.sock"
