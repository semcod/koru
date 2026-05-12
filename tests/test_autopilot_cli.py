"""CLI-level tests for ``koru autopilot``."""

from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

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


def test_ide_list_marks_focused_ide(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        cli_command,
        "detect_running_ides",
        lambda: [
            SimpleNamespace(id="windsurf", label="Windsurf", pid=10, exe="/opt/windsurf"),
            SimpleNamespace(id="jetbrains", label="JetBrains IDE", pid=20, exe="/opt/idea"),
        ],
    )
    monkeypatch.setattr(cli_command, "detect_focused_ide_id", lambda: "jetbrains")
    rc = autopilot_main(["ide-list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "windsurf" in out
    assert "jetbrains" in out
    assert "[focused]" in out


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
    monkeypatch.setattr(cli_command, "detect_focused_ide_id", lambda: "windsurf")
    rc = autopilot_main(["doctor", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_backend"] == "xdotool"
    assert payload["session"] == "x11"
    assert payload["backends"][0]["available"] is True
    assert payload["focused_ide"] == "windsurf"


def test_doctor_fix_text_output(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeInjector:
        session = "wayland"

        def probe(self):
            from koru.autopilot.injector import BackendStatus
            return [BackendStatus(name="ydotool", available=True, reason="/usr/bin/ydotool")]

        def select_backend(self) -> str:
            return "ydotool"

    monkeypatch.setattr(cli_command, "Injector", _FakeInjector)
    monkeypatch.setattr(cli_command, "detect_running_ides", lambda: [])
    monkeypatch.setattr(cli_command, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        cli_command,
        "_doctor_fix_payload",
        lambda: {
            "commands": ["koru autopilot setup-host"],
            "automated_apt_suggestion": "sudo apt-get install -y wtype",
            "human_actions_required": ["Relogin after adding input group."],
        },
    )

    rc = autopilot_main(["doctor", "--fix"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "next steps (guided fix):" in out
    assert "koru autopilot setup-host" in out
    assert "apt suggestion" in out
    assert "human actions still required:" in out


def test_doctor_fix_json_output(capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch) -> None:
    class _FakeInjector:
        session = "wayland"

        def probe(self):
            from koru.autopilot.injector import BackendStatus
            return [BackendStatus(name="ydotool", available=True, reason="/usr/bin/ydotool")]

        def select_backend(self) -> str:
            return "ydotool"

    monkeypatch.setattr(cli_command, "Injector", _FakeInjector)
    monkeypatch.setattr(cli_command, "detect_running_ides", lambda: [])
    monkeypatch.setattr(cli_command, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        cli_command,
        "_doctor_fix_payload",
        lambda: {
            "commands": ["koru autopilot setup-host --install --dry-run"],
            "automated_apt_suggestion": None,
            "human_actions_required": ["Start ydotoold service."],
        },
    )

    rc = autopilot_main(["doctor", "--format", "json", "--fix"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected_backend"] == "ydotool"
    assert "fix" in payload
    assert payload["fix"]["commands"][0] == "koru autopilot setup-host --install --dry-run"
    assert payload["fix"]["human_actions_required"][0] == "Start ydotoold service."


def test_install_plugin_dry_run_auto_detect_from_term_program(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")

    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setattr(cli_command.shutil, "which", lambda name: "/usr/bin/code" if name == "code" else None)
    monkeypatch.setattr(cli_command, "_resolve_plugin_vsix_path", lambda _p: vsix)

    rc = autopilot_main(["install-plugin", "--dry-run", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["ide"] == "vscode"
    assert payload["editor"] == "/usr/bin/code"
    assert payload["vsix"] == str(vsix)
    assert payload["command"][0] == "/usr/bin/code"


def test_install_plugin_auto_detect_ambiguous_running_ides_errors(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.setattr(cli_command, "detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        cli_command,
        "detect_running_ides",
        lambda: [
            SimpleNamespace(id="cursor", label="Cursor", pid=1, exe="/usr/bin/cursor"),
            SimpleNamespace(id="windsurf", label="Windsurf", pid=2, exe="/usr/bin/windsurf"),
        ],
    )

    rc = autopilot_main(["install-plugin", "--dry-run"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "multiple supported IDEs detected" in err


def test_install_plugin_exec_success_json_payload(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")

    monkeypatch.setattr(cli_command, "_resolve_plugin_target_ide", lambda _raw: "cursor")
    monkeypatch.setattr(cli_command, "_resolve_plugin_editor_bin", lambda _ide: "/usr/bin/cursor")
    monkeypatch.setattr(cli_command, "_resolve_plugin_vsix_path", lambda _p: vsix)

    def _fake_run(cmd, capture_output, text, check):
        assert cmd[0] == "/usr/bin/cursor"
        return cli_command.subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(cli_command.subprocess, "run", _fake_run)

    rc = autopilot_main(["install-plugin", "--ide", "cursor", "--format", "json", "--force"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["returncode"] == 0
    assert payload["ide"] == "cursor"
    assert payload["command"][-1] == "--force"


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


# ---- P2.6: systemd --user unit --------------------------------------------


def test_install_unit_print_renders_execstart(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(cli_command, "_resolve_koru_bin", lambda: "/opt/koru/bin/koru")
    rc = autopilot_main(["install-unit", "--print"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "[Unit]" in out
    assert "ExecStart=/opt/koru/bin/koru autopilot daemon --idempotent --no-handoff" in out


def test_install_unit_writes_to_xdg_default_path(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "cfg"))
    monkeypatch.setattr(cli_command, "_resolve_koru_bin", lambda: "/usr/bin/koru")
    rc = autopilot_main(["install-unit"])
    assert rc == 0
    unit = tmp_path / "cfg" / "systemd" / "user" / "koru-autopilot.service"
    assert unit.is_file()
    text = unit.read_text(encoding="utf-8")
    assert "ExecStart=/usr/bin/koru autopilot daemon --idempotent --no-handoff" in text
    assert "installed" in capsys.readouterr().out


def test_install_unit_refuses_overwrite_without_force(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dest = tmp_path / "koru-autopilot.service"
    dest.write_text("[Unit]\nDescription=existing\n", encoding="utf-8")
    rc = autopilot_main(["install-unit", "--dest", str(dest)])
    assert rc == 1
    err = capsys.readouterr().err
    assert "already exists" in err
    assert "pass --force" in err


def test_resolve_koru_bin_falls_back_to_sys_executable_sibling(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    venv_bin = tmp_path / "venv" / "bin"
    venv_bin.mkdir(parents=True)
    py = venv_bin / "python"
    py.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    py.chmod(0o755)
    koru = venv_bin / "koru"
    koru.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    koru.chmod(0o755)

    monkeypatch.setattr(cli_command.shutil, "which", lambda _name: None)
    monkeypatch.setattr(cli_command.sys, "executable", str(py))

    assert cli_command._resolve_koru_bin() == str(koru)
