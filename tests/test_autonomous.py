"""Tests for `koru autonomous` one-command loop."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from koru import autonomous as autonomous_mod
from koru import autonomous_env as autonomous_env_mod
from koru import autonomous_wup as autonomous_wup_mod
from koru.queue.types import QueueLoopResult
from koru.scan import ScanResult


def test_effective_flags_matrix() -> None:
    assert autonomous_env_mod.effective_ticket_source_flags("queue") == (False, False)
    assert autonomous_env_mod.effective_ticket_source_flags("scan") == (True, False)
    assert autonomous_env_mod.effective_ticket_source_flags("all") == (True, True)
    assert autonomous_mod._effective_flags("queue") == (False, False)


def test_scan_after_idle_queue_runs_scan_when_queue_idle(tmp_path, monkeypatch) -> None:
    calls: list[dict] = []

    def spy_run_scan(**kwargs):
        calls.append(kwargs)
        return ScanResult(suggestions=[], applied=[], skipped=[])

    monkeypatch.setattr(autonomous_mod, "run_scan", spy_run_scan)
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        ),
    )
    autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="t",
        queue_name=None,
        enable_scan=False,
        max_iterations=1,
        enable_autopilot=False,
        autopilot_ide="auto",
        drive_prompt="",
        submit=True,
        include_semcod_artifacts=None,
        client=None,
        state=autonomous_mod.AutoloopState(),
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=None,
        wup_watch_enabled=False,
        wup_diagnostic_tickets=False,
        wup_ticket_queue="default",
        strict_diagnostics=False,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        scan_skip_if_clean=False,
        scan_skip_after=1,
        scan_after_idle_queue=True,
        topology_integration=False,
        stdio_format="human",
        correlation_id="idle-scan-test",
    )
    assert len(calls) == 1
    assert calls[0]["apply"] is True


def test_scan_after_idle_min_interval_skips_second_scan(tmp_path, monkeypatch) -> None:
    calls: list[dict] = []

    def spy_run_scan(**kwargs):
        calls.append(kwargs)
        return ScanResult(suggestions=[], applied=[], skipped=[])

    monkeypatch.setattr(autonomous_mod, "run_scan", spy_run_scan)
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        ),
    )
    clock = [0.0]

    def fake_time() -> float:
        return clock[0]

    monkeypatch.setattr(autonomous_mod.time, "time", fake_time)
    common = dict(
        project=tmp_path,
        actor="t",
        queue_name=None,
        enable_scan=False,
        max_iterations=1,
        enable_autopilot=False,
        autopilot_ide="auto",
        drive_prompt="",
        submit=True,
        include_semcod_artifacts=None,
        client=None,
        state=autonomous_mod.AutoloopState(),
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=None,
        wup_watch_enabled=False,
        wup_diagnostic_tickets=False,
        wup_ticket_queue="default",
        strict_diagnostics=False,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        scan_skip_if_clean=False,
        scan_skip_after=1,
        scan_after_idle_queue=True,
        scan_after_idle_min_interval_seconds=60.0,
        topology_integration=False,
        stdio_format="human",
        correlation_id="rate-limit-test",
    )
    autonomous_mod._run_cycle(cycle=1, **common)
    assert len(calls) == 1
    clock[0] = 30.0
    autonomous_mod._run_cycle(cycle=2, **common)
    assert len(calls) == 1
    clock[0] = 100.0
    autonomous_mod._run_cycle(cycle=3, **common)
    assert len(calls) == 2


def test_idle_streak_skip_increments_telemetry(tmp_path, monkeypatch) -> None:
    driven: list[str] = []

    class RecordingClient:
        def drive(self, prompt: str, **_kwargs):
            driven.append(prompt)
            return {"ok": True, "backend": "test"}

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=[],
            last_status="idle",
            last_message="",
            last_ticket_id=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod, "run_scan", lambda **kwargs: ScanResult([], [], []))
    st = autonomous_mod.AutoloopState()
    common = dict(
        project=tmp_path,
        actor="t",
        queue_name=None,
        enable_scan=False,
        max_iterations=1,
        enable_autopilot=True,
        autopilot_ide="auto",
        drive_prompt="go",
        submit=True,
        include_semcod_artifacts=None,
        client=RecordingClient(),
        state=st,
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=None,
        wup_watch_enabled=False,
        wup_diagnostic_tickets=False,
        wup_ticket_queue="default",
        strict_diagnostics=False,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_drive_idle_streak=1,
        autopilot_skip_statuses="waiting_input",
        scan_skip_if_clean=False,
        scan_skip_after=1,
        scan_after_idle_queue=False,
        scan_after_idle_min_interval_seconds=0.0,
        topology_integration=False,
        stdio_format="human",
        correlation_id="idle-streak-telemetry",
    )
    autonomous_mod._run_cycle(cycle=1, **common)
    assert len(driven) == 1
    assert st.telemetry_autopilot_idle_streak_skips == 0
    autonomous_mod._run_cycle(cycle=2, **common)
    assert len(driven) == 1
    assert st.telemetry_autopilot_idle_streak_skips == 1


def test_ticket_sources_env_overrides_cli_queue_to_scan(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TICKET_SOURCES", "scan")
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    scan_calls: list[dict] = []

    def spy_run_scan(**kwargs):
        scan_calls.append(kwargs)
        return ScanResult(suggestions=[], applied=[], skipped=[])

    monkeypatch.setattr(autonomous_mod, "run_scan", spy_run_scan)
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ],
    )
    assert rc == 0
    assert len(scan_calls) == 1


def test_ticket_sources_env_invalid_keeps_cli_queue(tmp_path, monkeypatch, capsys) -> None:
    monkeypatch.setenv("TICKET_SOURCES", "bogus")
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    scan_calls: list[dict] = []

    def spy_run_scan(**kwargs):
        scan_calls.append(kwargs)
        return ScanResult(suggestions=[], applied=[], skipped=[])

    monkeypatch.setattr(autonomous_mod, "run_scan", spy_run_scan)
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ],
    )
    assert rc == 0
    assert scan_calls == []
    err = capsys.readouterr().err
    assert "unknown TICKET_SOURCES" in err


def test_autonomous_environ_doctor_probe_invalid_ticket_sources(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TICKET_SOURCES", "nope")
    status, detail = autonomous_env_mod.autonomous_environ_doctor_probe(tmp_path)
    assert status == "fail"
    assert "invalid" in detail


def test_autonomous_environ_doctor_probe_pass_summary(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("TICKET_SOURCES", raising=False)
    monkeypatch.delenv("WUP_MODE", raising=False)
    monkeypatch.delenv("IDLE_DIAGNOSTICS_PROFILE", raising=False)
    monkeypatch.delenv("ENABLE_IDLE_DIAGNOSTICS", raising=False)
    monkeypatch.delenv("ENABLE_DIAGNOSTIC_TICKETS", raising=False)
    monkeypatch.setenv("WUP_MODE", "testql")
    status, detail = autonomous_env_mod.autonomous_environ_doctor_probe(tmp_path)
    assert status == "pass"
    assert "TICKET_SOURCES unset" in detail
    assert "WUP_MODE=testql" in detail


def test_looks_like_autonomous_matches_koru_cli_auto() -> None:
    assert autonomous_mod._looks_like_autonomous_up_command(
        "python3 -m koru.cli auto --project /tmp/x",
    )


def test_looks_like_autonomous_matches_koru_autonomous_regex() -> None:
    assert autonomous_mod._looks_like_autonomous_up_command(
        "python3 -m koru.cli autonomous up --project /tmp",
    )


def test_auto_main_argv_injects_replace_existing(tmp_path: Path) -> None:
    from koru.cli import _auto_main

    calls: list[list[str]] = []
    stopped: list[Path] = []

    def fake_stop(project: Path, **kwargs: object) -> None:
        stopped.append(project)

    def fake_autonomous(argv: list[str], *, invoked_as_auto: bool = False) -> int:
        calls.append(list(argv))
        return 0

    with patch(
        "koru._legacy_cli_impl.stop_prior_autonomous_for_auto_start",
        side_effect=fake_stop,
    ):
        with patch(
            "koru._legacy_cli_impl.autonomous_main",
            side_effect=fake_autonomous,
        ):
            assert _auto_main(["--project", str(tmp_path)]) == 0

    assert stopped == [tmp_path.resolve()]
    assert calls
    assert "--replace-existing" in calls[0]


def test_stop_prior_autonomous_for_auto_start_terminates(tmp_path, monkeypatch) -> None:
    existing = [
        autonomous_mod.ExistingAutonomousProcess(
            pid=99,
            command="python3 -m koru.cli auto --project " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project, any_project=False: existing if any_project else [],
    )
    monkeypatch.setattr(autonomous_mod, "_find_existing_wup_processes", lambda project: [])
    monkeypatch.setattr(
        autonomous_mod,
        "_terminate_existing_processes",
        lambda processes, **kwargs: stopped.extend(proc.pid for proc in processes),
    )
    autonomous_mod.stop_prior_autonomous_for_auto_start(tmp_path)
    assert stopped == [99]


def test_guard_existing_autonomous_noninteractive_blocks_duplicate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            autonomous_mod.ExistingAutonomousProcess(
                pid=123,
                command="koru autonomous up --project " + str(tmp_path),
                cwd=tmp_path,
            ),
        ],
    )
    args = SimpleNamespace(
        allow_duplicate=False,
        replace_existing=False,
        emit_events="human",
    )

    rc = autonomous_mod._guard_existing_autonomous_processes(args, tmp_path)

    assert rc == 2


def test_guard_existing_autonomous_replace_existing_terminates(tmp_path, monkeypatch) -> None:
    existing = [
        autonomous_mod.ExistingAutonomousProcess(
            pid=123,
            command="koru autonomous up --project " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project: existing,
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_terminate_existing_processes",
        lambda processes, **kwargs: stopped.extend(proc.pid for proc in processes),
    )
    args = SimpleNamespace(
        allow_duplicate=False,
        replace_existing=True,
        emit_events="human",
    )

    rc = autonomous_mod._guard_existing_autonomous_processes(args, tmp_path)

    assert rc == 0
    assert stopped == [123]


def test_guard_existing_autonomous_replace_existing_terminates_stale_wup(
    tmp_path,
    monkeypatch,
) -> None:
    wup = [
        autonomous_mod.ExistingManagedProcess(
            pid=456,
            kind="wup-watch",
            command="wup watch " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(autonomous_mod, "_find_existing_autonomous_processes", lambda project: [])
    monkeypatch.setattr(autonomous_mod, "_find_existing_wup_processes", lambda project: wup)
    monkeypatch.setattr(
        autonomous_mod,
        "_terminate_existing_processes",
        lambda processes, **kwargs: stopped.extend(proc.pid for proc in processes),
    )
    args = SimpleNamespace(
        allow_duplicate=False,
        replace_existing=True,
        emit_events="human",
    )

    rc = autonomous_mod._guard_existing_autonomous_processes(args, tmp_path)

    assert rc == 0
    assert stopped == [456]


def test_guard_existing_autonomous_interactive_decline_blocks_duplicate(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            autonomous_mod.ExistingAutonomousProcess(
                pid=123,
                command="koru autonomous up --project " + str(tmp_path),
                cwd=tmp_path,
            ),
        ],
    )
    monkeypatch.setattr(autonomous_mod.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
    args = SimpleNamespace(
        allow_duplicate=False,
        replace_existing=False,
        emit_events="human",
    )

    rc = autonomous_mod._guard_existing_autonomous_processes(args, tmp_path)

    assert rc == 2


def test_autonomous_jsonl_keyboard_interrupt_emits_reason(tmp_path, monkeypatch) -> None:
    """AutonomousStopped must distinguish SIGTERM (handled elsewhere) from Ctrl+C."""
    import contextlib
    import io

    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_scan",
        lambda **kwargs: ScanResult(suggestions=[], applied=[], skipped=[]),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    n_sleep = 0

    def sleep_side(_s: float) -> None:
        nonlocal n_sleep
        n_sleep += 1
        if n_sleep == 1:
            raise KeyboardInterrupt()

    monkeypatch.setattr(autonomous_mod.time, "sleep", sleep_side)
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        rc = autonomous_mod.autonomous_main(
            [
                "up",
                "--project",
                str(tmp_path),
                "--max-cycles",
                "0",
                "--sleep-seconds",
                "1",
                "--emit-events",
                "jsonl",
                "--no-autopilot",
                "--no-wup-watch",
            ],
        )
    assert rc == 0
    events = [json.loads(line) for line in buf.getvalue().splitlines() if line.strip()]
    stopped = [e for e in events if e.get("type") == "AutonomousStopped"]
    assert stopped
    assert stopped[-1]["payload"]["reason"] == "keyboard_interrupt"


def test_queue_loop_result_summary_includes_waiting_ticket() -> None:
    empty = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
    )
    assert "waiting_ticket=none" in empty.summary()
    one = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-001"],
        last_status="waiting_input",
        last_message="?",
    )
    assert "waiting_ticket=PLF-001" in one.summary()


def test_queue_loop_waiting_ticket_label_helper() -> None:
    r = QueueLoopResult(1, [], [], ["PLF-A", "PLF-B"], "waiting_input", "")
    assert autonomous_mod._queue_loop_waiting_ticket_label(r) == "PLF-B"


def test_resolve_autopilot_ide_env_overrides_cli(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "cursor"
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "vscode"


def test_resolve_autopilot_ide_ignores_bad_env(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "not-a-real-ide")
    assert autonomous_mod._resolve_autopilot_ide("jetbrains") == "jetbrains"


def test_resolve_autopilot_ide_auto_env_does_not_override_cli(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "auto")
    assert autonomous_mod._resolve_autopilot_ide("cursor") == "cursor"


def test_resolve_autopilot_ide_headless_forces_auto(monkeypatch) -> None:
    monkeypatch.setenv("KORU_HEADLESS", "1")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "auto"


def test_resolve_autopilot_ide_headless_allow_autopilot_honors_env(monkeypatch) -> None:
    monkeypatch.setenv("KORU_HEADLESS", "1")
    monkeypatch.setenv("KORU_HEADLESS_ALLOW_AUTOPILOT", "1")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "cursor"


def test_resolve_autopilot_ide_koru_ide_mode_headless(monkeypatch) -> None:
    monkeypatch.setenv("KORU_IDE_MODE", "headless")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "cursor")
    assert autonomous_mod._resolve_autopilot_ide("vscode") == "auto"


@pytest.mark.skipif(sys.platform == "win32", reason="SSH+DISPLAY heuristic is POSIX-specific")
def test_resolve_autopilot_ide_ssh_without_display_headless(monkeypatch) -> None:
    monkeypatch.delenv("DISPLAY", raising=False)
    monkeypatch.setenv("SSH_CONNECTION", "127.0.0.1 1 127.0.0.1 22")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    assert autonomous_mod._resolve_autopilot_ide("cursor") == "auto"


@pytest.mark.skipif(sys.platform == "win32", reason="SSH+DISPLAY heuristic is POSIX-specific")
def test_resolve_autopilot_ide_ssh_with_display_uses_cli(monkeypatch) -> None:
    monkeypatch.setenv("SSH_CONNECTION", "127.0.0.1 1 127.0.0.1 22")
    monkeypatch.setenv("DISPLAY", ":0")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    assert autonomous_mod._resolve_autopilot_ide("zed") == "zed"


def test_resolve_autopilot_ide_os_environ_autopilot_ide(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "vscode")
    monkeypatch.delenv("KORU_HEADLESS", raising=False)
    monkeypatch.delenv("KORU_IDE_MODE", raising=False)
    assert autonomous_mod._resolve_autopilot_ide("auto") == "vscode"


def test_resolve_autopilot_ide_headless_allow_yes(monkeypatch) -> None:
    monkeypatch.setenv("KORU_HEADLESS", "1")
    monkeypatch.setenv("KORU_HEADLESS_ALLOW_AUTOPILOT", "yes")
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "zed")
    assert autonomous_mod._resolve_autopilot_ide("cursor") == "zed"


def _isolate_integrated_terminal_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Drop IDE terminal env leaked from the host (Cursor sets VSCODE_* + CURSOR_*)."""
    for key in (
        "KORU_AUTOPILOT_INSTANCE",
        "KORU_AUTOPILOT_IDE",
        "CURSOR_AGENT",
        "CURSOR_CLI",
        "CHROME_DESKTOP",
        "WINDSURF_CSRF_TOKEN",
        "WINDSURF_VERSION",
        "TERM_PROGRAM",
        "VSCODE_PID",
        "VSCODE_NLS_CONFIG",
        "VSCODE_IPC_HOOK",
        "VSCODE_CODE_CACHE_PATH",
        "VSCODE_CWD",
    ):
        monkeypatch.delenv(key, raising=False)


