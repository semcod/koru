"""Tests for the autonomous outer-loop runner."""

from __future__ import annotations

import json
from types import SimpleNamespace

from koru import autonomous_loop_runner
from koru.observability_writer import observability_event_store_path


def test_handle_cycle_exit_conditions_stops_on_waiting_input() -> None:
    events: list[dict] = []
    logs: list[str] = []
    args = SimpleNamespace(stop_on_waiting_input=True, emit_events="jsonl", max_cycles=0)
    queue_result = SimpleNamespace(last_status="waiting_input")

    result = autonomous_loop_runner.handle_cycle_exit_conditions(
        args,
        queue_result,
        7,
        "corr-1",
        write_event=lambda _stream, **payload: events.append(payload),
        stdio_info=lambda msg, **_kwargs: logs.append(msg),
        output_stream=object(),
    )

    assert result is True
    assert events == [
        {
            "event_type": "AutonomousStopped",
            "correlation_id": "corr-1",
            "payload": {"reason": "waiting_input", "cycle": 7},
        }
    ]
    assert "queue is waiting_input" in logs[0]


def test_run_autonomous_cycle_checkpoints_updates_pipeline_and_sleeps() -> None:
    calls: dict[str, object] = {}
    logs: list[str] = []
    sleeps: list[float] = []
    queue_result = SimpleNamespace(last_status="idle")
    diag_result = SimpleNamespace(status="ok")
    loop_state = SimpleNamespace(stagnation_streak=2)
    args = SimpleNamespace(
        emit_events="human",
        max_cycles=0,
        max_iterations=50,
        scan_after_idle_queue=True,
        stop_on_waiting_input=False,
    )

    def restart_daemon_if_needed(*args):
        calls["restart_args"] = args
        return "client2", "daemon2", "thread2"

    def build_cycle_run_kwargs(*_args, **kwargs):
        calls["cycle_kwargs_source"] = kwargs
        return {"token": "cycle"}

    result = autonomous_loop_runner.run_autonomous_cycle(
        cycle=3,
        args=args,
        project="project",
        client="client",
        daemon="daemon",
        thread="thread",
        socket_path="socket",
        autopilot_socket_observed_at_boot=True,
        queue_name=None,
        enable_scan=True,
        autopilot_ide="windsurf",
        loop_state=loop_state,
        checkpoint_path="checkpoint",
        diagnostic_state_dir="diagnostics",
        wup_process=None,
        correlation_id="corr-2",
        auto_pipeline_state="pipeline-state",
        restart_daemon_if_needed=restart_daemon_if_needed,
        select_and_log_cycle_profile=lambda *_args, **_kwargs: "profile",
        resolve_effective_cycle_flags=lambda *_args, **_kwargs: (False, True),
        build_cycle_run_kwargs=build_cycle_run_kwargs,
        run_cycle=lambda **kwargs: (None, queue_result, "ok", diag_result),
        update_auto_pipeline_state=lambda *args: calls.setdefault("pipeline_update", args),
        save_loop_checkpoint=lambda *args, **kwargs: calls.setdefault(
            "checkpoint",
            (args, kwargs),
        ),
        queue_loop_waiting_ticket_label=lambda _queue_result: "-",
        handle_exit_conditions=lambda *_args: False,
        compute_cycle_sleep=lambda *_args: 4.5,
        stdio_info=lambda msg, **_kwargs: logs.append(msg),
        sleep=lambda seconds: sleeps.append(seconds),
    )

    assert result is False
    assert calls["restart_args"] == (
        args,
        "client",
        "socket",
        "daemon",
        "thread",
        True,
        "project",
    )
    assert calls["cycle_kwargs_source"]["enable_scan"] is False
    assert calls["pipeline_update"] == ("pipeline-state", queue_result, diag_result, "ok")
    assert calls["checkpoint"] == (
        ("checkpoint",),
        {
            "cycle": 3,
            "state": loop_state,
            "queue_status": "idle",
            "waiting_ticket": "-",
        },
    )
    assert "summary cycle=3 queue=idle" in logs[0]
    assert logs[1].startswith(
        "koru autonomous: next 1/3 wait 4.5s; queue is idle"
    )
    assert "all planfile tickets" in logs[1]
    assert logs[2].startswith(
        "koru autonomous: next 2/3 strategy detail→general: "
        "planfile ticket queue first"
    )
    assert "code2llm whole-project discovery" in logs[2]
    assert logs[3].startswith("koru autonomous: next 3/3 quick links:")
    assert "/llm/action/create-ticket-for-project" in logs[3]
    assert "/?tab=tickets" in logs[3]
    assert sleeps == [4.5]


