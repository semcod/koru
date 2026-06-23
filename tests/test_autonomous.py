"""Tests for `koru autonomous` one-command loop."""

from __future__ import annotations

import io
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest
import yaml

from koru import autonomous as autonomous_mod
from koru import autonomous_cycle as autonomous_cycle_mod
from koru import autonomous_cycle_orchestrator as cycle_orchestrator_mod
from koru import autonomous_cycle_drive_retry as drive_retry_mod
from koru import autonomous_cycle_skip_conditions as skip_conditions_mod
from koru import autonomous_env as autonomous_env_mod
from koru import autonomous_processes as autonomous_processes_mod
from koru import autonomous_wup as autonomous_wup_mod
from koru.autonomous_parser import looks_like_autonomous_up_command
from koru.autonomous_processes import ExistingAutonomousProcess, ExistingManagedProcess
from koru.queue.types import QueueLoopResult
from koru.scan import ScanResult


@pytest.fixture(autouse=True)
def _isolate_terminal_ide(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "detect_terminal_host_ide_id",
        lambda: None,
    )


def _force_idle_drive_prompt(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        autonomous_mod,
        "resolve_idle_drive_prompt",
        lambda *_args, drive_prompt, **_kwargs: (drive_prompt, "drive_prompt"),
    )


def test_effective_flags_matrix() -> None:
    assert autonomous_env_mod.effective_ticket_source_flags("queue") == (False, False)
    assert autonomous_env_mod.effective_ticket_source_flags("scan") == (True, False)
    assert autonomous_env_mod.effective_ticket_source_flags("all") == (True, True)


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


def test_run_cycle_records_environment_profile_in_telemetry(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("XDG_SESSION_TYPE", "wayland")
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **_kwargs: QueueLoopResult(
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
        cycle=7,
        project=tmp_path,
        actor="t",
        queue_name=None,
        enable_scan=False,
        max_iterations=1,
        enable_autopilot=False,
        autopilot_ide="vscodium",
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
        scan_after_idle_queue=False,
        topology_integration=False,
        stdio_format="human",
        correlation_id="env-profile-test",
    )

    snapshot = json.loads(
        (tmp_path / ".planfile" / ".koru" / "autonomy-telemetry.json").read_text(
            encoding="utf-8",
        ),
    )
    profile = snapshot["last_cycle"]["environment_profile"]
    assert profile["ide"]["id"] == "vscodium"
    assert profile["os"]["display_server"] == "wayland"
    assert profile["control"]["interface_id"] == "plugin_socket_vscode_family"
    assert "ide=vscodium" in profile["decision_key"]


def test_scan_after_idle_runs_code2llm_discovery_when_semcod_scan_empty(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "run_scan",
        lambda **_kwargs: ScanResult(suggestions=[], applied=[], skipped=[]),
    )
    discoveries: list[Path] = []

    def fake_discovery(project, _hp, _emit, **_kwargs):
        discoveries.append(project)
        return {"ran": True, "applied": ["Split god module: src/a.py"], "skipped": []}

    monkeypatch.setattr(
        autonomous_cycle_mod,
        "_run_code2llm_discovery_after_idle",
        fake_discovery,
    )
    state = autonomous_cycle_mod.AutoloopState()
    telemetry = {
        "scan_after_idle_run": False,
        "scan_after_idle_applied": 0,
        "scan_after_idle_skipped_rate_limit": False,
    }
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
        last_ticket_id=None,
    )

    result = autonomous_cycle_mod._handle_scan_after_idle(
        tmp_path,
        state,
        1,
        queue_result,
        True,
        True,
        0.0,
        False,
        telemetry,
        lambda *_args, **_kwargs: None,
        lambda *_args, **_kwargs: None,
    )

    assert result is not None
    assert discoveries == [tmp_path]
    assert telemetry["code2llm_discovery_run"] is True
    assert telemetry["code2llm_discovery_applied"] == 1
    assert state.telemetry_scan_after_idle_tickets_applied == 1


def test_scan_after_idle_duplicate_cooldown_still_runs_general_discovery(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "run_scan",
        lambda **_kwargs: pytest.fail("duplicate cooldown should skip concrete scan"),
    )
    discoveries: list[Path] = []
    logs: list[str] = []

    def fake_discovery(project, _hp, _emit, **_kwargs):
        discoveries.append(project)
        return {"ran": False, "applied": ["Project-wide finding"], "skipped": []}

    monkeypatch.setattr(
        autonomous_cycle_mod,
        "_run_code2llm_discovery_after_idle",
        fake_discovery,
    )
    state = autonomous_cycle_mod.AutoloopState(
        last_scan_duplicate_fingerprint="1:abc",
        last_scan_duplicate_ts=9999999999.0,
    )
    telemetry: dict[str, object] = {}
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
        last_ticket_id=None,
    )

    result = autonomous_cycle_mod._handle_scan_after_idle(
        tmp_path,
        state,
        1,
        queue_result,
        True,
        True,
        0.0,
        False,
        telemetry,
        logs.append,
        lambda *_args, **_kwargs: None,
    )

    assert result is None
    assert discoveries == [tmp_path]
    assert telemetry["scan_after_idle_skipped_duplicate_cooldown"] is True
    assert telemetry["code2llm_discovery_applied"] == 1
    assert state.telemetry_scan_after_idle_tickets_applied == 1
    assert any("detail→general" in line for line in logs)


def test_cycle_code2llm_discovery_ensures_standardized_follow_up_ticket(
    tmp_path,
    monkeypatch,
) -> None:
    from koru.autonomy import code2llm_discovery as code2llm_discovery_mod
    from koru.autonomy import ide_work as ide_work_mod

    outcome = code2llm_discovery_mod.DiscoveryOutcome(
        ran=True,
        code2llm_returncode=0,
        applied_titles=[],
        skipped_titles=[],
    )
    emits: list[tuple[str, dict]] = []

    monkeypatch.setattr(
        code2llm_discovery_mod,
        "run_code2llm_discovery",
        lambda _project, *, scope_paths=None: outcome,
    )
    monkeypatch.setattr(
        code2llm_discovery_mod,
        "format_discovery_summary",
        lambda _outcome: "code2llm discovery: applied=0 skipped=0",
    )
    monkeypatch.setattr(
        ide_work_mod,
        "ensure_project_discovery_ticket",
        lambda _project, *, auto_run_code2llm: {
            "id": "PLF-901",
            "name": "Project discovery",
        },
    )

    payload = autonomous_cycle_mod._run_code2llm_discovery_after_idle(
        tmp_path,
        lambda _line: None,
        lambda kind, payload, **_kwargs: emits.append((kind, payload)),
    )

    assert payload is not None
    assert payload["follow_up_workflow"] == "standardized_project_discovery"
    assert payload["follow_up_ticket_id"] == "PLF-901"
    assert emits and emits[-1][0] == "Code2llmDiscoveryCompleted"
    assert emits[-1][1]["follow_up_ticket_id"] == "PLF-901"


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
    _force_idle_drive_prompt(monkeypatch)
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
    assert looks_like_autonomous_up_command(
        "python3 -m koru.cli auto --project /tmp/x",
    )