def test_apply_agent_lane_environ_auto_cursor(tmp_path, monkeypatch) -> None:
    _isolate_integrated_terminal_env(monkeypatch)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    (tmp_path / ".cursor").mkdir()
    with (
        patch("koru.autonomous_startup.detect_running_ides", return_value=[]),
        patch("koru.autonomous_startup.detect_terminal_host_ide_id", return_value=None),
    ):
        lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "cursor"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "cursor"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)


def test_apply_agent_lane_environ_auto_prefers_vscode_terminal(tmp_path, monkeypatch) -> None:
    _isolate_integrated_terminal_env(monkeypatch)
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "{}")
    (tmp_path / ".windsurf").mkdir()
    with patch("koru.autonomous_startup.detect_running_ides", return_value=[]):
        lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "vscode"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscode"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "vscode"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)


def test_apply_agent_lane_environ_auto_vscode_terminal_overrides_stale_windsurf_env(
    tmp_path,
    monkeypatch,
) -> None:
    _isolate_integrated_terminal_env(monkeypatch)
    monkeypatch.setenv("KORU_AUTOPILOT_IDE", "windsurf")
    monkeypatch.setenv("VSCODE_IPC_HOOK", "/run/user/1000/vscode-ipc.sock")
    (tmp_path / ".windsurf").mkdir()

    with patch("koru.autonomous_startup.detect_running_ides", return_value=[]):
        lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")

    assert lane == "vscode"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscode"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "vscode"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)


