"""CLI-level tests for ``koru autopilot``."""

from __future__ import annotations

import json
import os
from pathlib import Path
from types import SimpleNamespace

import pytest

from koru.autopilot import cli_command, doctor_cli, install_plugin_cli, systemd_cli
from koru.autopilot.cli_command import autopilot_main
from koru.autopilot.commands import handoff
from koru.autopilot.cli_parser import build_autopilot_parser
from koru.autopilot.cli_trace import action_trace


def test_autopilot_parser_requires_action() -> None:
    with pytest.raises(SystemExit):
        autopilot_main([])


def test_autopilot_parser_module_preserves_drive_and_trace_options() -> None:
    parser = build_autopilot_parser()

    drive_args = parser.parse_args(
        ["drive", "--prompt", "hello", "--ide", "vscode", "--require-plugin"]
    )
    replay_args = parser.parse_args(["drive", "--prompt-file", "prompt.txt", "--ide", "vscodium"])
    trace_args = parser.parse_args(["trace", "--format", "drive-dsl", "--limit", "3"])

    assert drive_args.action == "drive"
    assert drive_args.prompt == "hello"
    assert drive_args.ide == "vscode"
    assert drive_args.require_plugin is True
    assert replay_args.prompt_file == Path("prompt.txt")
    assert trace_args.action == "trace"
    assert trace_args.format == "drive-dsl"
    assert trace_args.limit == 3


def test_drive_without_daemon_errors(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "drive", "hello"])
    assert rc == 2
    err = capsys.readouterr().err
    assert "daemon not running" in err


def test_drive_missing_text_errors(capsys: pytest.CaptureFixture[str]) -> None:
    rc = autopilot_main(["drive"])
    assert rc == 2
    assert "missing text" in capsys.readouterr().err


