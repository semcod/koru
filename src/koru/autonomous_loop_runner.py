"""Outer-loop runner for ``koru autonomous`` cycles."""

from __future__ import annotations

import sys
from typing import Any


_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


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
    stdio_info(
        f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
        f"waiting={queue_loop_waiting_ticket_label(queue_result)} "
        f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
        f"autopilot={autopilot_status} sleep={effective_sleep}s",
        fmt=args.emit_events,
    )
    if effective_sleep > 0:
        sleep(effective_sleep)
    return False


__all__ = ["handle_cycle_exit_conditions", "run_autonomous_cycle"]
