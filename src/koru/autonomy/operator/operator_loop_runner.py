"""Outer-loop runner for ``koru autonomous`` cycles.

This module keeps the cycle lifecycle and acts as the facade for the
extracted helper modules. Tests and callers patch/read helper names here,
and the extracted modules late-bind back through this facade so those
patches keep working.
"""

from __future__ import annotations

import sys
from typing import Any

from koru.autonomy.config import structured_cycle_report_enabled
from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_by_from_autopilot_status as _blocked_by_from_autopilot_status,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_interface_action_lines as _blocked_interface_action_lines,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_interface_detail_suffix as _blocked_interface_detail_suffix,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_interface_items as _blocked_interface_items,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _blocked_interface_recovery_suffix as _blocked_interface_recovery_suffix,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _dashboard_action_urls as _dashboard_action_urls,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _default_dashboard_action_urls as _default_dashboard_action_urls,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _format_blocked_interface_line as _format_blocked_interface_line,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _interface_matches_ide as _interface_matches_ide,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _is_plugin_blocker as _is_plugin_blocker,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _safe_dashboard_action_urls as _safe_dashboard_action_urls,
)
from koru.autonomy.operator.operator_loop_interfaces import (
    _select_blocked_interface_items as _select_blocked_interface_items,
)
from koru.autonomy.operator.operator_loop_narration import (
    AutonomyNextStepNarrator as AutonomyNextStepNarrator,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_default_steps as _handle_default_steps,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_status_completed_or_failed as _handle_status_completed_or_failed,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_status_idle as _handle_status_idle,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_status_waiting_input as _handle_status_waiting_input,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_stop_reason_max_cycles as _handle_stop_reason_max_cycles,
)
from koru.autonomy.operator.operator_loop_narration import (
    _handle_stop_reason_waiting_input as _handle_stop_reason_waiting_input,
)
from koru.autonomy.operator.operator_loop_narration import (
    _operator_next_steps as _operator_next_steps,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _autopilot_quick_action_lines as _autopilot_quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _backtick_command as _backtick_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _base_quick_action_lines as _base_quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _curl_url as _curl_url,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _diagnostics_quick_action_lines as _diagnostics_quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _emit_quick_action_line as _emit_quick_action_line,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _is_create_ticket_action as _is_create_ticket_action,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _queue_quick_action_lines as _queue_quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _quick_action_lines as _quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_backtick_command as _record_backtick_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_quick_action_control_command as _record_quick_action_control_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_quick_action_control_commands as _record_quick_action_control_commands,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_reconnect_plugin_command as _record_reconnect_plugin_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_replay_sidecar_command as _record_replay_sidecar_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _record_url_command as _record_url_command,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _replay_quick_action_lines as _replay_quick_action_lines,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _split_quick_action as _split_quick_action,
)
from koru.autonomy.operator.operator_loop_quick_actions import (
    _url_origin as _url_origin,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _current_mission_lines as _current_mission_lines,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _emit_idle_no_ticket_warning as _emit_idle_no_ticket_warning,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _idle_no_ticket_warning as _idle_no_ticket_warning,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _log_operator_next_steps as _log_operator_next_steps,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _should_warn_idle_no_ticket as _should_warn_idle_no_ticket,
)
from koru.autonomy.operator.operator_loop_reporting import (
    _slug as _slug,
)
from koru.autonomy.phases.contexts import SleepBackoffContext
from koru.autonomy.phases.sleep_phase import finish_cycle_with_sleep
from koru.autonomy.structured_report import emit_structured_cycle_report

_AUTOPILOT_BLOCKED_QUEUE_STATUSES = frozenset({"waiting_input"})


