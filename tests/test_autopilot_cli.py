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


# ---- P2.5: handoff ---------------------------------------------------------


def test_handoff_dry_run_prints_brief_and_skips_daemon(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``handoff --dry-run`` must print the brief and never touch the socket."""
    monkeypatch.setattr(cli_command, "_build_brief", lambda _p: "# fake brief\n\nhi")
    rc = autopilot_main([
        "handoff", "--dry-run", "--project", str(tmp_path),
    ])
    assert rc == 0
    out = capsys.readouterr().out
    assert "# fake brief" in out


def test_handoff_requires_running_daemon(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_command, "_build_brief", lambda _p: "# brief")
    socket = tmp_path / "missing.sock"
    rc = autopilot_main([
        "--socket", str(socket), "handoff", "--project", str(tmp_path),
    ])
    assert rc == 2
    assert "daemon not running" in capsys.readouterr().err


def test_handoff_drives_brief_through_client(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: build_brief + daemon up → client.drive called with the brief."""

    monkeypatch.setattr(cli_command, "_build_brief", lambda _p: "# the brief")

    class _FakeClient:
        def __init__(self, *_a, **_kw) -> None:
            self.drive_called_with: dict | None = None

        def is_running(self) -> bool:
            return True

        def drive(self, text, *, submit=True, ide="auto"):
            self.drive_called_with = {"text": text, "submit": submit, "ide": ide}
            return {"ok": True, "delivered": True, "type": "ack"}

    fake = _FakeClient()
    monkeypatch.setattr(cli_command, "AutopilotClient", lambda *a, **k: fake)
    rc = autopilot_main(["handoff", "--project", str(tmp_path)])
    assert rc == 0
    assert fake.drive_called_with["text"] == "# the brief"
    assert fake.drive_called_with["submit"] is True
    assert fake.drive_called_with["ide"] == "auto"
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["chars"] == len("# the brief")


# ---- P2.8: tail ------------------------------------------------------------


def _write_audit_log(path: Path, entries: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as fh:
        for e in entries:
            fh.write(json.dumps(e) + "\n")


def test_tail_text_format_renders_entries(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(log, [
        {"ts": "2026-05-11T18:30:01.000Z", "event": "daemon_started", "socket": "/tmp/x"},
        {"ts": "2026-05-11T18:30:05.000Z", "event": "drive",
         "ide": "windsurf", "backend": "plugin", "chars": 29, "submit": True, "ok": True},
    ])
    rc = autopilot_main(["tail", "--log", str(log)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "daemon_started" in out
    assert "drive" in out
    assert "windsurf" in out
    assert "backend=plugin" in out
    assert "chars=29" in out


def test_tail_json_format_returns_array(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(log, [
        {"ts": "t1", "event": "drive", "ide": "windsurf"},
        {"ts": "t2", "event": "drive", "ide": "vscode"},
    ])
    rc = autopilot_main(["tail", "--log", str(log), "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert [e["ide"] for e in data] == ["windsurf", "vscode"]


def test_tail_n_limits_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(log, [
        {"ts": f"t{i}", "event": "drive", "ide": "x", "chars": i} for i in range(10)
    ])
    rc = autopilot_main(["tail", "--log", str(log), "-n", "3"])
    assert rc == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    # Last 3 entries
    assert "chars=7" in lines[0]
    assert "chars=9" in lines[2]


def test_tail_missing_log_errors_cleanly(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    rc = autopilot_main(["tail", "--log", str(tmp_path / "nope.log")])
    assert rc == 1
    assert "no log at" in capsys.readouterr().err


def test_tail_skips_malformed_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "audit.log"
    log.write_text(
        '{"ts":"t1","event":"drive","ide":"x"}\n'
        "not json at all\n"
        '{"ts":"t2","event":"drive","ide":"y"}\n',
        encoding="utf-8",
    )
    rc = autopilot_main(["tail", "--log", str(log)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "ide=x" in out
    assert "ide=y" in out
    assert "not json" not in out
