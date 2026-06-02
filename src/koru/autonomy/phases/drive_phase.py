"""Drive and post-drive phase orchestration for autonomous cycles."""

from __future__ import annotations

from typing import Any, Callable

from koru.autonomy.phases.contexts import (
    CyclePhaseContext,
    DrivePhaseConfig,
    DrivePhaseInputs,
    DrivePhaseResult,
)


def run_drive_phase(
    context: CyclePhaseContext,
    config: DrivePhaseConfig,
    inputs: DrivePhaseInputs,
    *,
    take_pre_drive_snapshot: Callable[..., Any],
    handle_autopilot_phase: Callable[..., tuple[str, str | None, str | None]],
) -> DrivePhaseResult:
    """Run the isolated autopilot drive phase."""
    take_pre_drive_snapshot(context.project, context.state, inputs.wup_health)
    status, backend, drive_kind = handle_autopilot_phase(
        context.project,
        context.state,
        context.cycle,
        inputs.queue_result,
        config.enable_autopilot,
        config.client,
        config.autopilot_ide,
        config.drive_prompt,
        config.submit,
        config.autopilot_action,
        config.autopilot_on_idle_only,
        config.autopilot_skip_on_diagnostics_fail,
        config.autopilot_skip_drive_idle_streak,
        config.autopilot_skip_statuses,
        inputs.diag_result,
        config.topology_integration,
        inputs.cycle_telemetry,
        context.callbacks.hp,
        context.callbacks.emit,
    )
    return DrivePhaseResult(status=status, backend=backend, drive_kind=drive_kind)


def run_post_drive_phase(
    context: CyclePhaseContext,
    config: DrivePhaseConfig,
    inputs: DrivePhaseInputs,
    drive_result: DrivePhaseResult,
    *,
    handle_post_drive_verification: Callable[..., Any],
    run_advisory_hooks: Callable[..., Any],
    emit_cycle_completion_events: Callable[..., Any],
) -> None:
    """Run post-drive verification, advisory hooks, and completion emission."""
    handle_post_drive_verification(
        context.project,
        context.state,
        context.cycle,
        inputs.queue_result,
        drive_result.status,
        inputs.wup_health,
        context.callbacks.hp,
        context.callbacks.emit,
    )
    run_advisory_hooks(
        project=context.project,
        state=context.state,
        cycle=context.cycle,
        queue_result=inputs.queue_result,
        queue_name=config.queue_name,
        cycle_telemetry=inputs.cycle_telemetry,
        _hp=context.callbacks.hp,
        _emit=context.callbacks.emit,
    )
    emit_cycle_completion_events(
        project=context.project,
        state=context.state,
        cycle=context.cycle,
        queue_result=inputs.queue_result,
        diag_result=inputs.diag_result,
        wup_health=inputs.wup_health,
        drive_status=drive_result.status,
        autopilot_ide=config.autopilot_ide,
        autopilot_backend=drive_result.backend,
        autopilot_drive_kind=drive_result.drive_kind,
        cycle_telemetry=inputs.cycle_telemetry,
        scan_after_idle_queue=config.scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=config.scan_after_idle_min_interval_seconds,
        autopilot_skip_drive_idle_streak=config.autopilot_skip_drive_idle_streak,
        hp=context.callbacks.hp,
        emit=context.callbacks.emit,
    )