def test_looks_like_autonomous_matches_koru_autonomous_regex() -> None:
    assert looks_like_autonomous_up_command(
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


def test_auto_invocation_uses_full_autonomous_defaults(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTO_PIPELINE", raising=False)
    with patch.object(autonomous_mod, "_action_up", return_value=0) as action_up:
        rc = autonomous_mod.autonomous_main(["--project", str(tmp_path)], invoked_as_auto=True)

    assert rc == 0
    args = action_up.call_args.args[0]
    assert args._auto_pipeline_enabled is False
    assert args.ticket_sources == "all"
    assert args.max_cycles == 0
    assert args.max_iterations == 50
    assert args.stop_on_waiting_input is False
    assert args.scan_after_idle_queue is True
    assert args.semcod_artifacts is True
    assert args.operator_pipeline is True
    assert args.operator_tickets is True
    assert args.enable_autopilot is True
    assert args.autopilot_action == "drive"


def test_auto_invocation_can_disable_after_idle_intake(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTO_PIPELINE", raising=False)
    with patch.object(autonomous_mod, "_action_up", return_value=0) as action_up:
        rc = autonomous_mod.autonomous_main(
            ["--project", str(tmp_path), "--no-scan-after-idle-queue"],
            invoked_as_auto=True,
        )

    assert rc == 0
    args = action_up.call_args.args[0]
    assert args.scan_after_idle_queue is False


def test_auto_invocation_applies_koru_yaml_strategy_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTO_PIPELINE", raising=False)
    monkeypatch.delenv("KORU_PLANNING_LLM", raising=False)
    monkeypatch.delenv("KORU_PLANNING_LLM_MODEL", raising=False)
    (tmp_path / "koru.yaml").write_text(
        """
schema: '1.0'
autonomy:
  strategy:
    idle_discovery:
      enabled: false
      min_interval_seconds: 123
      tools:
        automated: []
        artifact_sources: []
    planning_assistant:
      enabled: false
      openrouter:
        model: openrouter/example/model
""",
        encoding="utf-8",
    )

    with patch.object(autonomous_mod, "_action_up", return_value=0) as action_up:
        rc = autonomous_mod.autonomous_main(["--project", str(tmp_path)], invoked_as_auto=True)

    assert rc == 0
    args = action_up.call_args.args[0]
    assert args.scan_after_idle_queue is False
    assert args.scan_after_idle_min_interval == 123
    assert args.semcod_artifacts is False
    assert os.environ["KORU_PLANNING_LLM"] == "0"
    assert os.environ["KORU_PLANNING_LLM_MODEL"] == "example/model"


def test_auto_invocation_cli_flags_override_koru_yaml_strategy_defaults(
    tmp_path: Path,
    monkeypatch,
) -> None:
    monkeypatch.delenv("KORU_AUTO_PIPELINE", raising=False)
    (tmp_path / "koru.yaml").write_text(
        """
schema: '1.0'
autonomy:
  strategy:
    idle_discovery:
      enabled: false
      min_interval_seconds: 123
      tools:
        automated: []
        artifact_sources: []
""",
        encoding="utf-8",
    )

    with patch.object(autonomous_mod, "_action_up", return_value=0) as action_up:
        rc = autonomous_mod.autonomous_main(
            [
                "--project",
                str(tmp_path),
                "--scan-after-idle-queue",
                "--scan-after-idle-min-interval",
                "7",
                "--semcod-artifacts",
            ],
            invoked_as_auto=True,
        )

    assert rc == 0
    args = action_up.call_args.args[0]
    assert args.scan_after_idle_queue is True
    assert args.scan_after_idle_min_interval == 7
    assert args.semcod_artifacts is True


def test_auto_invocation_can_enable_adaptive_pipeline(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTO_PIPELINE", "1")
    with patch.object(autonomous_mod, "_action_up", return_value=0) as action_up:
        rc = autonomous_mod.autonomous_main(["--project", str(tmp_path)], invoked_as_auto=True)

    assert rc == 0
    args = action_up.call_args.args[0]
    assert args._auto_pipeline_enabled is True


def test_auto_onboarding_flow_uses_simulated_stdin(tmp_path: Path, monkeypatch) -> None:
    project = tmp_path / "demo-onboarding"
    project.mkdir()

    monkeypatch.setenv("KORU_ONBOARDING_LLX", "0")
    monkeypatch.setenv("KORU_ONBOARDING_CREATE_TICKET", "1")

    from koru.wizard.ide import DetectedIDE
    from koru.wizard.project import ProjectCandidate

    ide = DetectedIDE(
        id="vscode",
        label="VS Code",
        running=True,
        pid=321,
        path="/usr/bin/code",
    )
    monkeypatch.setattr("koru.wizard.cli.discover_installed_ides", lambda: [ide])
    monkeypatch.setattr(
        "koru.wizard.cli.propose_projects",
        lambda _ides: [ProjectCandidate(path=project, source="VS Code workspace")],
    )

    class _TTYInput(io.StringIO):
        def isatty(self) -> bool:
            return True

    class _TTYOutput(io.StringIO):
        def isatty(self) -> bool:
            return True

    stdin = _TTYInput("quality\ncc_refactor\n")
    stdout = _TTYOutput()
    monkeypatch.setattr(autonomous_mod._autonomous_onboarding.sys, "stdin", stdin)
    monkeypatch.setattr(autonomous_mod._autonomous_onboarding.sys, "stdout", stdout)

    captured: dict[str, object] = {}
    monkeypatch.setattr(autonomous_mod, "_setup_autonomous_env_vars", lambda: (None, {}))

    def fake_setup_session(args):
        captured["autopilot_ide"] = args.autopilot_ide
        captured["agent_lane"] = args.agent_lane
        captured["project"] = args.project
        return "cid", args.project.resolve(), 73

    monkeypatch.setattr(autonomous_mod, "_setup_autonomous_session", fake_setup_session)

    rc = autonomous_mod.autonomous_main(["--project", str(project)], invoked_as_auto=True)

    assert rc == 73
    assert captured["autopilot_ide"] == "vscode"
    assert captured["agent_lane"] == "vscode"
    assert Path(str(captured["project"])).resolve() == project.resolve()

    sprint_yaml = project / ".planfile" / "sprints" / "current.yaml"
    assert sprint_yaml.exists()
    text = sprint_yaml.read_text(encoding="utf-8")
    assert "koru-wizard" in text


def test_auto_pipeline_profiles_escalate_when_queue_stays_idle() -> None:
    args = SimpleNamespace(
        max_iterations=1,
        ticket_sources="queue",
        semcod_artifacts=False,
        idle_diagnostics="off",
        diagnostic_tickets=False,
        scan_after_idle_queue=False,
        scan_after_idle_min_interval=0.0,
        enable_autopilot=False,
        autopilot_action="off",
        _auto_user_options=set(),
    )
    state = autonomous_mod.AutoPipelineState()

    first = autonomous_mod._select_auto_pipeline_profile(args, state, base_enable_scan=False)
    assert first.name == "rescue"
    assert first.enable_scan is False
    assert first.idle_diagnostics == "off"
    assert first.include_semcod_artifacts is False

    idle = QueueLoopResult(1, [], [], [], "idle", "")
    autonomous_mod._update_auto_pipeline_state(
        state,
        idle,
        autonomous_mod.DiagnosticResult("skipped", []),
        "skipped",
    )
    second = autonomous_mod._select_auto_pipeline_profile(args, state, base_enable_scan=False)
    assert second.name == "stabilize"
    assert second.idle_diagnostics == "quick"
    assert second.scan_after_idle_queue is True
    assert second.include_semcod_artifacts is False

    autonomous_mod._update_auto_pipeline_state(
        state,
        idle,
        autonomous_mod.DiagnosticResult("ok", []),
        "skipped",
    )
    third = autonomous_mod._select_auto_pipeline_profile(args, state, base_enable_scan=False)
    assert third.name == "quality"
    assert third.enable_scan is True
    assert third.idle_diagnostics == "full"
    assert third.include_semcod_artifacts is True

    autonomous_mod._update_auto_pipeline_state(
        state,
        idle,
        autonomous_mod.DiagnosticResult("ok", []),
        "skipped",
    )
    fourth = autonomous_mod._select_auto_pipeline_profile(args, state, base_enable_scan=False)
    assert fourth.name == "architecture"
    assert fourth.idle_diagnostics == "deep"


def test_effective_cycle_autopilot_skips_required_plugin_when_missing(
    monkeypatch,
) -> None:
    messages: list[str] = []

    class NoPluginClient:
        def status(self):
            return {"plugins": []}

    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda msg, *, fmt: messages.append(msg),
    )

    enabled = autonomous_mod._effective_cycle_autopilot_enabled(
        True,
        client=NoPluginClient(),
        autopilot_ide="vscode",
        stdio_format="human",
    )

    assert enabled is False
    assert any("autopilot skipped this cycle" in msg for msg in messages)


def test_autopilot_terminal_conflict_blocks_cross_vscode_family_drive(monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_CROSS_IDE", raising=False)
    monkeypatch.setattr(
        "koru.autonomy.env.detect_terminal_host_ide_id",
        lambda: "vscodium",
    )

    from koru.autonomy.env import autopilot_terminal_conflict_reason
    reason = autopilot_terminal_conflict_reason("vscode")

    assert reason is not None
    assert "terminal host is vscodium" in reason


def test_autopilot_terminal_conflict_can_be_explicitly_allowed(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_ALLOW_CROSS_IDE", "1")
    monkeypatch.setattr(
        "koru.autonomy.env.detect_terminal_host_ide_id",
        lambda: "vscodium",
    )

    from koru.autonomy.env import autopilot_terminal_conflict_reason
    assert autopilot_terminal_conflict_reason("vscode") is None


def test_autopilot_terminal_conflict_allows_connected_target_plugin(monkeypatch) -> None:
    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_CROSS_IDE", raising=False)
    monkeypatch.setattr(
        "koru.autonomy.env.detect_terminal_host_ide_id",
        lambda: "vscode",
    )

    from koru.autonomy.env import autopilot_terminal_conflict_reason
    assert (
        autopilot_terminal_conflict_reason(
            "vscodium",
            plugin_connected=True,
        )
        is None
    )


def test_effective_cycle_autopilot_allows_non_plugin_required_ide() -> None:
    enabled = autonomous_mod._effective_cycle_autopilot_enabled(
        True,
        client=None,
        autopilot_ide="jetbrains",
        stdio_format="human",
    )

    assert enabled is True


def test_effective_cycle_scan_skips_after_waiting_input(monkeypatch) -> None:
    messages: list[str] = []
    state = autonomous_mod.AutoloopState(previous_signature="waiting_input:STARTER-048")

    monkeypatch.delenv("KORU_AUTONOMOUS_SCAN_WHILE_WAITING", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda msg, *, fmt: messages.append(msg),
    )

    enabled = autonomous_mod._effective_cycle_scan_enabled(
        True,
        state=state,
        stdio_format="human",
    )

    assert enabled is False
    assert any("scan skipped this cycle" in msg for msg in messages)


def test_effective_cycle_scan_waiting_override(monkeypatch) -> None:
    state = autonomous_mod.AutoloopState(previous_signature="waiting_input:STARTER-048")
    monkeypatch.setenv("KORU_AUTONOMOUS_SCAN_WHILE_WAITING", "1")

    enabled = autonomous_mod._effective_cycle_scan_enabled(
        True,
        state=state,
        stdio_format="human",
    )

    assert enabled is True


def test_build_queue_command_omits_unsupported_all_queues_flag() -> None:
    assert autonomous_cycle_mod._build_queue_command(50, None) == (
        "koru --queue --loop --max-iterations 50"
    )
    assert autonomous_cycle_mod._build_queue_command(50, "operator") == (
        "koru --queue --loop --max-iterations 50 --queue-name operator"
    )


def test_stop_prior_autonomous_for_auto_start_terminates(tmp_path, monkeypatch) -> None:
    existing = [
        ExistingAutonomousProcess(
            pid=99,
            command="python3 -m koru.cli auto --project " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(
        autonomous_processes_mod,
        "_find_existing_autonomous_processes",
        lambda project, any_project=False: existing if any_project else [],
    )
    monkeypatch.setattr(autonomous_processes_mod, "_find_existing_wup_processes", lambda project: [])
    monkeypatch.setattr(
        autonomous_processes_mod,
        "_terminate_existing_processes",
        lambda processes, **kwargs: stopped.extend(proc.pid for proc in processes),
    )
    autonomous_mod.stop_prior_autonomous_for_auto_start(tmp_path)
    assert stopped == [99]


def test_guard_existing_autonomous_noninteractive_blocks_duplicate(tmp_path, monkeypatch) -> None:
    monkeypatch.setattr(
        autonomous_processes_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            ExistingAutonomousProcess(
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
        ExistingAutonomousProcess(
            pid=123,
            command="koru autonomous up --project " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(
        autonomous_processes_mod,
        "_find_existing_autonomous_processes",
        lambda project: existing,
    )
    monkeypatch.setattr(
        autonomous_processes_mod,
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
        ExistingManagedProcess(
            pid=456,
            kind="wup-watch",
            command="wup watch " + str(tmp_path),
            cwd=tmp_path,
        ),
    ]
    stopped: list[int] = []
    monkeypatch.setattr(autonomous_processes_mod, "_find_existing_autonomous_processes", lambda project: [])
    monkeypatch.setattr(autonomous_processes_mod, "_find_existing_wup_processes", lambda project: wup)
    monkeypatch.setattr(
        autonomous_processes_mod,
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
        autonomous_processes_mod,
        "_find_existing_autonomous_processes",
        lambda project: [
            ExistingAutonomousProcess(
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

    monkeypatch.setattr(autonomous_mod, "_sleep", sleep_side)
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


def test_resolve_autopilot_ide_os_environ_autopilot_instance(monkeypatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
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
        "TERM_PROGRAM_VERSION",
        "WINDSURF_CASCADE_TERMINAL",
        "GIO_LAUNCHED_DESKTOP_FILE",
        # JetBrains integrated-terminal markers (host may run from a JediTerm
        # shell); detect_terminal_host_ide_id() short-circuits to jetbrains on
        # these before the VS Code checks.
        "TERMINAL_EMULATOR",
        "IDEA_INITIAL_DIRECTORY",
        "PYCHARM_HOSTED",
        "JETBRAINS_IDE",
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


def test_apply_agent_lane_environ_auto_prefers_vscodium_terminal(tmp_path, monkeypatch) -> None:
    _isolate_integrated_terminal_env(monkeypatch)
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_PID", "123")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "/snap/codium/current/resources/app")
    (tmp_path / ".vscode").mkdir()
    with patch("koru.autonomous_startup.detect_running_ides", return_value=[]):
        lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")
    assert lane == "vscodium"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscodium"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "vscodium"
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)


def test_apply_agent_lane_environ_auto_preserves_explicit_vscodium_over_vscode_terminal(
    tmp_path,
    monkeypatch,
) -> None:
    _isolate_integrated_terminal_env(monkeypatch)
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscodium")
    monkeypatch.setenv("TERM_PROGRAM", "vscode")
    monkeypatch.setenv("VSCODE_NLS_CONFIG", "{}")
    (tmp_path / ".vscode").mkdir()

    with patch("koru.autonomous_startup.detect_running_ides", return_value=[]):
        lane = autonomous_mod._apply_agent_lane_environ(tmp_path, "auto")

    assert lane == "vscodium"
    assert os.environ["KORU_AUTOPILOT_INSTANCE"] == "vscodium"
    assert os.environ["KORU_AUTOPILOT_IDE"] == "vscodium"
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
    monkeypatch.delenv("KORU_AUTOPILOT_SOCKET", raising=False)

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
    assert install_calls == ["cursor:koru-autopilot-cursor-main.sock"]
    assert "KORU_STRICT_PLUGIN_VERSION" not in os.environ
    for key in ("KORU_AUTOPILOT_IDE", "KORU_AUTOPILOT_INSTANCE", "KORU_AUTOPILOT_SOCKET"):
        os.environ.pop(key, None)


def test_setup_autopilot_plugin_unsupported_skips_wait(tmp_path, monkeypatch) -> None:
    args = SimpleNamespace(
        enable_autopilot=True,
        emit_events="human",
        autopilot_plugin_wait_seconds=5.0,
        project=str(tmp_path),
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


def test_setup_autopilot_plugin_installed_but_not_loaded_hints_reload(
    tmp_path,
    monkeypatch,
) -> None:
    args = SimpleNamespace(
        enable_autopilot=True,
        emit_events="human",
        autopilot_plugin_wait_seconds=5.0,
        project=str(tmp_path),
    )
    messages: list[str] = []
    wait_called = {"n": 0}

    def _wait(*_a, **_k):
        wait_called["n"] += 1
        return False

    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(
            status="already_installed",
            ide="cursor",
            message="ok",
            command=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod, "format_plugin_install_result", lambda _r: "already")
    monkeypatch.setattr(autonomous_mod, "_wait_for_autopilot_plugin", _wait)
    monkeypatch.setattr(autonomous_mod, "_stdio_info", lambda message, **_kwargs: messages.append(message))
    monkeypatch.setattr(
        "koru.autonomous_operator._extension_active_in_latest_session",
        lambda _ide: False,
    )
    from koru.ide_adapters.ide_reload import IdeReloadOutcome

    monkeypatch.setattr(
        "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
        lambda *_a, **_k: IdeReloadOutcome(attempted=False, ok=False),
    )
    monkeypatch.setenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "0")

    connected = autonomous_mod._setup_autopilot_plugin(
        args,
        "cursor",
        tmp_path / "koru-autopilot-cursor.sock",
        client=object(),
    )

    assert connected is False
    assert wait_called["n"] == 0
    text = "\n".join(messages)
    assert "Developer: Reload Window" in text
    assert "\033[33m" in text
    assert "pomijam oczekiwanie na plugin" in text
    assert "koru ide doctor --ide cursor --fix --explain" in text


def test_setup_autopilot_plugin_stale_version_attempts_reload_and_waits_again(
    tmp_path,
    monkeypatch,
) -> None:
    args = SimpleNamespace(
        enable_autopilot=True,
        emit_events="human",
        autopilot_plugin_wait_seconds=5.0,
        project=str(tmp_path),
    )
    messages: list[str] = []
    wait_timeouts: list[float] = []

    class _Client:
        def status(self):
            return {
                "plugins": [
                    {
                        "ide": "vscode",
                        "version": "0.0.1",
                        "protocolVersion": 1,
                        "capabilities": ["chat.submit"],
                    }
                ]
            }

    def _wait(*_a, **kwargs):
        wait_timeouts.append(float(kwargs["timeout_seconds"]))
        return len(wait_timeouts) == 2

    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(
            status="already_installed",
            ide="vscode",
            message="ok",
            command=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod, "format_plugin_install_result", lambda _r: "already")
    monkeypatch.setattr(autonomous_mod, "_wait_for_autopilot_plugin", _wait)
    monkeypatch.setattr(autonomous_mod, "_stdio_info", lambda message, **_kwargs: messages.append(message))
    monkeypatch.setattr(
        "koru.autonomous_operator._extension_active_in_latest_session",
        lambda _ide: True,
    )
    from koru.ide_adapters.ide_reload import IdeReloadOutcome

    monkeypatch.setattr(
        "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
        lambda *_a, **_k: IdeReloadOutcome(attempted=True, ok=True, method="dry_run"),
    )

    connected = autonomous_mod._setup_autopilot_plugin(
        args,
        "vscode",
        tmp_path / "koru-autopilot-vscode.sock",
        client=_Client(),
    )

    assert connected is True
    assert wait_timeouts == [5.0, 12.0]
    text = "\n".join(messages)
    assert "plugin wymaga przeładowania IDE" in text
    assert "autopilot plugin reconnected after reload" in text


def test_setup_autopilot_plugin_empty_plugin_list_attempts_reload(
    tmp_path,
    monkeypatch,
) -> None:
    args = SimpleNamespace(
        enable_autopilot=True,
        emit_events="human",
        autopilot_plugin_wait_seconds=5.0,
        project=str(tmp_path),
    )
    wait_timeouts: list[float] = []

    class _Client:
        def status(self):
            return {"plugins": []}

    def _wait(*_a, **kwargs):
        wait_timeouts.append(float(kwargs["timeout_seconds"]))
        return len(wait_timeouts) == 2

    monkeypatch.setattr(
        autonomous_mod,
        "install_plugin_for_ide",
        lambda **_kwargs: SimpleNamespace(
            status="already_installed",
            ide="vscode",
            message="ok",
            command=None,
        ),
    )
    monkeypatch.setattr(autonomous_mod, "format_plugin_install_result", lambda _r: "already")
    monkeypatch.setattr(autonomous_mod, "_wait_for_autopilot_plugin", _wait)
    monkeypatch.setattr(autonomous_mod, "_stdio_info", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(
        "koru.autonomous_operator._extension_active_in_latest_session",
        lambda _ide: True,
    )
    from koru.ide_adapters.ide_reload import IdeReloadOutcome

    monkeypatch.setattr(
        "koru.ide_adapters.ide_reload.try_reload_vscode_family_ide",
        lambda *_a, **_k: IdeReloadOutcome(attempted=True, ok=True, method="dry_run"),
    )

    connected = autonomous_mod._setup_autopilot_plugin(
        args,
        "vscode",
        tmp_path / "koru-autopilot-vscode.sock",
        client=_Client(),
    )

    assert connected is True
    assert wait_timeouts == [5.0, 12.0]


def test_status_has_autopilot_plugin_matches_specific_ide(monkeypatch) -> None:
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)

    assert autonomous_mod._status_has_autopilot_plugin(
        {"plugins": [{"ide": "vscode", "protocolVersion": 1}, {"ide": "windsurf"}]},
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
        lambda _plugin_ide: "0.1.14",
    )
    monkeypatch.setattr(
        autonomous_mod.DriveOrchestrator,
        "expected_plugin_build_sha",
        lambda _plugin_ide: None,
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
        {"plugins": [{"ide": "vscode", "version": "0.1.14", "protocolVersion": 1}]},
        "vscode",
    )


def test_status_has_autopilot_plugin_blocks_stale_version_with_strict_protocol(monkeypatch) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(
        autonomous_mod.DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.15",
    )
    monkeypatch.setattr(
        autonomous_mod.DriveOrchestrator,
        "expected_plugin_build_sha",
        lambda _plugin_ide: None,
    )

    assert not autonomous_mod._status_has_autopilot_plugin(
        {
            "plugins": [
                {
                    "ide": "vscode",
                    "version": "0.1.14",
                    "protocolVersion": 1,
                    "capabilities": ["chat.submit"],
                }
            ]
        },
        "vscode",
    )


def test_status_has_autopilot_plugin_accepts_stale_version_with_protocol_policy(monkeypatch) -> None:
    monkeypatch.setenv("KORU_PLUGIN_VERSION_POLICY", "protocol")
    monkeypatch.setattr(
        autonomous_mod.DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.15",
    )

    assert autonomous_mod._status_has_autopilot_plugin(
        {
            "plugins": [
                {
                    "ide": "vscode",
                    "version": "0.1.14",
                    "protocolVersion": 1,
                    "capabilities": ["chat.submit"],
                }
            ]
        },
        "vscode",
    )


def test_autonomous_defaults_to_strict_plugin_policy(monkeypatch) -> None:
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")
    messages: list[str] = []
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)
    monkeypatch.delenv("KORU_STRICT_PLUGIN_ACK", raising=False)
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda message, **_kwargs: messages.append(message),
    )

    autonomous_mod._enable_autonomous_strict_plugin_policy(args)

    assert os.environ["KORU_STRICT_PLUGIN_VERSION"] == "1"
    assert os.environ["KORU_STRICT_PLUGIN_ACK"] == "1"
    assert any("strict plugin version/ack policy enabled" in message for message in messages)
    os.environ.pop("KORU_STRICT_PLUGIN_VERSION", None)
    os.environ.pop("KORU_STRICT_PLUGIN_ACK", None)


def test_autonomous_respects_explicit_plugin_version_policy(monkeypatch) -> None:
    args = SimpleNamespace(enable_autopilot=True, emit_events="human")
    messages: list[str] = []
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "0")
    monkeypatch.setattr(
        autonomous_mod,
        "_stdio_info",
        lambda message, **_kwargs: messages.append(message),
    )

    autonomous_mod._enable_autonomous_strict_plugin_policy(args)

    assert os.environ["KORU_STRICT_PLUGIN_VERSION"] == "0"
    assert os.environ["KORU_STRICT_PLUGIN_ACK"] == "1"
    assert messages == ["koru autonomous: strict plugin ack policy enabled by default"]
    os.environ.pop("KORU_STRICT_PLUGIN_ACK", None)


def test_build_cycle_run_kwargs_forwards_effective_autopilot(monkeypatch) -> None:
    captured: dict[str, object] = {}

    def fake_build_cycle_run_kwargs(_args, _profile, **kwargs):
        captured.update(kwargs)
        return {"ok": True}

    monkeypatch.setattr(
        autonomous_mod._autonomous_cycle_config,
        "build_cycle_run_kwargs",
        fake_build_cycle_run_kwargs,
    )

    result = autonomous_mod._build_cycle_run_kwargs(
        SimpleNamespace(),
        None,
        cycle=1,
        project=Path("/tmp/project"),
        queue_name="default",
        enable_scan=True,
        enable_autopilot=False,
        autopilot_ide="cursor",
        client=object(),
        loop_state=object(),
        diagnostic_state_dir=Path("/tmp/project/.planfile/.koru"),
        wup_process=None,
        correlation_id="corr-test",
    )

    assert result == {"ok": True}
    assert captured["enable_autopilot"] is False


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
            return {"plugins": [{"ide": "vscode", "protocolVersion": 1}]}

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
        kwargs: dict[str, object] = {}

        def __init__(self, **kwargs) -> None:
            FakeDaemon.kwargs = dict(kwargs)
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
    assert FakeDaemon.kwargs["enable_project_handoff"] is False
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
            waiting=["TEST-001"],
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
    assert len(driven) == 1
    assert driven[0].startswith("answer this prompt")
    assert "planfile ticket done PLF-999" in driven[0]
    assert "planfile ticket input PLF-999" in driven[0]
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


def test_run_cycle_auto_marks_waiting_ticket_llm_ready_before_stuck_skip(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    """Runnable waiting_input tickets should not require a manual label command."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-1317:
      labels: [refactor]
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
            last_message="refactor this module",
            waiting=["PLF-1317"],
        ),
    )
    state = autonomous_mod.AutoloopState(
        previous_signature="waiting_input:PLF-1317",
        stagnation_streak=1,
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=3,
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
    assert driven[0].startswith("refactor this module")
    sprint = yaml.safe_load((sprint_dir / "current.yaml").read_text(encoding="utf-8"))
    assert "llm-ready" in sprint["sprint"]["tickets"]["PLF-1317"]["labels"]
    out = capsys.readouterr().out
    assert "auto llm-ready: added label to PLF-1317" in out


def test_run_cycle_drives_llm_ready_waiting_ticket_without_stagnation_skip(
    tmp_path,
    monkeypatch,
) -> None:
    """llm-ready tickets should be driven by IDE autopilot even when human queue waits."""
    # Clear chat activity state to avoid test isolation failures
    monkeypatch.setattr(autonomous_cycle_mod, "_skip_due_to_recent_chat_activity", lambda *args, **kwargs: False)
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
    assert len(driven) == 1
    assert driven[0].startswith("remove duplicated classes")
    assert "planfile ticket done PLF-1321" in driven[0]


def test_run_cycle_llm_ready_skips_redrive_on_recent_in_memory_chat_activity(
    tmp_path,
    monkeypatch,
) -> None:
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-2001:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    driven: list[str] = []

    class RecordingClient:
        def drive(self, prompt: str, **_kwargs):
            driven.append(prompt)
            return {"ok": True, "backend": "plugin"}

    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setattr(
        "koruide.chat_history.has_recent_activity",
        lambda **_kwargs: (_ for _ in ()).throw(AssertionError("must use state.autopilot_events")),
    )
    monkeypatch.setattr(
        autonomous_mod,
        "run_planfile_queue_loop",
        lambda **kwargs: SimpleNamespace(
            summary=lambda: "iterations=1 completed=0 failed=0 waiting=1 last_status=waiting_input",
            last_status="waiting_input",
            last_message="continue CQRS refactor",
            waiting=["PLF-2001"],
        ),
    )
    state = autonomous_mod.AutoloopState(
        previous_signature="waiting_input:PLF-2001",
        stagnation_streak=0,
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 30.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Architektura: wprowadź CQRS + Event Sourcing",
            },
        ],
    )

    _scan_result, queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=3,
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
    assert autopilot_status == "skipped(chat_activity)"
    assert driven == []


def test_skip_due_to_recent_chat_activity_passes_events_to_llx_reflection(
    tmp_path,
    monkeypatch,
) -> None:
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-2010:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2010"],
        last_status="waiting_input",
        last_message="Wprowadź separację Command/Query",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 12.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Wprowadź separację Command/Query",
            },
        ],
        last_driven_prompt="Wprowadź separację Command/Query",
    )
    reflection_calls: dict[str, object] = {}

    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: True)

    def _fake_reflect_on_chat(**kwargs):
        reflection_calls["events"] = kwargs.get("events")
        return SimpleNamespace(done=True, needs_input=False, summary="LLM finished")

    monkeypatch.setattr("koru.llm_reflect.reflect_on_chat", _fake_reflect_on_chat)

    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert telemetry.get("autopilot_skipped_chat_activity") is True
    assert isinstance(telemetry.get("autopilot_llx_reflection"), dict)
    assert telemetry["autopilot_llx_reflection"]["done"] is True
    events = reflection_calls.get("events")
    assert isinstance(events, list)
    assert events
    assert events[-1].type == "message.sent"


def test_extract_needs_input_question_prefers_recent_received_question() -> None:
    question = autonomous_cycle_mod._extract_needs_input_question(
        [
            SimpleNamespace(
                type="message.received",
                text="I can continue, but which API gateway environment should be targeted?",
                summary="",
            ),
        ],
        "needs operator input",
    )

    assert "which api gateway environment should be targeted?" in question.lower()


def test_skip_due_to_recent_chat_activity_creates_operator_ticket_on_needs_input(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2012"],
        last_status="waiting_input",
        last_message="Missing deployment constraint for API gateway",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Please continue with CQRS rollout",
            },
            {
                "ts": autonomous_cycle_mod.time.time() - 5.0,
                "type": "message.received",
                "ide": "vscode",
                "chat": "default",
                "text": "I can continue, but which API gateway environment should be targeted?",
            },
        ],
        last_driven_prompt="Please continue with CQRS rollout",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: True)
    monkeypatch.setattr(
        "koru.llm_reflect.reflect_on_chat",
        lambda **_kwargs: SimpleNamespace(
            done=False,
            needs_input=True,
            summary="LLM needs more operator input.",
        ),
    )

    created_calls: list[dict[str, object]] = []

    def _fake_create_nl_task(project: Path, text: str, **kwargs):
        created_calls.append({"project": project, "text": text, "kwargs": kwargs})
        return SimpleNamespace(ticket_id="PLF-9901", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert len(created_calls) == 1
    assert created_calls[0]["kwargs"]["queue_name"] == "operator"
    assert created_calls[0]["kwargs"]["priority"] == "high"
    assert "which API gateway environment should be targeted?" in created_calls[0]["text"]
    assert telemetry.get("autopilot_llx_operator_ticket") == "PLF-9901"
    assert state.last_operator_needs_input_ticket_id == "PLF-9901"


def test_skip_due_to_recent_chat_activity_dedupes_needs_input_ticket_upsert(
    tmp_path,
    monkeypatch,
) -> None:
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-2013:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2013"],
        last_status="waiting_input",
        last_message="Need endpoint contract details",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 6.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Continue with local_manager bounded context",
            },
        ],
        last_driven_prompt="Continue with local_manager bounded context",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: True)
    monkeypatch.setattr(
        "koru.llm_reflect.reflect_on_chat",
        lambda **_kwargs: SimpleNamespace(
            done=False,
            needs_input=True,
            summary="LLM asks for endpoint contract details.",
        ),
    )

    create_calls: list[str] = []

    def _fake_create_nl_task(_project: Path, _text: str, **_kwargs):
        create_calls.append("create")
        return SimpleNamespace(ticket_id="PLF-9902", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry_first: dict[str, object] = {}
    telemetry_second: dict[str, object] = {}
    assert (
        autonomous_cycle_mod._skip_due_to_recent_chat_activity(
            project=tmp_path,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=telemetry_first,
            _hp=lambda _msg: None,
        )
        is True
    )
    assert (
        autonomous_cycle_mod._skip_due_to_recent_chat_activity(
            project=tmp_path,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=telemetry_second,
            _hp=lambda _msg: None,
        )
        is True
    )

    assert create_calls == ["create"]
    assert telemetry_second.get("autopilot_llx_operator_ticket") == "PLF-9902"


def test_skip_due_to_recent_chat_activity_uses_heuristic_without_llx(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2014"],
        last_status="waiting_input",
        last_message="Need API context",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Continue deployment task",
            },
            {
                "ts": autonomous_cycle_mod.time.time() - 5.0,
                "type": "message.received",
                "ide": "vscode",
                "chat": "default",
                "text": "Which API gateway environment should be targeted?",
            },
        ],
        last_driven_prompt="Continue deployment task",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    created_calls: list[dict[str, object]] = []

    def _fake_create_nl_task(project: Path, text: str, **kwargs):
        created_calls.append({"project": project, "text": text, "kwargs": kwargs})
        return SimpleNamespace(ticket_id="PLF-9903", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )

    assert should_skip is True
    assert len(created_calls) == 1
    assert "Which API gateway environment should be targeted?" in created_calls[0]["text"]
    assert telemetry.get("autopilot_needs_input_heuristic") is True
    assert telemetry.get("autopilot_llx_operator_ticket") == "PLF-9903"


def test_skip_due_to_recent_chat_activity_uses_openrouter_reflection_fallback(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_PLANNING_LLM", "1")
    monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2014"],
        last_status="waiting_input",
        last_message="Need API context",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Continue deployment task",
            },
            {
                "ts": autonomous_cycle_mod.time.time() - 5.0,
                "type": "message.received",
                "ide": "vscode",
                "chat": "default",
                "text": "Done with the task.",
            },
        ],
        last_driven_prompt="Continue deployment task",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    calls: dict[str, object] = {}

    def _fake_openrouter_reflect(**kwargs):
        calls["chat_events"] = kwargs.get("chat_events")
        return SimpleNamespace(done=True, needs_input=False, summary="OpenRouter says done")

    monkeypatch.setattr(
        "koru.autonomy.planning_llm.reflect_on_chat",
        _fake_openrouter_reflect,
    )

    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert telemetry.get("autopilot_skipped_chat_activity") is True
    assert isinstance(telemetry.get("autopilot_llx_reflection"), dict)
    assert telemetry["autopilot_llx_reflection"]["done"] is True
    chat_events = calls.get("chat_events")
    assert isinstance(chat_events, list)
    assert chat_events


def test_skip_due_to_recent_chat_activity_heuristic_can_be_disabled(
    tmp_path,
    monkeypatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_LLM_NEEDS_INPUT_HEURISTIC", "0")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2015"],
        last_status="waiting_input",
        last_message="Need API context",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 7.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Continue deployment task",
            },
            {
                "ts": autonomous_cycle_mod.time.time() - 4.0,
                "type": "message.received",
                "ide": "vscode",
                "chat": "default",
                "text": "Which API gateway environment should be targeted?",
            },
        ],
        last_driven_prompt="Continue deployment task",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    create_calls: list[str] = []

    def _fake_create_nl_task(_project: Path, _text: str, **_kwargs):
        create_calls.append("create")
        return SimpleNamespace(ticket_id="PLF-9904", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )

    assert should_skip is True
    assert create_calls == []
    assert telemetry.get("autopilot_needs_input_heuristic") is None


def test_phase4_advisory_prioritize_tickets_emits_event(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_PLANNING_LLM_PRIORITIZE_TICKETS", "1")
    monkeypatch.delenv("KORU_PLANNING_LLM_STRATEGY_TUNING", raising=False)

    monkeypatch.setattr(
        autonomous_cycle_mod,
        "_load_open_tickets_for_planning",
        lambda *_args, **_kwargs: [
            {"id": "PLF-1", "title": "A", "status": "open"},
            {"id": "PLF-2", "title": "B", "status": "open"},
        ],
    )
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "_llm_prioritize_tickets",
        lambda **_kwargs: SimpleNamespace(
            ordered_ticket_ids=("PLF-2", "PLF-1"),
            reason="B first",
            confidence=0.8,
        ),
    )

    emitted: list[tuple[str, dict[str, object]]] = []
    cycle_telemetry: dict[str, object] = {}
    autonomous_cycle_mod._run_phase4_advisory_hooks(
        project=tmp_path,
        state=autonomous_mod.AutoloopState(),
        cycle=3,
        queue_result=QueueLoopResult(1, [], [], [], "idle", ""),
        queue_name=None,
        cycle_telemetry=cycle_telemetry,
        _hp=lambda _msg: None,
        _emit=lambda event, payload: emitted.append((event, payload)),
    )

    assert emitted
    assert emitted[0][0] == "LlmTicketPriority"
    assert emitted[0][1]["ordered_ticket_ids"] == ["PLF-2", "PLF-1"]
    assert isinstance(cycle_telemetry.get("llm_ticket_priority"), dict)


def test_phase4_advisory_strategy_tuning_emits_event(monkeypatch, tmp_path) -> None:
    monkeypatch.setenv("KORU_PLANNING_LLM_STRATEGY_TUNING", "1")
    monkeypatch.delenv("KORU_PLANNING_LLM_PRIORITIZE_TICKETS", raising=False)

    monkeypatch.setattr(
        autonomous_cycle_mod,
        "load_recent_decisions",
        lambda *_args, **_kwargs: [{"cycle": 1, "skip_code": "idle_streak"}],
    )
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "load_autonomy_strategy",
        lambda *_args, **_kwargs: {"id": "accordion"},
    )
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "_llm_propose_strategy_tuning",
        lambda **_kwargs: SimpleNamespace(
            reason="Reduce idle interval",
            confidence=0.6,
            patch="idle_discovery:\n  min_interval_seconds: 30",
        ),
    )

    emitted: list[tuple[str, dict[str, object]]] = []
    cycle_telemetry: dict[str, object] = {}
    autonomous_cycle_mod._run_phase4_advisory_hooks(
        project=tmp_path,
        state=autonomous_mod.AutoloopState(),
        cycle=4,
        queue_result=QueueLoopResult(1, [], [], [], "idle", ""),
        queue_name=None,
        cycle_telemetry=cycle_telemetry,
        _hp=lambda _msg: None,
        _emit=lambda event, payload: emitted.append((event, payload)),
    )

    assert emitted
    assert emitted[0][0] == "LlmStrategyTuningAdvice"
    assert isinstance(cycle_telemetry.get("llm_strategy_tuning"), dict)


def test_skip_chat_activity_blocks_redrive_for_llm_ready_ticket(
    tmp_path, monkeypatch
) -> None:
    """llm-ready tickets keep cooldown even when message.received is missing."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-2001:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2001"],
        last_status="waiting_input",
        last_message="continue CQRS refactor",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 30.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Architektura: wprowadź CQRS",
            },
        ],
    )
    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )
    assert should_skip is True
    assert telemetry.get("autopilot_skipped_chat_activity") is True
    assert not any("redrive allowed" in line for line in logs)


def test_skip_chat_activity_allows_llm_ready_redrive_after_no_change_verdict(
    tmp_path, monkeypatch
) -> None:
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-2001:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2001"],
        last_status="waiting_input",
        last_message="continue CQRS refactor",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 30.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Architektura: wprowadź CQRS",
            },
        ],
        last_drive_verdict={"outcome": "no_change", "confidence": 0.1},
    )
    telemetry: dict[str, object] = {}
    logs: list[str] = []

    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is False
    assert telemetry.get("autopilot_skipped_chat_activity") is None
    assert any("no_change after drive" in line for line in logs)


def test_skip_chat_activity_allows_redrive_when_sent_without_received(
    tmp_path, monkeypatch
) -> None:
    """Regression: message.sent without any message.received must not block
    waiting_input redrive — false-positive submits on Wayland still log sent."""
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "cursor")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-184"],
        last_status="waiting_input",
        last_message="CQRS task",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 120.0,
                "type": "message.sent",
                "ide": "cursor",
                "chat": "default",
                "text": "Architektura: wprowadź CQRS",
            },
        ],
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)
    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )
    assert should_skip is False
    assert any("redrive allowed" in line for line in logs)


