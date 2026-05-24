"""Tests for the autonomous outer-loop runner."""

from __future__ import annotations

from types import SimpleNamespace

from koru import autonomous_loop_runner


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
    args = SimpleNamespace(emit_events="human", max_iterations=50, scan_after_idle_queue=True)

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
    assert logs[1:4] == [
        "koru autonomous: next 1/3 wait 4.5s; no runnable ticket is blocking the queue",
        "koru autonomous: next 2/3 run idle intake strategy next cycle "
        "(scan/code2llm discovery is eligible)",
        "koru autonomous: next 3/3 create/upsert new planfile tickets from findings, "
        "then work them one by one",
    ]
    assert sleeps == [4.5]


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
        "so Koru will not paste over the IDE chat",
        "2/3 rerun planfile queue (max 12) and check whether STARTER-217 moved",
        "3/3 if queue becomes idle, run scan/discovery; if still waiting, "
        "use chat events/reflection before any redrive",
    ]
