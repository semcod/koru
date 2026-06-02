"""Sleep/backoff phase for the outer autonomous loop."""

from __future__ import annotations

from typing import Any

from koru.autonomy.phases.contexts import SleepBackoffContext


def finish_cycle_with_sleep(
    context: SleepBackoffContext,
    *,
    cycle_stop_reason: Any,
    emit_cycle_summary: Any,
    emit_idle_no_ticket_warning: Any,
    log_operator_next_steps: Any,
    emit_structured_report: Any,
    handle_exit_conditions: Any,
    compute_cycle_sleep: Any,
    stdio_info: Any,
    sleep: Any,
) -> bool:
    """Finalize one outer-loop cycle and sleep when the loop should continue."""
    effective_sleep = compute_cycle_sleep(
        context.args,
        context.loop_state,
        context.queue_result,
        context.autopilot_status,
    )
    stop_reason = cycle_stop_reason(context.args, context.queue_result, context.cycle)
    emit_cycle_summary(
        args=context.args,
        project=context.project,
        cycle=context.cycle,
        queue_result=context.queue_result,
        waiting_ticket=context.waiting_ticket,
        loop_state=context.loop_state,
        diag_result=context.diag_result,
        autopilot_status=context.autopilot_status,
        effective_sleep=effective_sleep,
        stdio_info=stdio_info,
    )
    emit_idle_no_ticket_warning(
        args=context.args,
        project=context.project,
        queue_status=str(getattr(context.queue_result, "last_status", "") or ""),
        waiting_ticket=context.waiting_ticket,
        autopilot_status=context.autopilot_status,
    )
    log_operator_next_steps(
        args=context.args,
        project=context.project,
        queue_result=context.queue_result,
        waiting_ticket=context.waiting_ticket,
        autopilot_status=context.autopilot_status,
        effective_sleep=effective_sleep,
        loop_state=context.loop_state,
        stop_reason=stop_reason,
        stdio_info=stdio_info,
        autopilot_ide=context.autopilot_ide,
    )
    emit_structured_report(
        args=context.args,
        cycle=context.cycle,
        queue_result=context.queue_result,
        waiting_ticket=context.waiting_ticket,
        loop_state=context.loop_state,
        diag_result=context.diag_result,
        autopilot_status=context.autopilot_status,
        autopilot_ide=context.autopilot_ide,
        effective_sleep=effective_sleep,
    )
    if handle_exit_conditions(
        context.args,
        context.queue_result,
        context.cycle,
        context.correlation_id,
    ):
        return True

    if effective_sleep > 0:
        sleep(effective_sleep)
    return False