def _cycle_stop_reason(args: Any, queue_result: Any, cycle: int) -> str | None:
    from koru.global_control import is_globally_disabled

    if is_globally_disabled():
        return "global_killswitch"
    if (
        getattr(args, "stop_on_waiting_input", False)
        and queue_result.last_status in _AUTOPILOT_BLOCKED_QUEUE_STATUSES
    ):
        return "waiting_input"
    max_cycles = int(getattr(args, "max_cycles", 0) or 0)
    if max_cycles > 0 and cycle >= max_cycles:
        return "max_cycles"
    return None


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
    stop_reason = _cycle_stop_reason(args, queue_result, cycle)
    if stop_reason == "global_killswitch":
        from koru.global_control import disabled_message

        if args.emit_events == "jsonl":
            write_event(
                output_stream,
                event_type="AutonomousStopped",
                correlation_id=correlation_id,
                payload={"reason": "global_killswitch", "cycle": cycle},
            )
        stdio_info(disabled_message("autonomous"), fmt=args.emit_events)
        return True

    if stop_reason == "waiting_input":
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

    if stop_reason == "max_cycles":
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


def _save_cycle_checkpoint(
    *,
    checkpoint_path: Any,
    cycle: int,
    loop_state: Any,
    queue_result: Any,
    queue_loop_waiting_ticket_label: Any,
    save_loop_checkpoint: Any,
) -> str:
    waiting_ticket = queue_loop_waiting_ticket_label(queue_result)
    save_loop_checkpoint(
        checkpoint_path,
        cycle=cycle,
        state=loop_state,
        queue_status=queue_result.last_status,
        waiting_ticket=waiting_ticket,
    )
    return waiting_ticket


def _cycle_idle_context(project: Any, queue_result: Any) -> str:
    if queue_result.last_status != "idle":
        return ""
    from koru.autonomy.ide_work import sprint_ticket_status_summary

    return f" {sprint_ticket_status_summary(project)}"


def _emit_cycle_summary(
    *,
    args: Any,
    project: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    effective_sleep: float,
    stdio_info: Any,
) -> None:
    idle_context = _cycle_idle_context(project, queue_result)
    stdio_info(
        f"koru autonomous: summary cycle={cycle} queue={queue_result.last_status} "
        f"waiting={waiting_ticket} "
        f"streak={loop_state.stagnation_streak} diagnostics={diag_result.status} "
        f"autopilot={autopilot_status} sleep={effective_sleep}s{idle_context}",
        fmt=args.emit_events,
    )


def _emit_structured_report(
    *,
    args: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    autopilot_ide: str,
    effective_sleep: float,
) -> None:
    if args.emit_events != "human":
        return
    if not structured_cycle_report_enabled():
        return

    from koru.activity_log import activity

    def activity_fn(category: str, message: str) -> None:
        activity(category, message, fmt="human")

    emit_structured_cycle_report(
        cycle=cycle,
        queue_status=str(getattr(queue_result, "last_status", "") or ""),
        waiting_ticket=waiting_ticket,
        wup_status=str(getattr(loop_state, "wup_status", "ok")),
        diag_status=str(getattr(diag_result, "status", "") or ""),
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        stagnation_streak=int(getattr(loop_state, "stagnation_streak", 0) or 0),
        sleep_seconds=effective_sleep,
        activity_fn=activity_fn,
    )


def _print_cycle_header(args: Any, cycle: int) -> None:
    if args.emit_events == "human":
        print(f"\n=== koru autonomous cycle #{cycle} ===")


def _prepare_cycle_run(
    *,
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
    diagnostic_state_dir: Any,
    wup_process: Any | None,
    correlation_id: str,
    auto_pipeline_state: Any | None,
    cycle: int,
    restart_daemon_if_needed: Any,
    select_and_log_cycle_profile: Any,
    resolve_effective_cycle_flags: Any,
    build_cycle_run_kwargs: Any,
) -> dict[str, Any]:
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
    effective_enable_scan, effective_enable_autopilot = resolve_effective_cycle_flags(
        args,
        profile,
        enable_scan=enable_scan,
        loop_state=loop_state,
        client=client,
        autopilot_ide=autopilot_ide,
    )
    return build_cycle_run_kwargs(
        args,
        profile,
        cycle=cycle,
        project=project,
        queue_name=queue_name,
        enable_scan=effective_enable_scan,
        enable_autopilot=effective_enable_autopilot,
        autopilot_ide=autopilot_ide,
        client=client,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
    )