def test_apply_agent_lane_environ_none_is_noop(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "keep-me")
    lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "none")
    assert lane is None
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "keep-me"


def test_autonomous_main_prepends_up_for_flags(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ],
    )
    assert rc == 0


def test_up_single_cycle_queue_only_no_autopilot(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )

    queue_calls: list[dict] = []

    def fake_queue_loop(**kwargs):
        queue_calls.append(kwargs)
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        )

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
        ],
    )

    assert rc == 0
    assert len(queue_calls) == 1
    assert queue_calls[0]["queue_name"] == "default"


def test_safe_up_uses_queue_diagnostics_without_autopilot(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )

    queue_calls: list[dict] = []
    diagnostic_calls: list[dict] = []

    def fake_queue_loop(**kwargs):
        queue_calls.append(kwargs)
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        )

    def fake_idle_diagnostics(**kwargs):
        diagnostic_calls.append(kwargs)
        return autonomous_mod.DiagnosticResult(status="ok", failed=[])

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(autonomous_mod, "_run_idle_diagnostics", fake_idle_diagnostics)
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "safe-up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--sleep-seconds",
            "0",
            "--agent-lane",
            "none",
        ],
    )

    assert rc == 0
    assert len(queue_calls) == 1
    assert queue_calls[0]["queue_name"] == "default"
    assert len(diagnostic_calls) == 1
    assert diagnostic_calls[0]["profile"] == "quick"
    assert diagnostic_calls[0]["diagnostic_tickets"] is True