def test_idle_no_ticket_warning_points_to_web_gui(monkeypatch) -> None:
    warnings: list[tuple[str, dict[str, object]]] = []

    def capture_warning(message: str, **kwargs: object) -> None:
        warnings.append((message, kwargs))

    monkeypatch.setattr("koru.activity_log.activity_warn", capture_warning)

    autonomous_loop_runner._emit_idle_no_ticket_warning(
        args=SimpleNamespace(emit_events="human"),
        project="project",
        queue_status="idle",
        waiting_ticket="-",
        autopilot_status="skipped(idle_no_ticket)",
    )

    assert len(warnings) == 1
    message, kwargs = warnings[0]
    assert "brak otwartych ticketów" in message
    assert kwargs["fmt"] == "human"
    assert "/llm/prompt/create-ticket-for-project" in str(kwargs["hint"])
    assert "lista ticketów" in str(kwargs["hint"])
    assert "szczegół→ogół" in str(kwargs["hint"])
    assert "workflow standaryzowany" in str(kwargs["hint"])
    assert "Co jeszcze zostalo do wykonania?" in str(kwargs["hint"])
    assert "prefact/metrun" in str(kwargs["hint"])
    assert kwargs["data"]["blocked_by"] == "idle_no_ticket"


def test_create_ticket_quick_action_is_warn_highlighted(monkeypatch) -> None:
    warnings: list[tuple[str, dict[str, object]]] = []
    info_lines: list[str] = []

    def capture_warning(message: str, **kwargs: object) -> None:
        warnings.append((message, kwargs))

    monkeypatch.setattr("koru.activity_log.activity_warn", capture_warning)

    autonomous_loop_runner._emit_quick_action_line(
        args=SimpleNamespace(emit_events="human"),
        action="[create ticket] http://127.0.0.1:8765/llm/action/create-ticket-for-project",
        stdio_info=lambda message, **_kwargs: info_lines.append(message),
    )

    assert info_lines == []
    assert len(warnings) == 1
    message, kwargs = warnings[0]
    assert "action [create ticket]" in message
    assert "brak otwartych ticketów" in str(kwargs["hint"])
    assert kwargs["data"] == {"action": "create_ticket", "blocked_by": "idle_no_ticket"}


def test_run_autonomous_cycle_logs_plan_before_max_cycles_exit() -> None:
    logs: list[str] = []
    queue_result = SimpleNamespace(last_status="waiting_input")
    diag_result = SimpleNamespace(status="skipped")
    loop_state = SimpleNamespace(stagnation_streak=1)
    args = SimpleNamespace(
        emit_events="human",
        max_cycles=3,
        max_iterations=50,
        scan_after_idle_queue=True,
        stop_on_waiting_input=False,
    )

    result = autonomous_loop_runner.run_autonomous_cycle(
        cycle=3,
        args=args,
        project="project",
        client="client",
        daemon="daemon",
        thread="thread",
        socket_path="socket",
        autopilot_socket_observed_at_boot=True,
        queue_name=None,
        enable_scan=True,
        autopilot_ide="vscode",
        loop_state=loop_state,
        checkpoint_path="checkpoint",
        diagnostic_state_dir="diagnostics",
        wup_process=None,
        correlation_id="corr-3",
        auto_pipeline_state=None,
        restart_daemon_if_needed=lambda *_args: ("client", "daemon", "thread"),
        select_and_log_cycle_profile=lambda *_args, **_kwargs: None,
        resolve_effective_cycle_flags=lambda *_args, **_kwargs: (True, True),
        build_cycle_run_kwargs=lambda *_args, **_kwargs: {"token": "cycle"},
        run_cycle=lambda **_kwargs: (None, queue_result, "skipped(chat_activity)", diag_result),
        update_auto_pipeline_state=lambda *_args: None,
        save_loop_checkpoint=lambda *_args, **_kwargs: None,
        queue_loop_waiting_ticket_label=lambda _queue_result: "STARTER-217",
        handle_exit_conditions=lambda *call_args: (
            autonomous_loop_runner.handle_cycle_exit_conditions(
                *call_args,
                write_event=lambda *_args, **_kwargs: None,
                stdio_info=lambda msg, **_kwargs: logs.append(msg),
                output_stream=object(),
            )
        ),
        compute_cycle_sleep=lambda *_args: 60.0,
        stdio_info=lambda msg, **_kwargs: logs.append(msg),
        sleep=lambda _seconds: None,
    )

    assert result is True
    assert "summary cycle=3 queue=waiting_input" in logs[0]
    assert logs[1:6] == [
        "koru autonomous: current mission ticket=STARTER-217 "
        "queue=waiting_input blocker=chat_activity",
        "koru autonomous: current mission next=wait 60s for chat cooldown, "
        "then reconsider redrive (tune: KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS)",
        "koru autonomous: next 1/3 stop now; reached max-cycles=3",
        "koru autonomous: next 2/3 preserve checkpoint with queue=waiting_input "
        "waiting=STARTER-217",
        "koru autonomous: next 3/3 next koru auto run will continue from the saved checkpoint",
    ]
    assert any("reached max-cycles=3" in line for line in logs[6:])
    assert any("[show decision trace]" in line for line in logs), (
        "operator log must include quick action links after next-step lines"
    )
    assert any("[show interfaces]" in line for line in logs), (
        "operator log should expose the registry view alongside decision trace"
    )