def _run_cycle_and_checkpoint(
    *,
    cycle_kwargs: dict[str, Any],
    cycle: int,
    loop_state: Any,
    checkpoint_path: Any,
    auto_pipeline_state: Any | None,
    run_cycle: Any,
    update_auto_pipeline_state: Any,
    save_loop_checkpoint: Any,
    queue_loop_waiting_ticket_label: Any,
) -> tuple[Any, str, Any, str]:
    _scan_result, queue_result, autopilot_status, diag_result = run_cycle(**cycle_kwargs)
    if auto_pipeline_state is not None:
        update_auto_pipeline_state(
            auto_pipeline_state,
            queue_result,
            diag_result,
            autopilot_status,
        )
    waiting_ticket = _save_cycle_checkpoint(
        checkpoint_path=checkpoint_path,
        cycle=cycle,
        loop_state=loop_state,
        queue_result=queue_result,
        queue_loop_waiting_ticket_label=queue_loop_waiting_ticket_label,
        save_loop_checkpoint=save_loop_checkpoint,
    )
    return queue_result, waiting_ticket, diag_result, autopilot_status


def _finish_cycle(
    *,
    args: Any,
    project: Any,
    cycle: int,
    queue_result: Any,
    waiting_ticket: str,
    loop_state: Any,
    diag_result: Any,
    autopilot_status: str,
    autopilot_ide: str,
    correlation_id: str,
    handle_exit_conditions: Any,
    compute_cycle_sleep: Any,
    stdio_info: Any,
    sleep: Any,
) -> bool:
    return finish_cycle_with_sleep(
        SleepBackoffContext(
            args=args,
            project=project,
            cycle=cycle,
            queue_result=queue_result,
            waiting_ticket=waiting_ticket,
            loop_state=loop_state,
            diag_result=diag_result,
            autopilot_status=autopilot_status,
            autopilot_ide=autopilot_ide,
            correlation_id=correlation_id,
        ),
        cycle_stop_reason=_cycle_stop_reason,
        emit_cycle_summary=_emit_cycle_summary,
        emit_idle_no_ticket_warning=_emit_idle_no_ticket_warning,
        log_operator_next_steps=_log_operator_next_steps,
        emit_structured_report=_emit_structured_report,
        handle_exit_conditions=handle_exit_conditions,
        compute_cycle_sleep=compute_cycle_sleep,
        stdio_info=stdio_info,
        sleep=sleep,
    )


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
    _print_cycle_header(args, cycle)
    cycle_kwargs = _prepare_cycle_run(
        args=args,
        project=project,
        client=client,
        daemon=daemon,
        thread=thread,
        socket_path=socket_path,
        autopilot_socket_observed_at_boot=autopilot_socket_observed_at_boot,
        queue_name=queue_name,
        enable_scan=enable_scan,
        autopilot_ide=autopilot_ide,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
        auto_pipeline_state=auto_pipeline_state,
        cycle=cycle,
        restart_daemon_if_needed=restart_daemon_if_needed,
        select_and_log_cycle_profile=select_and_log_cycle_profile,
        resolve_effective_cycle_flags=resolve_effective_cycle_flags,
        build_cycle_run_kwargs=build_cycle_run_kwargs,
    )
    queue_result, waiting_ticket, diag_result, autopilot_status = _run_cycle_and_checkpoint(
        cycle_kwargs=cycle_kwargs,
        cycle=cycle,
        loop_state=loop_state,
        checkpoint_path=checkpoint_path,
        auto_pipeline_state=auto_pipeline_state,
        run_cycle=run_cycle,
        update_auto_pipeline_state=update_auto_pipeline_state,
        queue_loop_waiting_ticket_label=queue_loop_waiting_ticket_label,
        save_loop_checkpoint=save_loop_checkpoint,
    )
    return _finish_cycle(
        args=args,
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        waiting_ticket=waiting_ticket,
        loop_state=loop_state,
        diag_result=diag_result,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        correlation_id=correlation_id,
        handle_exit_conditions=handle_exit_conditions,
        compute_cycle_sleep=compute_cycle_sleep,
        stdio_info=stdio_info,
        sleep=sleep,
    )


__all__ = [
    "handle_cycle_exit_conditions",
    "run_autonomous_cycle",
]
