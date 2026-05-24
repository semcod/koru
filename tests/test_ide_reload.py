"""Tests for IDE window reload automation."""

from __future__ import annotations

from pathlib import Path
from unittest import mock

import pytest

from koru.autonomy import env as autonomy_env
from koru.ide_adapters import ide_reload


def test_keyboard_fallback_when_plugin_missing_auto_wayland(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)
    assert autonomy_env.keyboard_fallback_when_plugin_missing("cursor") is True
    assert autonomy_env.plugin_required_for_ide("cursor") is False


def test_keyboard_fallback_when_plugin_missing_disabled(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "0")
    assert autonomy_env.keyboard_fallback_when_plugin_missing("cursor") is False
    assert autonomy_env.plugin_required_for_ide("cursor") is True


def test_reload_via_command_palette_success(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[list[str]] = []

    def fake_run(argv, **kwargs):
        calls.append(list(argv))
        return mock.Mock(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(ide_reload.shutil, "which", lambda name: name)
    monkeypatch.setattr(ide_reload, "_focus_ide_window", lambda _ide: True)
    monkeypatch.setattr(ide_reload, "_run", fake_run)
    outcome = ide_reload.reload_via_command_palette("cursor")
    assert outcome.ok is True
    assert outcome.method == "command_palette"
    assert any(cmd[0] == "wtype" for cmd in calls)


def test_try_reload_skipped_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "0")
    outcome = ide_reload.try_reload_vscode_family_ide("cursor", project=Path("/tmp/p"))
    assert outcome.attempted is False
