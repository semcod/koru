"""CLI-level tests for ``koru autopilot``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from koru.autopilot import cli_command
from koru.autopilot.cli_command import autopilot_main


def test_autopilot_parser_requires_action() -> None:
    with pytest.raises(SystemExit):
        autopilot_main([])


def test_drive_without_daemon_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "drive", "hello"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "daemon not running" in err


def test_drive_dry_run_direct(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    # Force the injector to find xdotool so dry-run can pick a backend.
    class _FakeInjector:
        def __init__(self) -> None:
            pass

        def type_text(self, text, *, ide="default", submit=True, dry_run=False):
            from koru.autopilot.injector import InjectionResult
            return InjectionResult(
                backend="xdotool", submitted=submit, dry_run=dry_run,
                output=f"[dry-run] {len(text)} chars",
            )

    monkeypatch.setattr(cli_command, "Injector", _FakeInjector)
    rc = autopilot_main(["drive", "--direct", "--dry-run", "hello", "world"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["dry_run"] is True
    assert payload["backend"] == "xdotool"


def test_ide_list_empty(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cli_command, "detect_running_ides", lambda: [])
    rc = autopilot_main(["ide-list"])
    assert rc == 0
    assert "no IDE processes" in capsys.readouterr().out


def test_doctor_json_output(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeInjector:
        session = "x11"

        def probe(self):
            from koru.autopilot.injector import BackendStatus
            return [BackendStatus(name="xdotool", available=True, reason="/usr/bin/xdotool")]

        def select_backend(self) -> str:
            return "xdotool"

    monkeypatch.setattr(cli_command, "Injector", _FakeInjector)
    monkeypatch.setattr(cli_command, "detect_running_ides", lambda: [])
    rc = autopilot_main(["doctor", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_backend"] == "xdotool"
    assert payload["session"] == "x11"
    assert payload["backends"][0]["available"] is True


def test_status_when_no_daemon(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "status"])
    assert rc == 1
    assert "NOT running" in capsys.readouterr().out


def test_shutdown_when_no_daemon(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "shutdown"])
    assert rc == 0
    assert "not running" in capsys.readouterr().out