def test_up_single_cycle_all_sources_runs_scan(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_scan",
        lambda **kwargs: ScanResult(suggestions=[], applied=[], skipped=[]),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "all",
            "--no-autopilot",
        ],
    )

    assert rc == 0


def test_up_auto_installs_plugin_before_autopilot_loop(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        ),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    install_calls: list[str] = []

    def fake_install_plugin_for_ide(*, ide, socket_path):
        install_calls.append(f"{ide}:{socket_path.name}")
        return SimpleNamespace(status="installed", ide=ide, message="ok", command=None)

    class FakeClient:
        def status(self):
            return {"plugins": [{"ide": "cursor", "version": "0.1.14"}]}

        def drive(self, *_args, **_kwargs):
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(autonomous_mod, "install_plugin_for_ide", fake_install_plugin_for_ide)
    monkeypatch.setattr(
        autonomous_mod,
        "format_plugin_install_result",
        lambda result: f"plugin {result.status} {result.ide}",
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_start_or_reuse_daemon",
        lambda **kwargs: (FakeClient(), None, None),
    )
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "1",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--agent-lane",
            "none",
            "--autopilot-ide",
            "cursor",
        ],
    )

    assert rc == 0
    assert install_calls == ["cursor:koru-autopilot.sock"]
    assert "KORU_STRICT_PLUGIN_VERSION" not in os.environ


def test_setup_autopilot_plugin_unsupported_skips_wait(tmp_path, monkeypatch) -> None:
    args = SimpleNamespace(
        enable_autopilot=True,
        emit_events="human",
        autopilot_plugin_wait_seconds=5.0,
    )

    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(
            status="unsupported",
            ide="jetbrains",
            message="no plugin",
            command=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod, "format_plugin_install_result", lambda _r: "unsupported")
    monkeypatch.setattr(
        autonomous_mod,
        "_wait_for_autopilot_plugin",
        lambda *_a, **_k: (_ for _ in ()).throw(AssertionError("wait should not be called")),
    )

    connected = autonomous_mod._setup_autopilot_plugin(
        args,
        "jetbrains",
        tmp_path / "koru-autopilot.sock",
        client=object(),
    )

    assert connected is False


def test_status_has_autopilot_plugin_matches_specific_ide(monkeypatch) -> None:
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)

    assert autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "vscode"}, {"ide": "windsurf"}]},
        "vscode",
    )
    assert not autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "windsurf"}]},
        "vscode",
    )


def test_status_has_autopilot_plugin_rejects_stale_plugin_when_strict(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(
        autonomous_mod.DriveOrchestrator,
        "expected_plugin_version",
        lambda: "0.1.14",
    )

    assert not autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "vscode", "version": "0.1.13"}]},
        "vscode",
    )
    assert not autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "vscode"}]},
        "vscode",
    )
    assert autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "vscode", "version": "0.1.14"}]},
        "vscode",
    )


def test_autonomous_defaults_to_strict_plugin_version(monkeypatch) -> None:
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")
    messages: list[str] = []
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda message, **_kwargs: messages.append(message),
    )

    autonomous_mod._enable_autonomous_strict_plugin_version(args)

    assert os.environ["KORU_STRICT_PLUGIN_VERSION"] == "1"
    assert any("strict plugin version policy enabled" in message for message in messages)
    os.environ.pop("KORU_STRICT_PLUGIN_VERSION", None)


def test_autonomous_respects_explicit_plugin_version_policy(monkeypatch) -> None:
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "0")
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("no log")),
    )

    autonomous_mod._enable_autonomous_strict_plugin_version(args)

    assert os.environ["KORU_STRICT_PLUGIN_VERSION"] == "0"


def test_wait_for_autopilot_plugin_polls_until_connected(monkeypatch) -> None:
    sleeps: list[float] = []
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)

    class FakeClient:
        def __init__(self) -> None:
            self.calls = 0

        def status(self):
            self.calls += 1
            if self.calls == 1:
                return {"plugins": []}
            return {"plugins": [{"ide": "vscode"}]}

    ticks = iter([0.0, 0.1, 0.2])
    monkeypatch.setattr(autonomous_mod.time, "monotonic", lambda: next(ticks))
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda seconds: sleeps.append(seconds))

    assert autonomous_mod._wait_for_autopilot_plugin(
        FakeClient(),
        "vscode",
        timeout_seconds=1.0,
        interval_seconds=0.25,
    )
    assert sleeps == [0.25]


