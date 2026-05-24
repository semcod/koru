"""Outer-loop runner for ``koru autonomous`` cycles."""

from __future__ import annotations

import sys
from typing import Any


_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


def _operator_next_steps(
    *,
    args: Any,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    stagnation_streak: int,
) -> list[str]:
    """Human-readable plan for the next outer-loop moves."""
    status = str(getattr(queue_result, "last_status", "") or "")
    max_iterations = int(getattr(args, "max_iterations", 50) or 50)
    ticket = waiting_ticket if waiting_ticket and waiting_ticket != "-" else "none"
    sleep_text = f"{effective_sleep:g}s"

    if status == "waiting_input":
        if "chat_activity" in autopilot_status:
            first = (
                f"1/3 wait {sleep_text}; chat cooldown is active for {ticket}, "
                "so Koru will not paste over the IDE chat"
            )
        elif "plugin_missing" in autopilot_status:
            first = (
                f"1/3 wait {sleep_text}; keep queue on {ticket} while the IDE "
                "plugin reconnects"
            )
        else:
            first = f"1/3 wait {sleep_text}; keep current waiting ticket {ticket} scoped"
        return [
            first,
            f"2/3 rerun planfile queue (max {max_iterations}) and check whether {ticket} moved",
            (
                "3/3 if queue becomes idle, run scan/discovery; if still waiting, "
                "use chat events/reflection before any redrive"
            ),
        ]

    if status == "idle":
        discovery = (
            "scan/code2llm discovery is eligible"
            if getattr(args, "scan_after_idle_queue", False)
            else "idle scan is disabled unless explicitly requested"
        )
        return [
            f"1/3 wait {sleep_text}; no runnable ticket is blocking the queue",
            f"2/3 run idle intake strategy next cycle ({discovery})",
            "3/3 create/upsert new planfile tickets from findings, then work them one by one",
        ]

    if status in {"completed", "failed"}:
        return [
            f"1/3 wait {sleep_text}; queue just reported {status}",
            f"2/3 rerun planfile queue (max {max_iterations}) to pick the next ticket",
            "3/3 if no ticket remains, switch to idle scan/discovery strategy",
        ]

    return [
        f"1/3 wait {sleep_text}; preserve current loop state (streak={stagnation_streak})",
        f"2/3 rerun queue/status checks for status={status or 'unknown'}",
        "3/3 choose scan, ticket drive, or operator input based on the next queue result",
    ]


def _log_operator_next_steps(
    *,
    args: Any,
    queue_result: Any,
    waiting_ticket: str,
    autopilot_status: str,
    effective_sleep: float,
    loop_state: Any,
    stdio_info: Any,
) -> None:
    for line in _operator_next_steps(
        args=args,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        stagnation_streak=int(getattr(loop_state, "stagnation_streak", 0) or 0),
    ):
        stdio_info(f"koru autonomous: next {line}", fmt=args.emit_events)


def handle_cycle_exit_conditions(
    args: Any,
    queue_result: Any,
    cycle: int,
    correlation_id: str,
    *,
    write_event: Any,
    stdio_info: Any,
    output_stream: Any = sys.stdout,
) -> bool:
    """Return True when the autonomous loop should stop after a cycle."""
    if args.stop_on_waiting_input and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES:
        if args.emit_events == "jsonl":
            write_event(
                output_stream,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": "waiting_input", "cycle": cycle},
            )
        stdio_info(
            "koru autonomous: queue is waiting_input; stopping until "
            "human/manual ticket recovery marks it ready or done",
            fmt=args.emit_events,
        )
        return True

    if args.max_cycles > 0 and cycle >= args.max_cycles:
        if args.emit_events == "jsonl":
            write_event(
                output_stream,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={
                    "reason": "max_cycles",
                    "cycle": cycle,
                    "max_cycles": args.max_cycles,
                },
            )
        stdio_info(
            f"koru autonomous: reached max-cycles={args.max_cycles}; stopping",
            fmt=args.emit_events,
        )
        return True
    return False


def run_autonomous_cycle(
    *,
    cycle: int,
    args: Any,
    project: Any,
    client: Any,
    daemon: Any,
    thread: Any,
    socket_path: Any,
    autopilot_socket_observed_at_boot: bool,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    loop_state: Any,
    checkpoint_path: Any,
    diagnostic_state_dir: Any,
    wup_process: Any | None,
    correlation_id: str,
    auto_pipeline_state: Any | None,
    restart_daemon_if_needed: Any,
    select_and_log_cycle_profile: Any,
    resolve_effective_cycle_flags: Any,
    build_cycle_run_kwargs: Any,
    run_cycle: Any,
    update_auto_pipeline_state: Any,
    save_loop_checkpoint: Any,
    queue_loop_waiting_ticket_label: Any,
    handle_exit_conditions: Any,
    compute_cycle_sleep: Any,
    stdio_info: Any,
    sleep: Any,
) -> bool:
    """Run one autonomous cycle and return True when the loop should exit."""
    if args.emit_events == "human":
        print(f"\n=== koru autonomous cycle #{cycle} ===")
    client, daemon, thread = restart_daemon_if_needed(
        args,
        client,
        socket_path,
        daemon,
        thread,
        autopilot_socket_observed_at_boot,
        project,
    )
    profile = select_and_log_cycle_profile(
        args,
        auto_pipeline_state,
        enable_scan=enable_scan,
    )
    effective_enable_scan, _effective_enable_autopilot = resolve_effective_cycle_flags(
        args,
        profile,
        enable_scan=enable_scan,
        loop_state=loop_state,
        client=client,
        autopilot_ide=autopilot_ide,
    )
    cycle_kwargs = build_cycle_run_kwargs(
        args,
        profile,
        cycle=cycle,
        project=project,
        queue_name=queue_name,
        enable_scan=effective_enable_scan,
        autopilot_ide=autopilot_ide,
        client=client,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
    )
    _scan_result, queue_result, autopilot_status, diag_result = run_cycle(**cycle_kwargs)
    if auto_pipeline_state is not None:
        update_auto_pipeline_state(
            auto_pipeline_state,
            queue_result,
            diag_result,
            autopilot_status,
        )
    save_loop_checkpoint(
        checkpoint_path,
        cycle=cycle,
        state=loop_state,
        queue_status=queue_result.last_status,
        waiting_ticket=queue_loop_waiting_ticket_label(queue_result),
    )

    if handle_exit_conditions(args, queue_result, cycle, correlation_id):
        return True

    effective_sleep = compute_cycle_sleep(args, loop_state, queue_result)
    waiting_ticket = queue_loop_waiting_ticket_label(queue_result)
    stdio_info(
        f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
        f"waiting={waiting_ticket} "
        f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
        f"autopilot={autopilot_status} sleep={effective_sleep}s",
        fmt=args.emit_events,
    )
    _log_operator_next_steps(
        args=args,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        autopilot_status=autopilot_status,
        effective_sleep=effective_sleep,
        loop_state=loop_state,
        stdio_info=stdio_info,
    )
    if effective_sleep > 0:
        sleep(effective_sleep)
    return False


__all__ = [
    "handle_cycle_exit_conditions",
    "run_autonomous_cycle",
]