def test_operator_next_steps_explain_waiting_input_chat_cooldown() -> None:
    steps = autonomous_loop_runner._operator_next_steps(
        args=SimpleNamespace(max_iterations=12),
        queue_result=SimpleNamespace(last_status="waiting_input"),
        waiting_ticket="STARTER-217",
        autopilot_status="skipped(chat_activity)",
        effective_sleep=60.0,
        stagnation_streak=1,
    )

    assert steps == [
        "1/3 wait 60s; chat cooldown is active for STARTER-217, "
        "so Koru will not paste over the IDE chat; this is not a daemon failure",
        "2/3 rerun planfile queue (max 12) and check whether STARTER-217 moved",
        "3/3 if queue becomes idle, run scan/discovery; if still waiting, "
        "use chat events/reflection before any redrive",
    ]


def test_next_step_narrator_returns_exactly_three_lines() -> None:
    narrator = autonomous_loop_runner.AutonomyNextStepNarrator(
        args=SimpleNamespace(max_iterations=50, scan_after_idle_queue=True),
        project="project",
        waiting_ticket="STARTER-239",
    )
    lines = narrator.narrate(
        queue_status="waiting_input",
        autopilot_status="skipped(plugin_missing)",
        sleep_seconds=240.0,
        stagnation_streak=5,
        stop_reason=None,
    )

    assert len(lines) == 3
    assert lines[0].startswith("1/3 wait 240s; keep queue on STARTER-239")


def test_current_mission_lines_include_ticket_and_plugin_blocker() -> None:
    lines = autonomous_loop_runner._current_mission_lines(
        queue_result=SimpleNamespace(last_status="waiting_input"),
        waiting_ticket="STARTER-239",
        autopilot_status="skipped(plugin_missing)",
        effective_sleep=30.0,
    )

    assert lines == [
        "koru autonomous: current mission ticket=STARTER-239 "
        "queue=waiting_input blocker=plugin_missing",
        "koru autonomous: current mission next=reload/reconnect plugin, "
        "then rerun queue for the same ticket",
    ]


def test_quick_action_lines_include_registry_backed_blocked_interface_hint() -> None:
    actions = autonomous_loop_runner._quick_action_lines(
        project="project",
        queue_status="waiting_input",
        waiting_ticket="STARTER-239",
        autopilot_status="skipped(plugin_missing)",
        autopilot_ide="vscodium",
    )

    assert any("[show interfaces]" in line for line in actions)
    assert any("[blocked interface]" in line for line in actions)
    assert any("plugin_socket_vscode_family" in line for line in actions)
    assert not any("plugin_socket_jetbrains" in line for line in actions)


def test_quick_action_create_ticket_uses_fast_action_endpoint() -> None:
    actions = autonomous_loop_runner._quick_action_lines(
        project=None,
        queue_status="idle",
        waiting_ticket="-",
        autopilot_status="skipped(idle_no_ticket)",
        autopilot_ide="vscodium",
    )

    create = next(line for line in actions if line.startswith("[create ticket]"))
    assert "/llm/action/create-ticket-for-project" in create
    assert "/llm/prompt/create-ticket-for-project" not in create