def test_trace_drive_dsl_reads_recent_lines(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    dsl_path = tmp_path / ".planfile" / ".koru" / "dsl_recent.json"
    dsl_path.parent.mkdir(parents=True)
    dsl_path.write_text(
        json.dumps({"lines": ["#001 act=paste ok=true", "#900 act=diagnose severity=ok"]}),
        encoding="utf-8",
    )
    parser = build_autopilot_parser()
    args = parser.parse_args(
        ["trace", "--project", str(tmp_path), "--format", "drive-dsl", "--limit", "1"]
    )

    rc = action_trace(args)

    assert rc == 0
    out = capsys.readouterr().out
    assert "#900 act=diagnose severity=ok" in out
    assert "#001 act=paste" not in out


def test_client_uses_explicit_ide_socket_when_env_is_unset(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)
    monkeypatch.setenv("XDG_RUNTIME_DIR", str(tmp_path))

    client = cli_command._client(SimpleNamespace(socket=None, ide="cursor"))

    assert client.socket_path == tmp_path / "koru-autopilot-cursor.sock"
    assert os.environ.get("KORU_AUTOPILOT_INSTANCE") is None


def test_drive_prompt_flag(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: dict[str, object] = {}

    class _C:
        def is_running(self) -> bool:
            return True

        def drive(
            self,
            text: str,
            *,
            submit: bool = True,
            ide: str = "auto",
            require_plugin: bool = False,
        ):
            captured["text"] = text
            captured["submit"] = submit
            captured["ide"] = ide
            captured["require_plugin"] = require_plugin
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(cli_command, "_client", lambda _a: _C())
    rc = autopilot_main(["drive", "--prompt", "TAK", "--ide", "vscode", "--require-plugin"])
    assert rc == 0
    assert captured["text"] == "TAK"
    assert captured["ide"] == "vscode"
    assert captured["require_plugin"] is True
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True


def test_drive_auto_fallbacks_to_direct_when_daemon_cannot_focus(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _C:
        def is_running(self) -> bool:
            return True

        def drive(
            self,
            text: str,
            *,
            submit: bool = True,
            ide: str = "auto",
            require_plugin: bool = False,
        ):
            return {
                "ok": False,
                "message": "chat input is not focused/open (no supported focus command)",
                "opened": False,
                "submitted": False,
                "type": "ack",
            }

    monkeypatch.setattr(cli_command, "_client", lambda _a: _C())
    monkeypatch.setattr(
        cli_command,
        "_run_direct_drive",
        lambda _args, _text, emit_payload=False: (
            0,
            {"ok": True, "backend": "ydotool", "submitted": True},
        ),
    )

    rc = autopilot_main(["drive", "hello"])
    assert rc == 0
    captured = capsys.readouterr()
    assert "falling back to local --direct injection" in captured.err
    payload = json.loads(captured.out)
    assert payload["backend"] == "ydotool"
    assert payload["daemon_fallback"]["opened"] is False
    assert payload["daemon_fallback"]["submitted"] is False


def test_drive_auto_fallback_can_be_disabled_by_env(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    class _C:
        def is_running(self) -> bool:
            return True

        def drive(
            self,
            text: str,
            *,
            submit: bool = True,
            ide: str = "auto",
            require_plugin: bool = False,
        ):
            return {
                "ok": False,
                "message": "chat input is not focused/open",
                "opened": False,
                "submitted": False,
                "type": "ack",
            }

    monkeypatch.setenv("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", "0")
    monkeypatch.setattr(cli_command, "_client", lambda _a: _C())

    def _should_not_fallback(*_a, **_k):
        raise AssertionError("should not fallback")

    monkeypatch.setattr(
        cli_command,
        "_run_direct_drive",
        _should_not_fallback,
    )

    rc = autopilot_main(["drive", "hello"])
    assert rc == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is False
    assert payload["opened"] is False


def test_drive_dry_run_direct(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi

    monkeypatch.setattr(oi, "try_drive_with_profile", lambda **_k: None)

    # Force the injector to find xdotool so dry-run can pick a backend.
    class _FakeInjector:
        session = "x11"

        def __init__(self) -> None:
            pass

        def select_backend(self) -> str:
            return "xdotool"

        def type_text(self, text, *, ide="default", submit=True, dry_run=False):
            from koru.autopilot.injector import InjectionResult

            return InjectionResult(
                backend="xdotool",
                submitted=submit,
                dry_run=dry_run,
                output=f"[dry-run] {len(text)} chars",
            )

    monkeypatch.setattr(cli_command, "Injector", _FakeInjector)
    rc = autopilot_main(["drive", "--direct", "--dry-run", "hello", "world"])
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads(out)
    assert payload["dry_run"] is True
    assert payload["backend"] == "xdotool"


def test_drive_direct_prefers_os_injector_profile(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    class _Inj:
        session = "x11"

        def type_text(self, *_a, **_k):
            raise AssertionError("keyboard injector should not run")

    monkeypatch.setattr(cli_command, "Injector", lambda: _Inj())
    monkeypatch.setattr(
        cli_command,
        "resolve_drive_target",
        lambda *_a, **_k: ("vscode", "vscode", "test:explicit"),
    )

    def _fake_try(**kwargs):
        assert kwargs["tool_id"] == "vscode"
        return {"ok": True, "backend": "os_injector", "tool_id": "vscode", "submitted": True}

    monkeypatch.setattr(oi_mod, "try_drive_with_profile", _fake_try)
    rc = autopilot_main(["drive", "--direct", "--prompt", "go"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["backend"] == "os_injector"


def test_drive_direct_honors_os_profile_override(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setattr(cli_command, "detect_running_ides", lambda: [])

    class _Inj:
        session = "x11"

        def type_text(self, *_a, **_k):
            raise AssertionError("keyboard injector should not run")

    seen: dict[str, object] = {}

    def _fake_try(**kwargs):
        seen.update(kwargs)
        return {"ok": True, "backend": "os_injector", "tool_id": kwargs["tool_id"]}

    monkeypatch.setattr(cli_command, "Injector", lambda: _Inj())
    monkeypatch.setattr(oi_mod, "try_drive_with_profile", _fake_try)
    rc = autopilot_main(
        ["drive", "--direct", "--os-profile", "windsurf", "--prompt", "go"],
    )
    assert rc == 0
    assert seen["tool_id"] == "windsurf"
    payload = json.loads(capsys.readouterr().out)
    assert payload["tool_id"] == "windsurf"


def test_drive_direct_os_profile_requires_os_injector_when_not_available(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod
    from koru.autopilot.injector import InjectionResult

    class _Inj:
        session = "wayland"

        def type_text(self, text, *, ide="default", submit=True, dry_run=False):
            return InjectionResult(
                backend="ydotool",
                submitted=submit,
                dry_run=dry_run,
                output=text,
            )

    monkeypatch.setattr(cli_command, "Injector", lambda: _Inj())
    monkeypatch.setattr(oi_mod, "try_drive_with_profile", lambda **_k: None)
    rc = autopilot_main(
        ["drive", "--direct", "--os-profile", "windsurf", "--prompt", "go"],
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "requested --os-profile but os-injector path is unavailable" in err


def test_drive_direct_os_profile_os_injector_error_no_fallback(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod
    from koru.autopilot.os_injector import OsInjectorError

    class _Inj:
        session = "wayland"

        def type_text(self, *_a, **_k):
            raise AssertionError("must not fallback when --os-profile is explicit")

    monkeypatch.setattr(cli_command, "Injector", lambda: _Inj())
    monkeypatch.setattr(
        oi_mod,
        "try_drive_with_profile",
        lambda **_k: (_ for _ in ()).throw(OsInjectorError("xdotool timed out")),
    )
    rc = autopilot_main(
        ["drive", "--direct", "--os-profile", "windsurf", "--prompt", "go"],
    )
    assert rc == 1
    err = capsys.readouterr().err
    assert "os-injector failed for requested profile" in err


def test_drive_direct_falls_back_when_os_injector_fails(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod
    from koru.autopilot.injector import InjectionResult
    from koru.autopilot.os_injector import OsInjectorError

    class _Inj:
        session = "wayland"

        def type_text(self, text, *, ide="default", submit=True, dry_run=False):
            return InjectionResult(
                backend="ydotool",
                submitted=submit,
                dry_run=dry_run,
                output=text,
            )

    monkeypatch.setattr(cli_command, "Injector", lambda: _Inj())
    monkeypatch.setattr(
        oi_mod,
        "try_drive_with_profile",
        lambda **_k: (_ for _ in ()).throw(OsInjectorError("xdotool timed out")),
    )
    rc = autopilot_main(["drive", "--direct", "--prompt", "go"])
    assert rc == 0
    err = capsys.readouterr().err
    assert "falling back to keyboard injector" in err


def test_calibrate_auto_ide_resolves_from_running_processes(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru.autopilot import ide as ide_mod
    from koru.autopilot import os_injector as oi_mod
    from koru.autopilot.ide import RunningIDE

    monkeypatch.setattr(cli_command.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi_mod, "capture_mouse_xy", lambda: (9, 9))
    cursor_only = [RunningIDE(id="cursor", label="Cursor", pid=1, exe="/c")]
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda: cursor_only)
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda: None)
    rc = autopilot_main(
        [
            "calibrate",
            "--ide",
            "auto",
            "--delay-seconds",
            "0",
            "--config",
            str(tmp_path / "auto.json"),
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads("\n".join(out.splitlines()[1:]))
    assert payload["profile"] == "cursor"
    assert payload["auto_detected"] is True


def test_calibrate_writes_profile_from_mouse(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setattr(cli_command.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi_mod, "capture_mouse_xy", lambda: (123, 456))
    rc = autopilot_main(
        [
            "calibrate",
            "--ide",
            "windsurf",
            "--delay-seconds",
            "0",
            "--config",
            str(tmp_path / "profiles.json"),
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    # JSON payload is printed after one human instruction line.
    payload = json.loads("\n".join(out.splitlines()[1:]))
    assert payload["profile"] == "windsurf"
    assert payload["chat_x"] == 123
    assert payload["chat_y"] == 456


def test_session_start_explicit_ides(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setattr(cli_command.time, "sleep", lambda _s: None)
    coords = iter([(10, 20), (30, 40)])
    monkeypatch.setattr(oi_mod, "capture_mouse_xy", lambda: next(coords))
    rc = autopilot_main(
        [
            "session-start",
            "--ides",
            "windsurf,cursor",
            "--delay-seconds",
            "0",
            "--config",
            str(tmp_path / "session.json"),
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads("\n".join(line for line in out.splitlines() if not line.startswith("[")))
    assert payload["ok"] is True
    assert [t["ide"] for t in payload["targets"]] == ["windsurf", "cursor"]


def test_session_start_keeps_profile_when_smoke_fails(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru.autopilot import os_injector as oi_mod
    from koru.autopilot.os_injector import OsInjectorError

    monkeypatch.setattr(cli_command.time, "sleep", lambda _s: None)
    monkeypatch.setattr(oi_mod, "capture_mouse_xy", lambda: (10, 20))
    monkeypatch.setattr(
        oi_mod,
        "inject_with_profile",
        lambda **_k: (_ for _ in ()).throw(OsInjectorError("xdotool timed out")),
    )
    rc = autopilot_main(
        [
            "session-start",
            "--ides",
            "windsurf",
            "--delay-seconds",
            "0",
            "--config",
            str(tmp_path / "session.json"),
            "--prompt",
            "smoke",
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads("\n".join(line for line in out.splitlines() if not line.startswith("[")))
    assert payload["ok"] is True
    assert payload["targets"][0]["warning"] == "profile_saved_but_smoke_failed"


def test_session_start_warns_on_duplicate_coordinates(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setattr(cli_command.time, "sleep", lambda _s: None)
    coords = iter([(11, 22), (11, 22)])
    monkeypatch.setattr(oi_mod, "capture_mouse_xy", lambda: next(coords))
    rc = autopilot_main(
        [
            "session-start",
            "--ides",
            "windsurf,cursor",
            "--delay-seconds",
            "0",
            "--config",
            str(tmp_path / "session.json"),
        ],
    )
    assert rc == 0
    out = capsys.readouterr().out
    payload = json.loads("\n".join(line for line in out.splitlines() if not line.startswith("[")))
    assert payload["ok"] is True
    assert "warnings" in payload
    dup = payload["warnings"]["duplicate_coordinates"][0]
    assert dup["chat_x"] == 11
    assert set(dup["ides"]) == {"windsurf", "cursor"}
    assert payload["targets"][0]["warning"] == "shared_coordinates_with_other_ides"


def test_ide_list_empty(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr("koru.autopilot.daemon_cli.detect_running_ides", lambda: [])
    rc = autopilot_main(["ide-list"])
    assert rc == 0
    assert "no IDE processes" in capsys.readouterr().out


def test_ide_list_marks_focused_ide(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "koru.autopilot.daemon_cli.detect_running_ides",
        lambda: [
            SimpleNamespace(id="windsurf", label="Windsurf", pid=10, exe="/opt/windsurf"),
            SimpleNamespace(id="jetbrains", label="JetBrains IDE", pid=20, exe="/opt/idea"),
        ],
    )
    monkeypatch.setattr("koru.autopilot.daemon_cli.detect_focused_ide_id", lambda: "jetbrains")
    rc = autopilot_main(["ide-list"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "windsurf" in out
    assert "jetbrains" in out
    assert "[focused]" in out


def test_doctor_json_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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


def test_doctor_fix_text_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        doctor_cli,
        "doctor_fix_payload",
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


def test_doctor_fix_json_output(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
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
        doctor_cli,
        "doctor_fix_payload",
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

    for key in (
        "CHROME_DESKTOP",
        "GIO_LAUNCHED_DESKTOP_FILE",
        "TERM_PROGRAM_VERSION",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_CWD",
        "VSCODE_IPC_HOOK",
        "VSCODE_NLS_CONFIG",
        "VSCODE_PID",
    ):
        monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setattr(install_plugin_cli, "detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setattr(
        install_plugin_cli.shutil,
        "which",
        lambda name: "/usr/bin/code" if name == "code" else None,
    )
    monkeypatch.setattr(install_plugin_cli, "resolve_plugin_vsix_path", lambda _p: vsix)

    rc = autopilot_main(["install-plugin", "--dry-run", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["ide"] == "vscode"
    assert payload["editor"] == "/usr/bin/code"
    assert payload["vsix"] == str(vsix)
    assert payload["command"][0] == "/usr/bin/code"


def test_install_plugin_vsix_resolver_prefers_package_version(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin_dir = tmp_path / "plugin"
    plugin_dir.mkdir()
    (plugin_dir / "package.json").write_text('{"version":"0.1.15"}', encoding="utf-8")
    stale = plugin_dir / "koru-autopilot-0.1.14.vsix"
    current = plugin_dir / "koru-autopilot-0.1.15.vsix"
    stale.write_text("stale", encoding="utf-8")
    current.write_text("current", encoding="utf-8")
    os.utime(stale, (20, 20))
    os.utime(current, (10, 10))
    monkeypatch.setattr(install_plugin_cli, "plugin_repo_dir", lambda _ide=None: plugin_dir)

    assert install_plugin_cli.resolve_plugin_vsix_path(None) == current.resolve()


def test_install_plugin_auto_detect_ambiguous_running_ides_errors(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("TERM_PROGRAM", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.setattr("koru.autopilot.ide.detect_focused_ide_id", lambda: None)
    monkeypatch.setattr("koru.autopilot.install_plugin_cli.detect_focused_ide_id", lambda: None)
    monkeypatch.setattr(
        "koru.autopilot.install_plugin_cli.detect_terminal_host_ide_id",
        lambda: None,
    )
    monkeypatch.setattr(
        "koru.autopilot.ide.detect_running_ides",
        lambda: [
            SimpleNamespace(id="cursor", label="Cursor", pid=1, exe="/usr/bin/cursor"),
            SimpleNamespace(id="windsurf", label="Windsurf", pid=2, exe="/usr/bin/windsurf"),
        ],
    )
    monkeypatch.setattr(
        "koru.autopilot.install_plugin_cli.detect_running_ides",
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

    monkeypatch.setattr(install_plugin_cli, "resolve_plugin_target_ide", lambda _raw: "cursor")
    monkeypatch.setattr(
        install_plugin_cli,
        "resolve_plugin_editor_bin",
        lambda _ide: "/usr/bin/cursor",
    )
    monkeypatch.setattr(install_plugin_cli, "resolve_plugin_vsix_path", lambda _p: vsix)

    def _fake_run(cmd, capture_output, text, check):
        assert cmd[0] == "/usr/bin/cursor"
        return install_plugin_cli.subprocess.CompletedProcess(cmd, 0, stdout="ok", stderr="")

    monkeypatch.setattr(install_plugin_cli.subprocess, "run", _fake_run)

    rc = autopilot_main(["install-plugin", "--ide", "cursor", "--format", "json", "--force"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["returncode"] == 0
    assert payload["ide"] == "cursor"
    assert payload["command"][-1] == "--force"


def test_install_plugin_vscodium_dry_run_uses_codium_cli(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    vsix = tmp_path / "koru-autopilot-0.1.0.vsix"
    vsix.write_text("fake", encoding="utf-8")
    monkeypatch.setattr(
        install_plugin_cli.shutil,
        "which",
        lambda name: "/usr/bin/codium" if name == "codium" else None,
    )
    monkeypatch.setattr(install_plugin_cli, "resolve_plugin_vsix_path", lambda _p: vsix)

    rc = autopilot_main(["install-plugin", "--ide", "vscodium", "--dry-run", "--format", "json"])

    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ide"] == "vscodium"
    assert payload["editor"] == "/usr/bin/codium"


def test_install_plugin_zed_reports_vsix_plugin_unsupported(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = autopilot_main(["install-plugin", "--ide", "zed", "--dry-run"])
    assert rc == 1
    assert "zed does not support the VS Code VSIX plugin" in capsys.readouterr().err


def test_install_plugin_pycharm_alias_maps_to_jetbrains(
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = autopilot_main(["install-plugin", "--ide", "pycharm", "--dry-run"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "jetbrains plugin install is not supported" in err


def test_install_plugin_jetbrains_dry_run_json(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin_dir = tmp_path / "koru-autopilot-jetbrains"
    plugin_dir.mkdir()
    monkeypatch.setattr(install_plugin_cli, "resolve_jetbrains_plugin_dir", lambda _p: plugin_dir)
    monkeypatch.setattr(
        install_plugin_cli,
        "resolve_gradle_bin",
        lambda _p: (_ for _ in ()).throw(AssertionError("dry-run must not resolve gradle binary")),
    )

    rc = autopilot_main(
        [
            "install-plugin-jetbrains",
            "--dry-run",
            "--format",
            "json",
            "--gradle-bin",
            "/path/to/gradle",
        ]
    )
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["dry_run"] is True
    assert payload["plugin_dir"] == str(plugin_dir)
    assert payload["command"] == ["/path/to/gradle", "buildPlugin"]


def test_install_plugin_jetbrains_success_json_payload(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    plugin_dir = tmp_path / "koru-autopilot-jetbrains"
    plugin_dir.mkdir()
    artifact = plugin_dir / "build" / "distributions" / "koru-autopilot.zip"
    artifact.parent.mkdir(parents=True)
    artifact.write_text("fake", encoding="utf-8")

    monkeypatch.setattr(install_plugin_cli, "resolve_jetbrains_plugin_dir", lambda _p: plugin_dir)
    monkeypatch.setattr(install_plugin_cli, "resolve_gradle_bin", lambda _p: "/usr/bin/gradle")
    monkeypatch.setattr(
        install_plugin_cli,
        "resolve_jetbrains_plugin_artifact",
        lambda _p: artifact,
    )

    def _fake_run(cmd, cwd, capture_output, text, check):
        assert cmd == ["/usr/bin/gradle", "buildPlugin"]
        assert cwd == str(plugin_dir)
        return install_plugin_cli.subprocess.CompletedProcess(cmd, 0, stdout="built", stderr="")

    monkeypatch.setattr(install_plugin_cli.subprocess, "run", _fake_run)

    rc = autopilot_main(["install-plugin-jetbrains", "--format", "json"])
    assert rc == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["ok"] is True
    assert payload["plugin_dir"] == str(plugin_dir)
    assert payload["artifact"] == str(artifact)
    assert payload["command"] == ["/usr/bin/gradle", "buildPlugin"]


def test_install_plugin_auto_detects_pycharm_hosted_as_jetbrains(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("PYCHARM_HOSTED", "1")
    rc = autopilot_main(["install-plugin", "--dry-run"])
    assert rc == 1
    err = capsys.readouterr().err
    assert "jetbrains plugin install is not supported" in err


def test_status_when_no_daemon(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "status"])
    assert rc == 1
    assert "NOT running" in capsys.readouterr().out


def test_status_accepts_legacy_json_flag(
    capsys: pytest.CaptureFixture[str],
    tmp_path: Path,
) -> None:
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(["--socket", str(socket), "status", "--json"])
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
    monkeypatch.setattr(handoff, "_build_brief", lambda _p, **kw: "# fake brief\n\nhi")
    rc = autopilot_main(
        [
            "handoff",
            "--dry-run",
            "--project",
            str(tmp_path),
        ]
    )
    assert rc == 0
    out = capsys.readouterr().out
    assert "# fake brief" in out


def test_handoff_requires_running_daemon(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(handoff, "_build_brief", lambda _p, **kw: "# brief")
    socket = tmp_path / "missing.sock"
    rc = autopilot_main(
        [
            "--socket",
            str(socket),
            "handoff",
            "--project",
            str(tmp_path),
        ]
    )
    assert rc == 2
    assert "daemon not running" in capsys.readouterr().err


def test_handoff_drives_brief_through_client(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Happy path: build_brief + daemon up → client.drive called with the brief."""

    monkeypatch.setattr(handoff, "_build_brief", lambda _p, **kw: "# the brief")

    class _FakeClient:
        def __init__(self, *_a, **_kw) -> None:
            self.drive_called_with: dict | None = None

        def is_running(self) -> bool:
            return True

        def drive(self, text, *, submit=True, ide="auto", require_plugin=False):
            self.drive_called_with = {
                "text": text,
                "submit": submit,
                "ide": ide,
                "require_plugin": require_plugin,
            }
            return {"ok": True, "delivered": True, "type": "ack"}

    fake = _FakeClient()
    monkeypatch.setattr(cli_command, "AutopilotClient", lambda *a, **k: fake)
    rc = autopilot_main(["handoff", "--project", str(tmp_path)])
    assert rc == 0
    assert fake.drive_called_with["text"] == "# the brief"
    assert fake.drive_called_with["submit"] is True
    assert fake.drive_called_with["ide"] == "auto"
    assert fake.drive_called_with["require_plugin"] is False
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
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(
        log,
        [
            {"ts": "2026-05-11T18:30:01.000Z", "event": "daemon_started", "socket": "/tmp/x"},
            {
                "ts": "2026-05-11T18:30:05.000Z",
                "event": "drive",
                "ide": "windsurf",
                "backend": "plugin",
                "chars": 29,
                "submit": True,
                "ok": True,
            },
        ],
    )
    rc = autopilot_main(["tail", "--log", str(log)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "daemon_started" in out
    assert "drive" in out
    assert "windsurf" in out
    assert "backend=plugin" in out
    assert "chars=29" in out


def test_tail_json_format_returns_array(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(
        log,
        [
            {"ts": "t1", "event": "drive", "ide": "windsurf"},
            {"ts": "t2", "event": "drive", "ide": "vscode"},
        ],
    )
    rc = autopilot_main(["tail", "--log", str(log), "--format", "json"])
    assert rc == 0
    data = json.loads(capsys.readouterr().out)
    assert [e["ide"] for e in data] == ["windsurf", "vscode"]


def test_tail_n_limits_output(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    log = tmp_path / "audit.log"
    _write_audit_log(
        log, [{"ts": f"t{i}", "event": "drive", "ide": "x", "chars": i} for i in range(10)]
    )
    rc = autopilot_main(["tail", "--log", str(log), "-n", "3"])
    assert rc == 0
    lines = capsys.readouterr().out.strip().splitlines()
    assert len(lines) == 3
    # Last 3 entries
    assert "chars=7" in lines[0]
    assert "chars=9" in lines[2]


def test_tail_missing_log_errors_cleanly(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    rc = autopilot_main(["tail", "--log", str(tmp_path / "nope.log")])
    assert rc == 1
    assert "no log at" in capsys.readouterr().err


def test_tail_skips_malformed_lines(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
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
    monkeypatch.setattr(systemd_cli, "resolve_koru_bin", lambda: "/opt/koru/bin/koru")
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
    monkeypatch.setattr(systemd_cli, "resolve_koru_bin", lambda: "/usr/bin/koru")
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

    monkeypatch.setattr(systemd_cli.shutil, "which", lambda _name: None)
    monkeypatch.setattr(systemd_cli.sys, "executable", str(py))

    assert systemd_cli.resolve_koru_bin() == str(koru)
