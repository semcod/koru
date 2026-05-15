"""Tests for `koru autonomous` one-command loop."""

from __future__ import annotations

import json
import os
import sys
from types import SimpleNamespace

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
        ]
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
        ]
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


def test_guard_existing_autonomous_noninteractive_blocks_duplicate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            autonomous_mod.ExistingAutonomousProcess(
                pid=123,
                command="koru autonomous up --project " + str(tmp_path),
                cwd=tmp_path,
            )
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
        )
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
    tmp_path, monkeypatch
) -> None:
    wup = [
        autonomous_mod.ExistingManagedProcess(
            pid=456,
            kind="wup-watch",
            command="wup watch " + str(tmp_path),
            cwd=tmp_path,
        )
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
    tmp_path, monkeypatch
) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            autonomous_mod.ExistingAutonomousProcess(
                pid=123,
                command="koru autonomous up --project " + str(tmp_path),
                cwd=tmp_path,
            )
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
            ]
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


def test_apply_agent_lane_environ_auto_cursor(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.delenv("VSCODE_NLS_CONFIG", raising=False)
    monkeypatch.delenv("VSCODE_IPC_HOOK", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("VSCODE_CWD", raising=False)
    monkeypatch.delenv("VSCODE_CODE_CACHE_PATH", raising=False)
    monkeypatch.delenv("CI", raising=False)
    monkeypatch.delenv("GITHUB_ACTIONS", raising=False)
    (tmp_path / ".cursor").mkdir()
    lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "cursor"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "cursor"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)


def test_apply_agent_lane_environ_auto_prefers_vscode_terminal(tmp_path, monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "{}")
    (tmp_path / ".windsurf").mkdir()
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
        ]
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
        ]
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
        ]
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
        ]
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
        ]
    )

    assert rc == 0
    assert install_calls == ["cursor:koru-autopilot.sock"]


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
        lambda **kwargs: fallback_calls.append(kwargs)
        or {"ok": True, "backend": "os_injector", "submitted": kwargs["submit"]},
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


def test_up_stops_on_waiting_input_by_default(
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
        """Accepts drive (fallback prompt) but tracks if --stop-on-waiting-input fires."""
        def drive(self, *_args, **_kwargs):
            return {"ok": True, "message": "sent", "backend": "test"}

    monkeypatch.setattr(autonomous_mod, "run_planfile_queue_loop", fake_queue_loop)
    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(status="skipped", ide="auto", message="ok", command=None),
    )
    monkeypatch.setattr(
        autonomous_mod, "format_plugin_install_result", lambda result: result.status
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
            "--project",
            str(tmp_path),
            "--sleep-seconds",
            "0",
            "--ticket-sources",
            "queue",
            "--agent-lane",
            "none",
        ]
    )

    # --stop-on-waiting-input is default-true → outer loop stops after 1 cycle
    # even though autopilot now sends a fallback prompt within that cycle.
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
        ]
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
    monkeypatch.setattr(
        autonomous_mod.shutil, "which", lambda name: "/bin/false" if name == "regix" else None
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
    wrapper.write_text("#!/bin/sh\nexec testql \"$@\"\n", encoding="utf-8")
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
        tmp_path, "gate:wup", fallback=False, enabled=True
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
                }
            }
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