def test_quick_action_submit_unverified_surfaces_trace_instead_of_retry() -> None:
    actions = autonomous_loop_runner._quick_action_lines(
        project=None,
        queue_status="waiting_input",
        waiting_ticket="STARTER-249",
        autopilot_status="failed(submit_unverified)",
        autopilot_ide="vscodium",
    )

    assert not any(line.startswith("[retry submit]") for line in actions)
    assert any(line.startswith("[validate submit trace]") for line in actions)
    assert any("Manual IDE action required: submit was not verified" in line for line in actions)


def test_quick_action_open_ticket_reuses_dashboard_tickets_url_with_hash(
    monkeypatch,
) -> None:
    monkeypatch.setattr(
        autonomous_loop_runner,
        "_dashboard_action_urls",
        lambda _project: {
            "dashboard": "http://127.0.0.1:8765/",
            "create_project_ticket": "http://127.0.0.1:8765/llm/prompt/create-ticket-for-project",
            "create_project_ticket_action": "http://127.0.0.1:8765/llm/action/create-ticket-for-project",
            "tickets": "http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Frepo&ide=vscode",
        },
    )

    actions = autonomous_loop_runner._quick_action_lines(
        project="project",
        queue_status="waiting_input",
        waiting_ticket="STARTER-248",
        autopilot_status="skipped(chat_activity)",
        autopilot_ide="vscode",
    )

    open_ticket = next(line for line in actions if line.startswith("[open ticket] "))
    assert open_ticket.startswith("[open ticket] http://127.0.0.1:8765/?tab=tickets&project=%2Ftmp%2Frepo&ide=vscode")
    assert open_ticket.endswith("#STARTER-248")


def test_blocked_interface_action_lines_filter_to_jetbrains_lane() -> None:
    actions = autonomous_loop_runner._blocked_interface_action_lines(
        "plugin_missing",
        autopilot_ide="jetbrains",
    )

    assert any("plugin_socket_jetbrains" in line for line in actions)
    assert not any("plugin_socket_vscode_family" in line for line in actions)


def test_current_mission_lines_treat_plugin_version_mismatch_as_plugin_blocker() -> None:
    lines = autonomous_loop_runner._current_mission_lines(
        queue_result=SimpleNamespace(last_status="waiting_input"),
        waiting_ticket="STARTER-215",
        autopilot_status="skipped(plugin_version_mismatch)",
        effective_sleep=30.0,
    )

    assert lines == [
        "koru autonomous: current mission ticket=STARTER-215 "
        "queue=waiting_input blocker=plugin_version_mismatch",
        "koru autonomous: current mission next=reload/reconnect plugin, "
        "then rerun queue for the same ticket",
    ]


def test_operator_quick_actions_emit_replayable_control_commands(tmp_path) -> None:
    args = SimpleNamespace(emit_events="human", max_iterations=50)
    logs: list[str] = []

    autonomous_loop_runner._log_operator_next_steps(
        args=args,
        project=tmp_path,
        queue_result=SimpleNamespace(last_status="waiting_input"),
        waiting_ticket="STARTER-277",
        autopilot_status="skipped(plugin_not_connected)",
        effective_sleep=240.0,
        loop_state=SimpleNamespace(stagnation_streak=3),
        stop_reason=None,
        stdio_info=lambda msg, **_kwargs: logs.append(msg),
        autopilot_ide="vscodium",
    )

    rows = [
        json.loads(raw)
        for raw in observability_event_store_path(tmp_path).read_text(encoding="utf-8").splitlines()
    ]
    commands = [row["payload"]["data"] for row in rows if row["event_type"] == "control.command"]
    surfaces = [command["surface"] for command in commands]
    operations = [command["operation"] for command in commands]
    assert "api" in surfaces
    assert "shell_cli" in surfaces
    assert "desktop_gui" in surfaces
    assert "GET /api/autonomy/trace" in operations
    assert "GET /api/interfaces" in operations
    assert "bash" in operations
    assert "command_palette_sequence" in operations
    assert any("koru replay" in str(command["args"]) for command in commands)
    assert any("ticket input STARTER-277" in str(command["args"]) for command in commands)