def test_skip_chat_activity_upserts_external_chat_intake_ticket(
    tmp_path, monkeypatch
) -> None:
    """External IDE chat intake should create/reuse an operator ticket."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3001:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3001"],
        last_status="waiting_input",
        last_message="continue",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "/home/tom/github/semcod/koru",
            },
        ],
        last_driven_prompt="Ticket PLF-3001 has been stuck in status 'waiting_input'",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    created_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_create_nl_task(_project: Path, text: str, **kwargs):
        created_calls.append((text, kwargs))
        return SimpleNamespace(ticket_id="PLF-INTAKE-1", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )

    assert should_skip is True
    assert len(created_calls) == 1
    assert "Incoming intake" in created_calls[0][0]
    scaffold = created_calls[0][1]["scaffold"]
    assert scaffold["title"] == "[OPERATOR] intake from IDE chat"
    assert "waiting:PLF-3001" not in scaffold["labels"]
    assert scaffold["source_context"]["origin_waiting_ticket"] == "PLF-3001"
    assert scaffold["source_context"]["dedupe_key"].startswith("autopilot:chat-intake:")
    assert "PLF-3001" not in scaffold["source_context"]["dedupe_key"]
    assert telemetry.get("autopilot_chat_intake_ticket") == "PLF-INTAKE-1"
    assert telemetry.get("autopilot_skipped_chat_intake") is True


def test_skip_chat_activity_treats_short_explicit_sent_text_as_intake(
    tmp_path, monkeypatch
) -> None:
    """Short explicit intake snippets must become tickets, not old-ticket redrives."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3003:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3003"],
        last_status="waiting_input",
        last_message="continue",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "fix: x",
            },
        ],
        last_driven_prompt="Ticket PLF-3003 has been stuck in status 'waiting_input'",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    created_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_create_nl_task(_project: Path, text: str, **kwargs):
        created_calls.append((text, kwargs))
        return SimpleNamespace(ticket_id="PLF-INTAKE-3", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    logs: list[str] = []
    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert len(created_calls) == 1
    assert "fix: x" in created_calls[0][0]
    assert not any("redrive allowed" in line for line in logs)
    assert telemetry.get("autopilot_chat_intake_ticket") == "PLF-INTAKE-3"


def test_skip_chat_activity_does_not_reupsert_current_chat_intake_ticket(
    tmp_path, monkeypatch
) -> None:
    """An intake ticket must not recursively create/reuse itself every cycle."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3005:
      labels: [llm-ready, autopilot-chat-intake]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3005"],
        last_status="waiting_input",
        last_message="[OPERATOR] intake from IDE chat",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "fix: x",
            },
        ],
        last_driven_prompt="",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    create_calls: list[str] = []

    def _fake_create_nl_task(_project: Path, _text: str, **_kwargs):
        create_calls.append("create")
        return SimpleNamespace(ticket_id="PLF-INTAKE-5", reused=True)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )

    assert should_skip is True
    assert create_calls == []
    assert telemetry.get("autopilot_chat_intake_ticket") is None


def test_skip_chat_activity_prefers_external_intake_over_self_drive_cooldown(
    tmp_path, monkeypatch
) -> None:
    """External intake should upsert ticket even when self-drive cooldown is active."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3010:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3010"],
        last_status="waiting_input",
        last_message="continue",
    )
    now = autonomous_cycle_mod.time.time()
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": now - 24.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Ticket PLF-3010 has been stuck in status 'waiting_input' for 5 cycles",
            },
            {
                "ts": now - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "bug: koru auto misroutes copy-paste intake",
            },
        ],
        last_driven_prompt="Ticket PLF-3010 has been stuck in status 'waiting_input' for 5 cycles",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    create_calls: list[tuple[str, dict[str, object]]] = []

    def _fake_create_nl_task(_project: Path, text: str, **kwargs):
        create_calls.append((text, kwargs))
        return SimpleNamespace(ticket_id="PLF-INTAKE-10", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert len(create_calls) == 1
    assert "Incoming intake" in create_calls[0][0]
    assert "bug: koru auto misroutes copy-paste intake" in create_calls[0][0]
    assert telemetry.get("autopilot_chat_intake_ticket") == "PLF-INTAKE-10"
    assert telemetry.get("autopilot_skipped_chat_intake") is True
    assert not any("recent_self_drive" in line for line in logs)


def test_skip_chat_activity_blocks_self_drive_even_without_ticket_ack(
    tmp_path, monkeypatch
) -> None:
    """A recent Koru-driven message.sent should cooldown even if ticket ack state is stale."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3004:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    prompt = "`project/analysis.toon.yaml` reports `autonomous_main` with CC=15."
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3004"],
        last_status="waiting_input",
        last_message=prompt,
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 30.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": prompt,
            },
        ],
        last_driven_prompt=prompt,
        last_driven_ticket_id="",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    logs: list[str] = []
    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    assert telemetry.get("autopilot_skipped_chat_activity") is True
    assert any("recent_self_drive" in line for line in logs)
    assert not any("redrive allowed" in line for line in logs)


def test_skip_chat_activity_does_not_ticket_self_driven_message(
    tmp_path, monkeypatch
) -> None:
    """Recent message.sent matching last driven prompt should not create intake ticket."""
    sprint_dir = tmp_path / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True)
    (sprint_dir / "current.yaml").write_text(
        """
sprint:
  tickets:
    PLF-3002:
      labels: [llm-ready]
""",
        encoding="utf-8",
    )
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    sent_text = "REFACTOR item from project analysis"
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-3002"],
        last_status="waiting_input",
        last_message="continue",
    )
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 8.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": sent_text,
            },
        ],
        last_driven_prompt=sent_text,
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    create_calls: list[str] = []

    def _fake_create_nl_task(_project: Path, _text: str, **_kwargs):
        create_calls.append("create")
        return SimpleNamespace(ticket_id="PLF-INTAKE-2", reused=False)

    monkeypatch.setattr(autonomous_cycle_mod, "create_nl_task", _fake_create_nl_task)

    telemetry: dict[str, object] = {}
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=lambda _msg: None,
    )

    assert should_skip is True
    assert create_calls == []
    assert telemetry.get("autopilot_chat_intake_ticket") is None


def test_autopilot_escalation_cooldown_applies_after_escalation_prompt(
    tmp_path, monkeypatch
) -> None:
    """Regression: an escalation_prompt drive must trigger a 30-min cooldown.

    Previously the autopilot loop kept re-driving the same
    'Ticket X has been stuck in waiting_input for N cycles' nudge every cycle
    (~30 s apart), trampling on whatever the IDE-side LLM was answering.
    After the previous drive's ``decision.kind == "escalation_prompt"`` the
    next cycle's cooldown must extend to ``KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS``
    (default 1800 s) so a real human or the IDE LLM has time to reply.
    """
    monkeypatch.setenv("KORU_AUTOPILOT_INSTANCE", "vscode")
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "60")
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2099"],
        last_status="waiting_input",
        last_message="Continue CQRS work",
    )
    # message.sent 5 minutes ago. With the legacy 60s cooldown we'd allow the
    # redrive; but because last_driven_kind=='escalation_prompt' the cooldown
    # must extend to 1800 s and the skip must fire.
    state = autonomous_mod.AutoloopState(
        autopilot_events=[
            {
                "ts": autonomous_cycle_mod.time.time() - 300.0,
                "type": "message.sent",
                "ide": "vscode",
                "chat": "default",
                "text": "Ticket PLF-2099 has been stuck in status 'waiting_input' for 3 cycles…",
            },
        ],
        last_driven_prompt="Ticket PLF-2099 has been stuck…",
        last_driven_kind="escalation_prompt",
    )
    monkeypatch.setattr("koru.llm_reflect.llm_reflect_enabled", lambda: False)

    telemetry: dict[str, object] = {}
    logs: list[str] = []
    should_skip = autonomous_cycle_mod._skip_due_to_recent_chat_activity(
        project=tmp_path,
        queue_result=queue_result,
        state=state,
        cycle_telemetry=telemetry,
        _hp=logs.append,
    )

    assert should_skip is True
    # Skip log line includes the *extended* cooldown (1800s) — proving the
    # multiplier kicked in instead of the bare 60s default.
    assert any("cooldown=1800" in line for line in logs)


def test_reply_chat_input_busy_recognizes_plugin_ack_shape() -> None:
    """Regression: koru autonomous must recognize plugin 0.1.50's input_busy ack.

    When the plugin pre-checks the chat input and finds un-submitted text it
    NACKs with ``verification="input_busy"`` and ``reason="chat_input_not_empty"``.
    The autonomous loop must short-circuit retries instead of hammering the
    drive five times per cycle (which would race with the user's typing).
    """
    busy = autonomous_cycle_mod._reply_chat_input_busy(
        {
            "ok": False,
            "verification": "input_busy",
            "reason": "chat_input_not_empty",
            "message": "chat input already contains un-submitted text",
        }
    )
    assert busy is True

    # Negative cases: success ack and unrelated failure must NOT match.
    assert (
        autonomous_cycle_mod._reply_chat_input_busy(
            {"ok": True, "verification": "strict"}
        )
        is False
    )
    assert (
        autonomous_cycle_mod._reply_chat_input_busy(
            {"ok": False, "verification": "submit_unverified"}
        )
        is False
    )


def test_submit_unverified_drive_failure_is_not_retryable(monkeypatch) -> None:
    sleeps: list[int] = []
    monkeypatch.setattr("koru.autonomous_drive_retry_policy.time.sleep", lambda seconds: sleeps.append(seconds))

    should_retry = drive_retry_mod._handle_failed_drive_attempt(
        {
            "ok": False,
            "submitted": False,
            "verification": "submit_unverified",
            "attempted_submit": "ydotool key ctrl+Return",
            "message": "chat opened and text injected, but submit could not be verified",
        },
        attempt=0,
        attempts=5,
    )

    assert should_retry is False
    assert sleeps == []


def test_submit_unverified_drive_status_is_specific() -> None:
    telemetry: dict[str, object] = {}
    status = cycle_orchestrator_mod._drive_result_autopilot_status(
        queue_result=QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=["STARTER-298"],
            last_status="waiting_input",
        ),
        reply={
            "ok": False,
            "verification": "submit_unverified",
            "submit_failure_reason": "input still contains pasted text",
        },
        ok=False,
        decision_kind="ticket_prompt",
        cycle_telemetry=telemetry,
    )

    assert status == "failed(submit_unverified)"
    assert telemetry["autopilot_submit_unverified"] is True
    assert telemetry["autopilot_submit_unverified_reason"] == "input still contains pasted text"


def test_submit_unverified_previous_drive_skips_redrive(tmp_path: Path) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-299"],
        last_status="waiting_input",
    )
    state = autonomous_mod.AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        last_driven_ticket_id="STARTER-299",
        stagnation_streak=1,
    )
    telemetry: dict[str, object] = {}
    lines: list[str] = []

    should_skip, reason = skip_conditions_mod._check_autopilot_skip_conditions(
        tmp_path,
        queue_result,
        state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        diag_result=autonomous_cycle_mod.DiagnosticResult("skipped", []),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lines.append,
    )

    assert should_skip is True
    assert reason == "skipped(manual_send_required)"
    assert telemetry["autopilot_submit_unverified"] is True
    assert telemetry["autopilot_skipped_manual_send_required"] is True
    assert any("manual_send_required" in line for line in lines)


def test_submit_unverified_previous_drive_allows_alt_strategy_before_limit(
    tmp_path: Path,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-299"],
        last_status="waiting_input",
    )
    state = autonomous_mod.AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        last_driven_ticket_id="STARTER-299",
        submit_unverified_streak=1,
        pending_submit_strategy_hint="submit_alt_registered",
        stagnation_streak=1,
    )
    telemetry: dict[str, object] = {}
    lines: list[str] = []

    should_skip, reason = skip_conditions_mod._check_autopilot_skip_conditions(
        tmp_path,
        queue_result,
        state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="waiting_input",
        diag_result=autonomous_cycle_mod.DiagnosticResult("skipped", []),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lines.append,
    )

    assert should_skip is False
    assert reason == ""
    assert telemetry["autopilot_submit_alt_retry_allowed"] is True
    assert telemetry["autopilot_submit_unverified_streak"] == 1
    assert any("alternate submit strategy" in line for line in lines)


def test_submit_unverified_previous_drive_does_not_block_next_ticket(tmp_path: Path) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-302"],
        last_status="waiting_input",
    )
    state = autonomous_mod.AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        last_driven_ticket_id="STARTER-301",
        stagnation_streak=1,
    )
    telemetry: dict[str, object] = {}

    should_skip, reason = skip_conditions_mod._check_autopilot_skip_conditions(
        tmp_path,
        queue_result,
        state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="",
        diag_result=autonomous_cycle_mod.DiagnosticResult("skipped", []),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lambda _line: None,
    )

    assert should_skip is False
    assert reason == ""
    assert state.last_autopilot_status == ""
    assert telemetry["autopilot_submit_unverified_cleared_for_new_ticket"] is True
    assert telemetry["autopilot_submit_unverified_previous_ticket"] == "STARTER-301"
    assert telemetry["autopilot_submit_unverified_current_ticket"] == "STARTER-302"


def test_submit_unverified_previous_drive_clears_after_message_sent_same_ticket(
    tmp_path: Path,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-437"],
        last_status="waiting_input",
    )
    state = autonomous_mod.AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        last_driven_ticket_id="STARTER-437",
        last_submit_unverified_ticket_id="STARTER-437",
        last_submit_unverified_ts=100.0,
        last_message_sent_ts=101.0,
        stagnation_streak=1,
    )
    telemetry: dict[str, object] = {}

    should_skip, reason = skip_conditions_mod._check_autopilot_skip_conditions(
        tmp_path,
        queue_result,
        state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="",
        diag_result=autonomous_cycle_mod.DiagnosticResult("skipped", []),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lambda _line: None,
    )

    assert should_skip is False
    assert reason == ""
    assert state.last_autopilot_status == ""
    assert state.last_submit_unverified_ts == 0.0
    assert state.last_submit_unverified_ticket_id == ""
    assert telemetry["autopilot_submit_unverified_cleared_by_message_sent"] is True
    assert telemetry["autopilot_submit_unverified_current_ticket"] == "STARTER-437"


def test_submit_unverified_previous_drive_not_cleared_by_stale_message_sent(
    tmp_path: Path,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-437"],
        last_status="waiting_input",
    )
    state = autonomous_mod.AutoloopState(
        last_autopilot_status="failed(submit_unverified)",
        last_driven_ticket_id="STARTER-437",
        last_submit_unverified_ticket_id="STARTER-437",
        last_submit_unverified_ts=100.0,
        last_message_sent_ts=99.0,
        stagnation_streak=1,
    )
    telemetry: dict[str, object] = {}

    should_skip, reason = skip_conditions_mod._check_autopilot_skip_conditions(
        tmp_path,
        queue_result,
        state,
        autopilot_action="drive",
        autopilot_on_idle_only=False,
        autopilot_skip_on_diagnostics_fail=False,
        autopilot_skip_drive_idle_streak=0,
        autopilot_skip_statuses="",
        diag_result=autonomous_cycle_mod.DiagnosticResult("skipped", []),
        topology_integration=False,
        cycle_telemetry=telemetry,
        _hp=lambda _line: None,
    )

    assert should_skip is True
    assert reason == "skipped(manual_send_required)"
    assert telemetry["autopilot_skipped_manual_send_required"] is True


def test_resolve_autopilot_drive_decision_includes_recent_llx_summary(
    tmp_path,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2011"],
        last_status="waiting_input",
        last_message="Wydziel commands/queries/events",
    )
    state = autonomous_mod.AutoloopState(
        last_llm_reflection_summary="Commands i queries zostały rozdzielone; teraz dodaj event-store i event-bus.",
        last_llm_reflection_ts=autonomous_cycle_mod.time.time(),
    )

    decision, idle_kind = autonomous_cycle_mod._resolve_autopilot_drive_decision(
        tmp_path,
        state,
        queue_result,
        drive_prompt="ignored",
        autopilot_action="drive",
    )

    assert idle_kind is None
    assert decision.kind == "ticket_prompt"
    assert "Recent IDE chat context:" in decision.prompt
    assert "event-store i event-bus" in decision.prompt
    assert "Do not restart from scratch" in decision.prompt


def test_resolve_autopilot_drive_decision_skips_closed_waiting_ticket(
    tmp_path,
    monkeypatch,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2011"],
        last_status="waiting_input",
        last_message="continue",
    )
    state = autonomous_mod.AutoloopState()
    monkeypatch.setattr(drive_retry_mod, "_planfile_ticket_status", lambda *_args: "done")

    decision, idle_kind = drive_retry_mod._resolve_autopilot_drive_decision(
        tmp_path,
        state,
        queue_result,
        drive_prompt="ignored",
        autopilot_action="drive",
    )

    assert idle_kind is None
    assert decision.skip is True
    assert decision.skip_reason == "waiting_ticket_closed"


def test_resolve_autopilot_drive_decision_does_not_skip_closed_waiting_ticket_when_disabled(
    tmp_path,
    monkeypatch,
) -> None:
    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["PLF-2011"],
        last_status="waiting_input",
        last_message="continue",
    )
    state = autonomous_mod.AutoloopState()
    monkeypatch.setenv("KORU_AUTOPILOT_SKIP_CLOSED_WAITING_TICKET", "0")
    monkeypatch.setattr(drive_retry_mod, "_planfile_ticket_status", lambda *_args: "done")

    decision, idle_kind = drive_retry_mod._resolve_autopilot_drive_decision(
        tmp_path,
        state,
        queue_result,
        drive_prompt="ignored",
        autopilot_action="drive",
    )

    assert idle_kind is None
    assert decision.skip is False
    assert decision.kind == "ticket_prompt"


def test_autopilot_idle_without_open_ticket_does_not_drive(
    tmp_path,
    monkeypatch,
) -> None:
    class Client:
        def drive(self, *_args, **_kwargs):
            raise AssertionError("idle queue without open tickets must not drive")

    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=[],
        last_status="idle",
        last_message="",
        last_ticket_id=None,
    )
    messages: list[str] = []
    monkeypatch.setattr(
        autonomous_cycle_mod,
        "resolve_idle_drive_prompt",
        lambda *_args, **_kwargs: ("continue with the next ticket", "idle_no_ticket"),
    )

    status, backend, kind = autonomous_cycle_mod._handle_autopilot_phase(
        tmp_path,
        autonomous_mod.AutoloopState(),
        1,
        queue_result,
        True,
        Client(),
        "auto",
        "continue with the next ticket",
        True,
        "drive",
        False,
        True,
        0,
        "waiting_input",
        autonomous_cycle_mod.DiagnosticResult("ok", []),
        False,
        {},
        messages.append,
        lambda *_args, **_kwargs: None,
    )

    assert status == "skipped(idle_no_ticket)"
    assert backend is None
    assert kind == "idle_no_ticket"
    assert any("idle_no_ticket" in message for message in messages)
    assert any("/llm/action/create-ticket-for-project" in message for message in messages)
    assert not any("open the dashboard at http://127.0.0.1:8765/" in message for message in messages)


def test_handle_autopilot_phase_waiting_ticket_closed_sets_skip_status_and_telemetry(
    tmp_path,
    monkeypatch,
) -> None:
    from koru import autonomous_cycle_orchestrator as orchestrator_mod

    class Client:
        def drive(self, *_args, **_kwargs):
            raise AssertionError("closed waiting ticket path must skip before drive")

    queue_result = QueueLoopResult(
        iterations=1,
        completed=[],
        failed=[],
        waiting=["STARTER-239"],
        last_status="waiting_input",
        last_message="continue",
        last_ticket_id="STARTER-239",
    )
    messages: list[str] = []
    telemetry: dict[str, object] = {}
    monkeypatch.setattr(
        orchestrator_mod,
        "_check_autopilot_skip_conditions",
        lambda *_args, **_kwargs: (False, ""),
    )
    monkeypatch.setattr(
        orchestrator_mod,
        "_execute_autopilot_drive",
        lambda *_args, **_kwargs: (
            {
                "ok": False,
                "backend": None,
                "message": "waiting ticket STARTER-239 is already closed",
                "prompt": "",
            },
            False,
            "waiting_ticket_closed",
            None,
        ),
    )

    status, backend, kind = autonomous_cycle_mod._handle_autopilot_phase(
        tmp_path,
        autonomous_mod.AutoloopState(),
        1,
        queue_result,
        True,
        Client(),
        "auto",
        "continue with the next ticket",
        True,
        "drive",
        False,
        True,
        0,
        "",
        autonomous_cycle_mod.DiagnosticResult("ok", []),
        False,
        telemetry,
        messages.append,
        lambda *_args, **_kwargs: None,
    )

    assert status == "skipped(waiting_ticket_closed)"
    assert backend is None
    assert kind == "waiting_ticket_closed"
    assert telemetry["autopilot_skipped_waiting_ticket_closed"] is True
    assert telemetry["autopilot_skipped_waiting_ticket_closed_ticket"] == "STARTER-239"


def test_run_cycle_autopilot_uses_os_injector_fallback_on_plugin_failure(
    tmp_path,
    monkeypatch,
) -> None:
    class FailingClient:
        def drive(self, *_args, **_kwargs):
            return {"ok": False, "backend": "plugin", "message": "submit failed"}

    monkeypatch.setattr("koru.autonomy.env.detect_terminal_host_ide_id", lambda: None)
    monkeypatch.setenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "1")
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
    _force_idle_drive_prompt(monkeypatch)
    fallback_calls: list[dict] = []
    monkeypatch.setattr(
        "koru.autonomous_cycle_gate.try_os_injector_fallback_with_deps",
        lambda prompt, *, submit, load_profile_fn, inject_with_profile_fn, os_injector_error: (
            fallback_calls.append({"prompt": prompt, "submit": submit})
            or {"ok": True, "backend": "os_injector", "submitted": submit}
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


def test_run_cycle_plugin_required_failure_skips_os_injector_fallback(
    tmp_path,
    monkeypatch,
) -> None:
    import time

    drive_calls: list[dict] = []
    fallback_calls: list[dict] = []

    class FailingClient:
        def drive(self, *_args, **kwargs):
            drive_calls.append(kwargs)
            return {"ok": False, "backend": "plugin", "message": "no connected plugin"}

    monkeypatch.delenv("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_PREFER_KEYBOARD", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_VISIBLE_TYPING", raising=False)
    monkeypatch.setenv("KORU_OS_INJECTOR_PROFILE", "windsurf")
    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
    monkeypatch.setattr(
        autonomous_mod,
        "_try_os_injector_fallback",
        lambda *args, **kwargs: (
            fallback_calls.append({"args": args, "kwargs": kwargs})
            or {"ok": True, "backend": "os_injector"}
        ),
    )
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
    _force_idle_drive_prompt(monkeypatch)

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
    assert autopilot_status == "failed"
    assert drive_calls
    assert all(call["require_plugin"] is True for call in drive_calls)
    assert fallback_calls == []


def test_run_cycle_autopilot_focus_error_retry_loop_retries_and_warns(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import time
    calls = []

    class FocusErrorClient:
        def drive(self, *_args, **_kwargs):
            calls.append(None)
            # Fail with focus/verification error
            return {
                "ok": False,
                "message": "chat input is not focused",
                "verification": "plugin_error",
                "diagnostics": {
                    "ide": "vscodium",
                    "appName": "VSCodium",
                    "logPath": "/tmp/koru-plugin-debug.log",
                    "focusOpenCandidates": ["workbench.action.chat.open"],
                    "rejected": [{"cmd": "workbench.action.chat.open", "reason": "probe rejected focus snapshot"}],
                },
            }

    # Mock time.sleep to make the test instant
    monkeypatch.setattr(time, "sleep", lambda x: None)

    # Disable OS injector fallback by returning None
    monkeypatch.setattr(autonomous_mod, "_try_os_injector_fallback", lambda *a, **k: None)

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
    _force_idle_drive_prompt(monkeypatch)

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
        client=FocusErrorClient(),
    )

    # Identical-failure dedup breaks out after the second attempt rather than
    # wasting 25 s on five identical retries (see
    # `_drive_failure_signature` in `koru.autonomous_cycle_drive_retry`).
    assert len(calls) == 2
    assert autopilot_status == "failed"

    captured = capsys.readouterr().out
    assert "[AUTOPILOT FOCUS ERROR]" in captured
    assert "Plugin message: chat input is not focused" in captured
    assert "ide: vscodium" in captured
    assert "logPath: /tmp/koru-plugin-debug.log" in captured
    assert "focusOpenCandidates: workbench.action.chat.open" in captured
    assert "lastRejected:" in captured
    assert "identical failure repeated" in captured


def test_run_cycle_autopilot_plugin_retry_loop_for_windsurf_fastpath_failure(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import time

    calls: list[None] = []

    class FastPathErrorClient:
        def drive(self, *_args, **_kwargs):
            calls.append(None)
            return {
                "ok": False,
                "message": "chat opened but paste command failed (fast path failed)",
                "verification": "plugin_error",
                "diagnostics": {
                    "ide": "windsurf",
                    "appName": "Windsurf",
                    "logPath": "/tmp/koru-plugin-debug.log",
                },
            }

    monkeypatch.setattr(time, "sleep", lambda _x: None)
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
    _force_idle_drive_prompt(monkeypatch)

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
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
        client=FastPathErrorClient(),
    )

    # Identical-failure dedup applies to the plugin-retry path too: the loop
    # stops after seeing the same signature twice rather than five times.
    assert len(calls) == 2
    assert autopilot_status == "failed"
    captured = capsys.readouterr().out
    assert "[AUTOPILOT PLUGIN RETRY]" in captured
    assert "Plugin message: chat opened but paste command failed (fast path failed)" in captured
    assert "[AUTOPILOT FOCUS ERROR]" not in captured
    assert "identical failure repeated" in captured


def test_run_cycle_does_not_retry_missing_plugin_as_focus_error(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import time

    calls: list[int] = []

    class MissingPluginClient:
        def drive(self, *_args, **_kwargs):
            calls.append(1)
            return {
                "ok": False,
                "message": "no connected autopilot plugin for ide=vscode",
            }

    monkeypatch.setattr(time, "sleep", lambda _x: None)
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
    _force_idle_drive_prompt(monkeypatch)

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=MissingPluginClient(),
    )

    assert calls == [1]
    assert autopilot_status == "failed"
    assert "[AUTOPILOT FOCUS ERROR]" not in capsys.readouterr().out


def test_run_cycle_does_not_retry_semantic_required_as_focus_error(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import time

    calls: list[int] = []

    class SemanticRequiredClient:
        def drive(self, *_args, **_kwargs):
            calls.append(1)
            return {
                "ok": False,
                "backend": "semantic_required",
                "message": (
                    "refusing blind keyboard/OS-injector fallback on Wayland for JetBrains "
                    "after vdisplay/imgl did not confirm the target"
                ),
            }

    monkeypatch.setattr(time, "sleep", lambda _x: None)
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
    _force_idle_drive_prompt(monkeypatch)

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="jetbrains",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=SemanticRequiredClient(),
    )

    assert calls == [1]
    assert autopilot_status == "failed"
    captured = capsys.readouterr().out
    assert "[AUTOPILOT SEMANTIC TARGET REQUIRED]" in captured
    assert "screencast start --force" in captured
    assert "[AUTOPILOT FOCUS ERROR]" not in captured
    assert "Retrying in 5 seconds" not in captured


def test_run_cycle_does_not_retry_when_plugin_requires_manual_focus(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    import time

    calls: list[int] = []

    class ManualFocusClient:
        def drive(self, *_args, **_kwargs):
            calls.append(1)
            return {
                "ok": False,
                "message": "chat input is not focused/open; focus_open_candidates=(none)",
                "verification": "plugin_error",
                "diagnostics": {
                    "ide": "vscode",
                    "appName": "Visual Studio Code",
                    "logPath": "/tmp/koru-plugin-debug.log",
                    "probeLadder": True,
                    "cacheFocusOpen": "workbench.panel.chat",
                    "focusOpenCandidates": [],
                },
            }

    monkeypatch.setattr(time, "sleep", lambda _seconds: None)
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
    _force_idle_drive_prompt(monkeypatch)

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=ManualFocusClient(),
    )

    assert calls == [1]
    assert autopilot_status == "skipped(manual_focus)"
    captured = capsys.readouterr().out
    assert "[AUTOPILOT FOCUS REQUIRED]" in captured
    assert "Retrying in 5 seconds" not in captured
    assert "focusOpenCandidates: (none)" in captured
    assert "autopilot: failed" not in captured


def test_log_autopilot_result_reports_manual_focus_as_skipped() -> None:
    messages: list[str] = []
    autonomous_cycle_mod._log_autopilot_result(
        False,
        QueueLoopResult(
            iterations=1,
            completed=[],
            failed=[],
            waiting=["PLF-1"],
            last_status="waiting_input",
            last_message="",
            last_ticket_id="PLF-1",
        ),
        "vscode",
        "escalation_prompt",
        {
            "ok": False,
            "message": "chat input is not focused/open; focus_open_candidates=(none)",
            "verification": "plugin_error",
            "diagnostics": {"focusOpenCandidates": []},
        },
        messages.append,
    )

    assert messages == [
        "  autopilot: skipped(manual_focus) "
        "(chat input is not focused/open; focus_open_candidates=(none), kind=escalation_prompt)",
    ]


def test_run_cycle_skips_drive_when_required_plugin_missing(
    tmp_path,
    monkeypatch,
    capsys,
) -> None:
    drive_calls: list[int] = []

    class MissingPluginClient:
        def status(self):
            return {"plugins": []}

        def drive(self, *_args, **_kwargs):
            drive_calls.append(1)
            return {"ok": True}

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
    monkeypatch.delenv("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", raising=False)

    _scan_result, _queue_result, autopilot_status, _diag = autonomous_mod._run_cycle(
        cycle=1,
        project=tmp_path,
        actor="koru-test",
        queue_name=None,
        enable_scan=False,
        max_iterations=50,
        enable_autopilot=True,
        autopilot_ide="vscode",
        drive_prompt="continue with the next ticket",
        submit=True,
        include_semcod_artifacts=False,
        client=MissingPluginClient(),
    )

    assert autopilot_status == "skipped(plugin_not_connected)"
    assert drive_calls == []
    captured = capsys.readouterr()
    assert "plugin_not_connected" in captured.out
    assert "koru ▸ OBS:" in captured.err

    from koru.observability_writer import observability_event_store_path

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    assert [row["event_type"] for row in rows] == [
        "autopilot.intent",
        "autopilot.route.decision",
        "autopilot.drive.failed",
        "autonomy.blocker",
        "autonomy.next",
    ]
    assert rows[0]["payload"]["data"]["goal"] == "deliver_prompt_to_ide_chat"
    assert rows[1]["payload"]["data"]["because"] == "plugin_not_connected"
    assert rows[2]["payload"]["data"]["code"] == "plugin_not_connected"
    assert rows[3]["payload"]["data"]["name"] == "plugin_not_connected"
    assert rows[4]["payload"]["data"]["action"] == "reload_reconnect_plugin"


def test_run_cycle_visible_typing_does_not_require_plugin(
    tmp_path,
    monkeypatch,
) -> None:
    drive_calls: list[dict] = []

    class RecordingClient:
        def drive(self, prompt, **kwargs):
            drive_calls.append(kwargs)
            return {"ok": True, "backend": "stub"}

    monkeypatch.setattr("koru.autonomy.env.detect_terminal_host_ide_id", lambda: None)
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
    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
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


def test_wup_compose_service_ready_rejects_unhealthy_or_stopped() -> None:
    assert not autonomous_wup_mod._compose_service_ready([])
    assert not autonomous_wup_mod._compose_service_ready(
        [{"State": "running", "Health": "unhealthy", "Status": "Up 2 seconds"}],
    )
    assert not autonomous_wup_mod._compose_service_ready(
        [{"State": "exited", "Health": "healthy", "Status": "Exited"}],
    )


def test_wup_compose_service_ready_accepts_status_when_state_missing() -> None:
    assert autonomous_wup_mod._compose_service_ready(
        [{"Health": "", "Status": "Up 2 seconds"}],
    )
    assert not autonomous_wup_mod._compose_service_ready(
        [{"Health": "", "Status": "Created"}],
    )


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


def test_read_wup_health_sanitizes_slash_in_service_marker_path(tmp_path) -> None:
    """WUP service ids like ``src/koru`` must not become nested marker dirs."""
    health_dir = tmp_path / ".wup"
    health_dir.mkdir()
    (health_dir / "service-health.json").write_text(
        json.dumps(
            {
                "src/koru": {
                    "status": "failed",
                    "stage": "quick",
                    "message": "cli-koru.testql.toon.yaml",
                    "track_file": "/tmp/track.json",
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
    assert result.failing_services == ["src/koru"]
    marker = tmp_path / ".planfile/.koru/autoloop-diag/wup-src_koru.failed"
    assert marker.exists()
    assert marker.read_text(encoding="utf-8").strip()


def test_read_wup_health_ignores_stale_services_not_in_wup_yaml(tmp_path) -> None:
    """Renamed WUP services must not keep ``service-health.json`` rows blocking autopilot."""
    from koru.tasks import create_nl_task

    (tmp_path / "wup.yaml").write_text(
        "services:\n  - name: koru-shell\n    type: shell\n",
        encoding="utf-8",
    )
    health_dir = tmp_path / ".wup"
    health_dir.mkdir()
    diag_dir = tmp_path / ".planfile/.koru/autoloop-diag"
    diag_dir.mkdir(parents=True)
    stale_ticket = create_nl_task(
        tmp_path,
        "[AUTO-DIAG] wup-koru-core needs attention in cycle 0. "
        "queue_status=wup_failure. Check: old failure.",
        priority="high",
    )
    (diag_dir / "wup-koru-core.failed").write_text(stale_ticket.ticket_id, encoding="utf-8")
    (health_dir / "service-health.json").write_text(
        json.dumps(
            {
                "koru-core": {
                    "status": "down",
                    "stage": "quick",
                    "message": "old failure",
                },
                "koru-shell": {"status": "up", "stage": "quick"},
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
    assert not (diag_dir / "wup-koru-core.failed").exists()
    pruned = json.loads((health_dir / "service-health.json").read_text(encoding="utf-8"))
    assert set(pruned) == {"koru-shell"}
    sprint = yaml.safe_load((tmp_path / ".planfile/sprints/current.yaml").read_text(encoding="utf-8"))
    ticket = sprint["sprint"]["tickets"][stale_ticket.ticket_id]
    assert ticket["status"] == "done"
    assert ticket["execution"]["state"] == "done"
    assert "WUP no longer reports wup-koru-core" in ticket["outputs"]["notes"][-1]


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


def test_read_wup_health_treats_aborted_as_interrupted_not_failure(tmp_path) -> None:
    health_dir = tmp_path / ".wup"
    health_dir.mkdir()
    diag_dir = tmp_path / ".planfile/.koru/autoloop-diag"
    diag_dir.mkdir(parents=True)
    (health_dir / "service-health.json").write_text(
        json.dumps(
            {
                "koru-shell": {
                    "status": "down",
                    "stage": "quick",
                    "message": "Aborted!",
                    "track_file": ".wup/tracks/abc.json",
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

    assert result.status == "interrupted"
    assert result.failing_services == []
    assert not (diag_dir / "wup-koru-shell.failed").exists()

    normalized = json.loads((health_dir / "service-health.json").read_text(encoding="utf-8"))
    assert normalized["koru-shell"]["status"] == "interrupted"
    assert normalized["koru-shell"]["interrupted"] is True