def test_start_or_reuse_daemon_reuses_current_version(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(autonomous_mod, "_current_koru_version", lambda: "1.2.3")

    class FakeClient:
        def is_running(self):
            return True

        def status(self):
            return {"daemon_version": "1.2.3"}

    starts: list[str] = []
    monkeypatch.setattr(autonomous_mod, "build_ide_client", lambda **_kwargs: FakeClient())
    monkeypatch.setattr(
        autonomous_mod,
        "AutopilotDaemon",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must reuse daemon")),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda message, **_kwargs: starts.append(message),
    )

    client, daemon, thread = autonomous_mod._start_or_reuse_daemon(
        project=tmp_path,
        socket_path=tmp_path / "koru.sock",
    )

    assert isinstance(client, FakeClient)
    assert daemon is None
    assert thread is None
    assert any("reusing autopilot daemon" in line for line in starts)


def test_start_or_reuse_daemon_restarts_daemon_without_version(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(autonomous_mod, "_current_koru_version", lambda: "1.2.3")

    class FakeClient:
        shutdowns = 0

        def __init__(self) -> None:
            self.status_calls = 0

        def is_running(self):
            return FakeClient.shutdowns == 0

        def status(self):
            return {"plugins": []}

        def shutdown(self):
            FakeClient.shutdowns += 1
            return {"ok": True}

    class FakeDaemon:
        def __init__(self, **_kwargs) -> None:
            self.started = False

        def start(self):
            self.started = True

        def serve_forever(self):
            return None

    class FakeThread:
        def __init__(self, target, daemon) -> None:
            self.target = target
            self.daemon = daemon
            self.started = False

        def start(self):
            self.started = True

    messages: list[str] = []
    monkeypatch.setattr(autonomous_mod, "build_ide_client", lambda **_kwargs: FakeClient())
    monkeypatch.setattr(autonomous_mod, "AutopilotDaemon", FakeDaemon)
    monkeypatch.setattr(autonomous_mod.threading, "Thread", FakeThread)
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda message, **_kwargs: messages.append(message),
    )

    client, daemon, thread = autonomous_mod._start_or_reuse_daemon(
        project=tmp_path,
        socket_path=tmp_path / "koru.sock",
    )

    assert isinstance(client, FakeClient)
    assert isinstance(daemon, FakeDaemon)
    assert daemon.started is True
    assert isinstance(thread, FakeThread)
    assert thread.started is True
    assert FakeClient.shutdowns == 1
    assert any("restarting stale autopilot daemon" in line for line in messages)


def test_run_cycle_sends_fallback_prompt_when_waiting_input_empty_message(
    tmp_path,
    monkeypatch,
) -> None:
    """waiting_input + empty message: send a fallback prompt instead of no-op.

    Previous behaviour was to skip silently ('blocked_empty_message'), causing
    tickets to stall forever. Now we send a generic continue-prompt so the IDE
    LLM at least picks the next ticket. Repeated stagnation is still guarded
    by ``autopilot_skip_statuses`` + ``stagnation_streak``.
    """
    drive_calls: list[tuple[str, dict]] = []

    class RecordingClient:
        def drive(self, prompt, **kwargs):
            drive_calls.append((prompt, kwargs))
            return {"ok": True, "message": "sent", "backend": "test"}

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="",
        ),
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="auto",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=True,
        client=RecordingClient(),
    )

    assert queue_result.last_status == "waiting_input"
    assert autopilot_status == "ok"
    assert len(drive_calls) == 1
    assert drive_calls[0][1]["require_plugin"] is True
    sent_prompt = drive_calls[0][0]
    # Fallback prompt asks IDE to pick next ticket / update status
    assert "next" in sent_prompt.lower() or "continue" in sent_prompt.lower()


def test_run_cycle_autopilot_waiting_input_logs_ticket_from_waiting_list(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """QueueLoopResult has no ticket_id; use ``waiting`` for the status line."""
    driven: list[str] = []

    class RecordingClient:
        def drive(self, prompt: str, **_kwargs):
            driven.append(prompt)
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="answer this prompt",
            waiting=["PLF-999"],
        ),
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="windsurf",
        drive_prompt="ignored when blocked",
        submit=True,
        include_semcod_artifacts=False,
        client=RecordingClient(),
    )

    assert queue_result.last_status == "waiting_input"
    assert autopilot_status == "ok"
    assert driven == ["answer this prompt"]
    out = capsys.readouterr().out
    assert "ticket=PLF-999" in out
    assert "backend=plugin" in out


def test_run_cycle_escalates_stuck_waiting_input_instead_of_skipping(
    tmp_path,
    monkeypatch,
) -> None:
    driven: list[str] = []

    class RecordingClient:
        def drive(self, prompt: str, **_kwargs):
            driven.append(prompt)
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="original ticket prompt",
            waiting=["PLF-1305"],
        ),
    )
    state = autonomous_mod.AutoloopState(
        previous_signature="waiting_input:PLF-1305",
        stagnation_streak=2,
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=4,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="ignored when blocked",
        submit=True,
        include_semcod_artifacts=False,
        client=RecordingClient(),
        state=state,
    )

    assert queue_result.last_status == "waiting_input"
    assert autopilot_status == "ok"
    assert len(driven) == 1
    assert "Ticket PLF-1305 has been stuck" in driven[0]
    assert "original ticket prompt" in driven[0]
    assert state.stagnation_streak == 0


def test_run_cycle_drives_llm_ready_waiting_ticket_without_stagnation_skip(
    tmp_path,
    monkeypatch,
) -> None:
    """llm-ready tickets should be driven by IDE autopilot even when human queue waits."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-1321:
      labels: [llm-ready, refactor]
""",
        encoding="utf-8",
    )
    driven: list[str] = []

    class RecordingClient:
        def drive(self, prompt: str, **_kwargs):
            driven.append(prompt)
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="remove duplicated classes",
            waiting=["PLF-1321"],
        ),
    )
    state = autonomous_mod.AutoloopState(
        previous_signature="waiting_input:PLF-1321",
        stagnation_streak=0,
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=2,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="ignored when blocked",
        submit=True,
        include_semcod_artifacts=False,
        client=RecordingClient(),
        state=state,
    )

    assert queue_result.last_status == "waiting_input"
    assert state.stagnation_streak == 1
    assert autopilot_status == "ok"
    assert driven == ["remove duplicated classes"]


