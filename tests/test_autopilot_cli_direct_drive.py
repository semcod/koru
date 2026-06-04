"""Focused unit tests for the extracted direct-drive subsystem (R5)."""
from __future__ import annotations

import argparse
import json
from typing import Any

import pytest

from koru.autopilot import cli_direct_drive
from koru.autopilot.cli_direct_drive import (
    _auto_direct_fallback_enabled,
    _emit_direct_drive_auto_selection,
    _emit_json_payload,
    _selected_keyboard_backend,
    _should_fallback_to_direct,
)
from koru.observability_writer import observability_event_store_path


def _ns(**kwargs: Any) -> argparse.Namespace:
    return argparse.Namespace(**kwargs)


# ---------------------------------------------------------------------------
# _auto_direct_fallback_enabled
# ---------------------------------------------------------------------------

def test_auto_direct_fallback_default_enabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", raising=False)
    assert _auto_direct_fallback_enabled() is True


def test_auto_direct_fallback_explicit_off(monkeypatch: pytest.MonkeyPatch) -> None:
    for value in ("0", "false", "False", "no", "off"):
        monkeypatch.setenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", value)
        assert _auto_direct_fallback_enabled() is False, value


def test_auto_direct_fallback_explicit_on(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", "1")
    assert _auto_direct_fallback_enabled() is True


# ---------------------------------------------------------------------------
# _should_fallback_to_direct
# ---------------------------------------------------------------------------

def test_should_fallback_returns_false_when_require_plugin() -> None:
    args = _ns(require_plugin=True)
    reply = {"ok": False, "opened": False, "submitted": False}
    assert _should_fallback_to_direct(args, reply) is False


def test_should_fallback_returns_false_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", "0")
    args = _ns(require_plugin=False)
    reply = {"ok": False, "opened": False, "submitted": False}
    assert _should_fallback_to_direct(args, reply) is False


def test_should_fallback_returns_false_when_reply_ok(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", raising=False)
    args = _ns(require_plugin=False)
    assert _should_fallback_to_direct(args, {"ok": True}) is False


def test_should_fallback_true_on_focus_message(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", raising=False)
    args = _ns(require_plugin=False)
    reply = {"ok": False, "message": "Chat input is not focused/open in IDE"}
    assert _should_fallback_to_direct(args, reply) is True


def test_should_fallback_true_when_not_opened_or_submitted(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", raising=False)
    args = _ns(require_plugin=False)
    reply = {"ok": False, "opened": False, "submitted": False}
    assert _should_fallback_to_direct(args, reply) is True


def test_should_fallback_false_when_opened_true(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", raising=False)
    args = _ns(require_plugin=False)
    reply = {"ok": False, "opened": True, "submitted": False}
    assert _should_fallback_to_direct(args, reply) is False


# ---------------------------------------------------------------------------
# _emit_json_payload
# ---------------------------------------------------------------------------

def test_emit_json_payload_enabled(capsys: pytest.CaptureFixture[str]) -> None:
    _emit_json_payload({"k": "v"}, enabled=True)
    out = capsys.readouterr().out
    assert '"k": "v"' in out


def test_emit_json_payload_disabled(capsys: pytest.CaptureFixture[str]) -> None:
    _emit_json_payload({"k": "v"}, enabled=False)
    assert capsys.readouterr().out == ""


# ---------------------------------------------------------------------------
# _emit_direct_drive_auto_selection
# ---------------------------------------------------------------------------

def test_emit_auto_selection_logs_when_auto(capsys: pytest.CaptureFixture[str]) -> None:
    args = _ns(ide="auto", os_profile="")
    _emit_direct_drive_auto_selection(args, "vscode", "auto:running")
    err = capsys.readouterr().err
    assert "auto-selected vscode (auto:running)" in err


def test_emit_auto_selection_silent_when_explicit_ide(capsys: pytest.CaptureFixture[str]) -> None:
    args = _ns(ide="vscode", os_profile="")
    _emit_direct_drive_auto_selection(args, "vscode", "explicit")
    assert capsys.readouterr().err == ""


def test_emit_auto_selection_silent_when_os_profile(capsys: pytest.CaptureFixture[str]) -> None:
    args = _ns(ide="auto", os_profile="windsurf")
    _emit_direct_drive_auto_selection(args, "windsurf", "auto:profile")
    assert capsys.readouterr().err == ""


def test_selected_keyboard_backend_prefers_select_backend() -> None:
    class _Injector:
        session = "wayland"

        def select_backend(self) -> str:
            return "wtype"

    assert _selected_keyboard_backend(_Injector()) == "wtype"


def test_selected_keyboard_backend_falls_back_to_session_or_keyboard() -> None:
    assert _selected_keyboard_backend(_ns(session="x11")) == "x11"
    assert _selected_keyboard_backend(_ns(session="")) == "keyboard"


# ---------------------------------------------------------------------------
# Backward-compat: re-exports from cli_command keep working
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_cli_command() -> None:
    """Symbols re-exported from cli_command must be the same objects."""
    from koru.autopilot import cli_command

    assert cli_command._auto_direct_fallback_enabled is _auto_direct_fallback_enabled
    assert cli_command._should_fallback_to_direct is _should_fallback_to_direct
    assert cli_command._run_direct_drive is cli_direct_drive._run_direct_drive
    assert cli_command._emit_json_payload is _emit_json_payload


def test_run_direct_drive_emits_desktop_gui_control_command(
    tmp_path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import cli_command
    import gillm.injection.os_injector as oi

    class _DummyInjector:
        session = "wayland"

        def select_backend(self) -> str:
            return "stub"

    monkeypatch.setattr(cli_command, "Injector", _DummyInjector)
    monkeypatch.setattr(
        cli_command,
        "resolve_drive_target",
        lambda _ide, _profile, project=None: ("vscode", "vscode", "explicit"),
    )
    monkeypatch.setattr(
        oi,
        "try_drive_with_profile",
        lambda **kwargs: {
            "ok": True,
            "backend": "os_injector",
            "submitted": kwargs["submit"],
        },
    )
    args = _ns(
        ide="vscode",
        os_profile="",
        project=tmp_path,
        submit=True,
        dry_run=False,
        delay_seconds=0.0,
    )

    rc, payload = cli_direct_drive._run_direct_drive(args, "hello replay", emit_payload=False)

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    command = rows[0]["payload"]["data"]
    assert rc == 0
    assert payload == {"ok": True, "backend": "os_injector", "submitted": True}
    assert command["surface"] == "desktop_gui"
    assert command["operation"] == "os_injector.profile_drive"
    assert command["replayable"] is True
    assert command["args"]["text"] == "hello replay"
    assert command["args"]["profile_id"] == "vscode"