def test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure(
    tmp_path,
    monkeypatch,
) -> None:
    class FailingClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": False, "backend": "plugin", "message": "submit failed"}

    monkeypatch.setenv("KORU_OS_INJECTOR_PROFILE", "windsurf")
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
            last_message="",
            waiting=[],
        ),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "load_profile",
        lambda *_args, **_kwargs: SimpleNamespace(
            tool_id="windsurf",
            window_id=1,
            chat_x=100,
            chat_y=200,
        ),
    )
    fallback_calls: list[dict] = []
    monkeypatch.setattr(
        autonomous_mod,
        "inject_with_profile",
        lambda **kwargs: (
            fallback_calls.append(kwargs)
            or {"ok": True, "backend": "os_injector", "submitted": kwargs["submit"]}
        ),
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="windsurf",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=FailingClient(),
    )

    assert queue_result.last_status == "idle"
    assert autopilot_status == "ok"
    assert len(fallback_calls) == 1
    assert fallback_calls[0]["submit"] is True


def test_run_cycle_visible_typing_does_not_require_plugin(
    tmp_path,
    monkeypatch,
) -> None:
    drive_calls: list[dict] = []

    class RecordingClient:
        def drive(self, prompt, **kwargs):
            drive_calls.append(kwargs)
            return {"ok": True, "backend": "stub"}

    monkeypatch.setenv("KORU_AUTOPILOT_VISIBLE_TYPING", "1")
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="do work",
            waiting=["PLF-1"],
        ),
    )

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="continue",
        submit=True,
        include_semcod_artifacts=False,
        client=RecordingClient(),
    )

    assert autopilot_status == "ok"
    assert drive_calls[0]["require_plugin"] is False


def test_run_cycle_jetbrains_does_not_require_plugin_by_default(
    tmp_path,
    monkeypatch,
) -> None:
    drive_calls: list[dict] = []

    class RecordingClient:
        def drive(self, prompt, **kwargs):
            drive_calls.append(kwargs)
            return {"ok": True, "backend": "stub"}

    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="do work",
            waiting=["PLF-1"],
        ),
    )

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="jetbrains",
        drive_prompt="continue",
        submit=True,
        include_semcod_artifacts=False,
        client=RecordingClient(),
    )

    assert autopilot_status == "ok"
    assert drive_calls[0]["require_plugin"] is False


@pytest.fixture(autouse=True)
def _fast_autonomous_up(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep unit tests from running real operator pipeline or infinite outer loops."""
    monkeypatch.setattr(autonomous_mod, "run_startup_operator_pipeline", lambda **_kw: None)
    monkeypatch.setattr(autonomous_mod, "_load_loop_checkpoint", lambda *_a, **_k: None)
    monkeypatch.setattr(autonomous_mod, "_save_loop_checkpoint", lambda *_a, **_k: None)


def test_up_keeps_running_on_waiting_input_by_default(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )

    calls = 0

    def fake_queue_loop(**kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="",
        )

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--no-operator-pipeline",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "3",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--no-autopilot",
            "--agent-lane",
            "none",
        ],
    )

    assert rc == 0
    assert calls == 3


def test_up_stops_on_waiting_input_when_flag_set(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )

    calls = 0

    def fake_queue_loop(**kwargs):
        nonlocal calls
        calls += 1
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="",
        )

    class StubClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": True, "message": "sent", "backend": "test"}

        def status(self):
            return {"plugins": [{"ide": "auto"}]}

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(status="skipped", ide="auto", message="ok", command=None),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "format_plugin_install_result",
        lambda result: result.status,
    )
    monkeypatch.setattr(
        autonomous_mod,
        "_start_or_reuse_daemon",
        lambda **kwargs: (StubClient(), None, None),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--no-operator-pipeline",
            "--project",
            str(tmp_path),
            "--stop-on-waiting-input",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--agent-lane",
            "none",
        ],
    )

    assert rc == 0
    assert calls == 1


def test_up_restarts_autopilot_when_socket_disappears_between_cycles(
    tmp_path,
    monkeypatch,
) -> None:
    """Unix socket vanishes after boot: autonomous restarts daemon via _start_or_reuse_daemon."""
    monkeypatch.setattr(
        autonomous_mod,
        "init_project",
        lambda project, force=False: SimpleNamespace(project=project),
    )
    monkeypatch.setattr(autonomous_mod.time, "sleep", lambda _s: None)
    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(status="skipped", ide="auto", message="ok", command=None),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "format_plugin_install_result",
        lambda result: result.status,
    )

    sock = tmp_path / "koru-autopilot-test.sock"
    sock.write_text("", encoding="utf-8")

    daemon_starts: list[int] = []

    class FakeClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": True, "backend": "fake"}

        def status(self):
            return {"plugins": [{"ide": "auto"}]}

    def fake_start_or_reuse_daemon(**_kwargs):
        daemon_starts.append(1)
        return (FakeClient(), None, None)

    cycle = {"n": 0}

    def fake_run_planfile_queue_loop(**_kwargs):
        cycle["n"] += 1
        if cycle["n"] == 1:
            sock.unlink(missing_ok=True)
        return SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=0 last_status=idle",
            last_status="idle",
        )

    monkeypatch.setattr(autonomous_mod, "_start_or_reuse_daemon", fake_start_or_reuse_daemon)
    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_run_planfile_queue_loop)
    monkeypatch.setattr(autonomous_mod, "default_socket_path", lambda: sock)

    rc = autonomous_mod.autonomous_main(
        [
            "up",
            "--no-serve",
            "--project",
            str(tmp_path),
            "--max-cycles",
            "2",
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--agent-lane",
            "none",
        ],
    )
    assert rc == 0
    assert len(daemon_starts) == 2


def test_compute_backoff_sleep_caps_stagnation() -> None:
    assert autonomous_mod._compute_backoff_sleep(30, 0, 900, True) == 30
    assert autonomous_mod._compute_backoff_sleep(30, 2, 900, True) == 120
    assert autonomous_mod._compute_backoff_sleep(30, 10, 100, True) == 100
    assert autonomous_mod._compute_backoff_sleep(30, 2, 900, False) == 30


def test_env_apply_autoloop_defaults_enables_full_diagnostics(monkeypatch) -> None:
    args = SimpleNamespace(
        ticket_sources="all",
        idle_diagnostics="off",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=".planfile/.koru/autoloop-diag",
        strict_diagnostics=False,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=True,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        backoff_on_stagnation=True,
        scan_skip_if_clean=False,
        scan_after_idle_queue=False,
        scan_after_idle_min_interval=0.0,
        topology_integration=True,
        wup_watch=False,
        wup_mode="testql",
        wup_deps="deps.json",
        wup_scenarios_dir="testql-scenarios",
        wup_testql_bin="testql",
        wup_track_dir=".wup/tracks",
        wup_diagnostic_tickets=True,
        wup_ticket_queue="default",
    )
    monkeypatch.setenv("ENABLE_IDLE_DIAGNOSTICS", "true")
    monkeypatch.setenv("ENABLE_DIAGNOSTIC_TICKETS", "true")
    monkeypatch.setenv("AUTOPILOT_ACTION", "off")
    autonomous_mod._env_apply_autoloop_defaults(args)
    assert args.idle_diagnostics == "full"
    assert args.diagnostic_tickets is True
    assert args.autopilot_action == "off"


def test_run_idle_diagnostics_profile_off_message(tmp_path, capsys) -> None:
    result = autonomous_mod._run_idle_diagnostics(
        stdio_format="human",
        project=tmp_path,
        profile="off",
        cycle=1,
        queue_status="idle",
        diagnostic_tickets=False,
        diagnostic_ticket_queue="default",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=tmp_path / ".planfile/.koru/autoloop-diag",
        topology_integration=False,
    )
    assert result.status == "off"
    captured = capsys.readouterr().out
    assert "disabled (profile=off)" in captured
    assert "(skipping)" not in captured


def test_run_idle_diagnostics_creates_deduped_ticket(tmp_path, monkeypatch) -> None:
    import koru.autonomous_diagnostics as _diag_mod

    monkeypatch.setattr(
        _diag_mod.shutil,
        "which",
        lambda name: "/bin/false" if name == "regix" else None,
    )
    monkeypatch.setattr(autonomous_mod, "_run_command_check", lambda *_args, **_kwargs: False)
    monkeypatch.setattr(autonomous_mod, "_is_topology_enabled", lambda *_args, **_kwargs: True)
    result = autonomous_mod._run_idle_diagnostics(
        project=tmp_path,
        profile="quick",
        cycle=1,
        queue_status="idle",
        diagnostic_tickets=True,
        diagnostic_ticket_queue="diag",
        diagnostic_ticket_priority="high",
        diagnostic_state_dir=tmp_path / ".planfile/.koru/autoloop-diag",
        topology_integration=False,
    )
    assert result.status == "failed"
    assert (tmp_path / ".planfile/.koru/autoloop-diag/regix.failed").exists()
    sprint = tmp_path / ".planfile/sprints/current.yaml"
    assert "[AUTO-DIAG] regix needs attention" in sprint.read_text(encoding="utf-8")


def test_wup_watch_command_uses_testql_mode(tmp_path) -> None:
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    wrapper = scripts / "koru-wup-testql"
    wrapper.write_text('#!/bin/sh\nexec testql "$@"\n', encoding="utf-8")
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )
    command = autonomous_wup_mod._wup_watch_command(config)
    assert command[:3] == ["wup", "watch", str(tmp_path)]
    assert "--mode" in command
    assert "testql" in command
    assert "--scenarios-dir" in command
    assert "--quick-limit" in command
    assert str(wrapper) in command


def test_wup_watch_command_prefers_project_venv_wrapper(tmp_path) -> None:
    wrapper = tmp_path / ".venv" / "bin" / "koru-wup-testql"
    wrapper.parent.mkdir(parents=True)
    wrapper.write_text('#!/bin/sh\nexec testql "$@"\n', encoding="utf-8")
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )
    command = autonomous_wup_mod._wup_watch_command(config)
    assert str(wrapper) in command


def test_wup_watch_command_keeps_explicit_testql_bin(tmp_path) -> None:
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="/usr/local/bin/testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )
    command = autonomous_wup_mod._wup_watch_command(config)
    assert "/usr/local/bin/testql" in command


def test_wup_watch_command_normalizes_percent_cpu_throttle(tmp_path) -> None:
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="default",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=70,
        quick_limit=3,
        config=None,
    )
    command = autonomous_wup_mod._wup_watch_command(config)
    assert command[command.index("--cpu-throttle") + 1] == "0.7"


def test_wup_subprocess_env_loads_project_wup_env(tmp_path, monkeypatch) -> None:
    (tmp_path / ".wup.env").write_text(
        "PLAYWRIGHT_BROWSERS_PATH=/tmp/project-browsers\nWUP_BASE_URL=http://localhost:8100\n",
        encoding="utf-8",
    )
    monkeypatch.delenv("PLAYWRIGHT_BROWSERS_PATH", raising=False)
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )

    env = autonomous_wup_mod._wup_subprocess_env(config)

    assert env["PLAYWRIGHT_BROWSERS_PATH"] == "/tmp/project-browsers"
    assert env["WUP_BASE_URL"] == "http://localhost:8100"


def test_start_wup_watch_passes_playwright_env(tmp_path, monkeypatch) -> None:
    (tmp_path / "wup.yaml").write_text("project:\n  name: test\n", encoding="utf-8")
    (tmp_path / ".wup.env").write_text(
        "PLAYWRIGHT_BROWSERS_PATH=/tmp/project-browsers\n",
        encoding="utf-8",
    )
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )

    popen_calls: list[dict[str, object]] = []

    class DummyProcess:
        pid = 123

    monkeypatch.setattr(
        autonomous_wup_mod.shutil,
        "which",
        lambda name: "/usr/bin/wup" if name == "wup" else None,
    )
    monkeypatch.setattr(
        autonomous_wup_mod,
        "_ensure_wup_profiled_compose_services",
        lambda *args, **kwargs: None,
    )

    def fake_popen(command, cwd=None, env=None):
        popen_calls.append({"command": command, "cwd": cwd, "env": env})
        return DummyProcess()

    monkeypatch.setattr(autonomous_wup_mod.subprocess, "Popen", fake_popen)

    process = autonomous_wup_mod._start_wup_watch(config, topology_integration=False)

    assert process is not None
    assert popen_calls
    assert popen_calls[0]["cwd"] == tmp_path
    assert popen_calls[0]["env"]["PLAYWRIGHT_BROWSERS_PATH"] == "/tmp/project-browsers"


def test_wup_profiled_compose_services_start_before_watch(tmp_path, monkeypatch) -> None:
    (tmp_path / "wup.yaml").write_text(
        """
monitoring:
  wup_services:
    firmware:
      docker:
        - compose_service: firmware
          compose_file: docker-compose.yml
          profiles:
            - simulator
        - compose_service: backend
          compose_file: docker-compose.yml
          profiles: []
""",
        encoding="utf-8",
    )
    config = autonomous_wup_mod.WupWatchConfig(
        enabled=True,
        mode="testql",
        project=tmp_path,
        deps_file="deps.json",
        scenarios_dir="testql-scenarios",
        testql_bin="testql",
        track_dir=".wup/tracks",
        debounce=2,
        cooldown=300,
        cpu_throttle=0.8,
        quick_limit=3,
        config=None,
    )
    calls: list[list[str]] = []

    monkeypatch.setattr(autonomous_wup_mod.shutil, "which", lambda name: f"/usr/bin/{name}")

    def fake_run(command, **kwargs):
        calls.append(command)
        assert kwargs["cwd"] == tmp_path
        if "ps" in command:
            return SimpleNamespace(
                returncode=0,
                stdout=json.dumps([{"State": "running", "Health": "healthy"}]),
                stderr="",
            )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    monkeypatch.setattr(autonomous_wup_mod.subprocess, "run", fake_run)
    autonomous_wup_mod._ensure_wup_profiled_compose_services(config)

    assert calls == [
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "--profile",
            "simulator",
            "up",
            "-d",
            "firmware",
        ],
        [
            "docker",
            "compose",
            "-f",
            "docker-compose.yml",
            "--profile",
            "simulator",
            "ps",
            "--format",
            "json",
            "firmware",
        ],
    ]


def test_wup_compose_ps_accepts_json_lines() -> None:
    items = autonomous_wup_mod._parse_compose_ps_json(
        '{"State":"running","Health":"healthy"}\n'
        '{"State":"running","Health":"healthy"}\n',
    )

    assert autonomous_wup_mod._compose_service_ready(items)


def test_wup_topology_gate_uses_pipeline_for_gate_wup(tmp_path, monkeypatch) -> None:
    calls: list[str] = []

    def fake_pipeline(_project: Path, key: str) -> bool:
        calls.append(key)
        return True

    monkeypatch.setattr(autonomous_wup_mod, "is_pipeline_enabled", fake_pipeline)
    monkeypatch.setattr(
        autonomous_wup_mod,
        "is_component_enabled",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(AssertionError("component lookup")),
    )

    assert autonomous_wup_mod._wup_topology_gate(
        tmp_path,
        "gate:wup",
        fallback=False,
        enabled=True,
    )
    assert calls == ["gate:wup"]


def test_read_wup_health_creates_high_priority_planfile_ticket(tmp_path) -> None:
    health_dir = tmp_path / ".wup"
    health_dir.mkdir()
    (health_dir / "service-health.json").write_text(
        json.dumps(
            {
                "api": {
                    "status": "down",
                    "stage": "quick",
                    "message": "TestQL scenario failed",
                    "track_file": ".wup/tracks/api.json",
                },
            },
        ),
        encoding="utf-8",
    )
    state = autonomous_mod.AutoloopState()
    result = autonomous_mod._read_wup_health(
        project=tmp_path,
        state=state,
        diagnostic_tickets=True,
        ticket_queue="default",
        state_dir=tmp_path / ".planfile/.koru/autoloop-diag",
    )
    assert result.status == "failed"
    assert result.failing_services == ["api"]
    marker = tmp_path / ".planfile/.koru/autoloop-diag/wup-api.failed"
    assert marker.exists()
    sprint = tmp_path / ".planfile/sprints/current.yaml"
    text = sprint.read_text(encoding="utf-8")
    assert "[AUTO-DIAG] wup-api needs attention" in text
    assert "priority: high" in text


def test_read_wup_health_ignores_degraded_fleet_and_clears_marker(tmp_path) -> None:
    health_dir = tmp_path / ".wup"
    health_dir.mkdir()
    diag_dir = tmp_path / ".planfile/.koru/autoloop-diag"
    diag_dir.mkdir(parents=True)
    (diag_dir / "wup-c2004.failed").write_text("PLF-9999", encoding="utf-8")
    (health_dir / "service-health.json").write_text(
        json.dumps(
            {
                "frontend": {"status": "up", "stage": "quick"},
                "c2004": {
                    "status": "degraded",
                    "stage": "health_scenario",
                    "message": "66/74 passed, 8 failed",
                },
            },
        ),
        encoding="utf-8",
    )
    state = autonomous_mod.AutoloopState()
    result = autonomous_mod._read_wup_health(
        project=tmp_path,
        state=state,
        diagnostic_tickets=True,
        ticket_queue="default",
        state_dir=diag_dir,
    )
    assert result.status == "ok"
    assert result.failing_services == []
    assert not (diag_dir / "wup-c2004.failed").exists()
