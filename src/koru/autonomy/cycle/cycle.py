
import json  # noqa: F401
import os
import subprocess  # noqa: F401
import sys
import time  # noqa: F401
from pathlib import Path
from typing import Any

from koruide.ide import detect_terminal_host_ide_id

from koru.autonomy.cycle.cycle_chat_activity import (
    _autopilot_redrive_cooldown_seconds,
    _extract_needs_input_question,
    _skip_due_to_recent_chat_activity,
)
from koru.autonomy.cycle.cycle_common import DiagnosticResult, _queue_loop_waiting_ticket_label  # noqa: F401
from koru.autonomy.cycle.cycle_drive_retry import (
    _log_autopilot_result,
    _reply_chat_input_busy,
    _resolve_autopilot_drive_decision,
)
from koru.autonomy.cycle.cycle_orchestrator import _handle_autopilot_phase
from koru.autonomy.cycle.cycle_post_drive import (
    _handle_post_drive_verification as _handle_post_drive_verification_impl,
)
from koru.autonomy.cycle.cycle_post_drive import (
    _take_pre_drive_snapshot as _take_pre_drive_snapshot_impl,
)
from koru.autonomy.cycle.cycle_skip_conditions import (
    _is_topology_enabled,  # noqa: F401
)
from koru.autonomy.cycle_diagnostics import _clear_diagnostic_marker as _clear_diagnostic_marker
from koru.autonomy.cycle_diagnostics import _create_diagnostic_ticket as _create_diagnostic_ticket
from koru.autonomy.cycle_diagnostics import _current_head as _current_head
from koru.autonomy.cycle_diagnostics import _handle_diagnostics as _handle_diagnostics
from koru.autonomy.cycle_diagnostics import _read_wup_health as _read_wup_health
from koru.autonomy.cycle_diagnostics import _run_command_check as _run_command_check
from koru.autonomy.cycle_diagnostics import _run_idle_diagnostics as _run_idle_diagnostics
from koru.autonomy.cycle_events import _autopilot_event_path as _autopilot_event_path
from koru.autonomy.cycle_events import _coerce_event_ts as _coerce_event_ts
from koru.autonomy.cycle_events import _cycle_socket_path as _cycle_socket_path
from koru.autonomy.cycle_events import _drain_autopilot_events as _drain_autopilot_events
from koru.autonomy.cycle_events import _handle_autopilot_events as _handle_autopilot_events
from koru.autonomy.cycle_events import _heal_stale_socket as _heal_stale_socket
from koru.autonomy.cycle_finalize import (
    emit_cycle_completion_events as _emit_cycle_completion_events_impl,
)
from koru.autonomy.cycle_planning import (
    _attach_environment_profile as _attach_environment_profile,
)
from koru.autonomy.cycle_planning import (
    _initialize_cycle_telemetry as _initialize_cycle_telemetry,
)
from koru.autonomy.cycle_planning import (
    _load_open_tickets_for_planning as _load_open_tickets_for_planning,
)
from koru.autonomy.cycle_planning import (
    _load_planfile_ticket_payload as _load_planfile_ticket_payload,
)
from koru.autonomy.cycle_planning import _planning_ticket_row as _planning_ticket_row
from koru.autonomy.cycle_planning import (
    _recent_verdicts_for_planning as _recent_verdicts_for_planning,
)
from koru.autonomy.cycle_planning import (
    _run_phase4_advisory_hooks as _run_phase4_advisory_hooks,
)
from koru.autonomy.cycle_planning import (
    _run_phase4_strategy_tuning_advice as _run_phase4_strategy_tuning_advice,
)
from koru.autonomy.cycle_planning import (
    _run_phase4_ticket_priority_advice as _run_phase4_ticket_priority_advice,
)
from koru.autonomy.cycle_queue_scan import _build_queue_command as _build_queue_command
from koru.autonomy.cycle_queue_scan import (
    _emit_queue_iteration_event as _emit_queue_iteration_event,
)
from koru.autonomy.cycle_queue_scan import (
    _ensure_standardized_discovery_follow_up as _ensure_standardized_discovery_follow_up,
)
from koru.autonomy.cycle_queue_scan import _handle_post_run_verify as _handle_post_run_verify
from koru.autonomy.cycle_queue_scan import _handle_queue_loop_phase as _handle_queue_loop_phase
from koru.autonomy.cycle_queue_scan import _handle_scan_after_idle as _handle_scan_after_idle
from koru.autonomy.cycle_queue_scan import _handle_scan_phase as _handle_scan_phase
from koru.autonomy.cycle_queue_scan import (
    _run_code2llm_discovery_after_idle as _run_code2llm_discovery_after_idle,
)
from koru.autonomy.cycle_queue_scan import _run_queue_loop as _run_queue_loop
from koru.autonomy.cycle_queue_scan import _update_stagnation_state as _update_stagnation_state
from koru.autonomy.cycle_trace import (
    decision_next_step_hint as _decision_next_step_hint_impl,
)
from koru.autonomy.cycle_trace import (
    record_decision_trace as _record_decision_trace_impl,
)
from koru.autonomy.decision_trace import load_recent_decisions  # noqa: F401
from koru.autonomy.env import plugin_required_for_ide as _plugin_required_for_ide
from koru.autonomy.operator.operator_wup import WupHealthResult
from koru.autonomy.operator.operator_wup import _read_wup_health as _read_wup_health_impl  # noqa: F401
from koru.autonomy.phases import queue_phase as _queue_phase
from koru.autonomy.phases.contexts import (
    CyclePhaseContext,
    DrivePhaseConfig,
    DrivePhaseInputs,
    PhaseCallbacks,
    PreDrivePhaseResult,
    QueueScanPhaseConfig,
)
from koru.autonomy.phases.drive_phase import (
    run_drive_phase as _run_drive_phase,
)
from koru.autonomy.phases.drive_phase import (
    run_post_drive_phase as _run_post_drive_phase,
)
from koru.autonomy.phases.verify_phase import (
    handle_post_run_verify_ide as _handle_post_run_verify_ide,
)
from koru.autonomy.planning_llm import (
    prioritize_tickets as _llm_prioritize_tickets,  # noqa: F401
)
from koru.autonomy.planning_llm import (
    propose_strategy_tuning as _llm_propose_strategy_tuning,  # noqa: F401
)
from koru.autonomy.post_run_verify import (
    verify_completed_tickets,  # noqa: F401
)
from koru.autonomy.state import AutoloopState
from koru.autonomy_strategy.config import load_autonomy_strategy  # noqa: F401
from koru.env_flags import env_truthy as _env_truthy  # noqa: F401
from koru.environment_profile import environment_profile_payload  # noqa: F401
from koru.queue import QueueLoopResult, run_planfile_queue_loop  # noqa: F401
from koru.queue import default_human_prompt as _default_human_prompt  # noqa: F401
from koru.queue import run_api_request as _run_api_request  # noqa: F401
from koru.queue import run_llm_request as _run_llm_request  # noqa: F401
from koru.queue import run_process as _run_process  # noqa: F401
from koru.queue import run_shell_command as _run_shell_command  # noqa: F401
from koru.queue.ticket import planfile_command  # noqa: F401
from koru.scan import ScanResult, run_scan  # noqa: F401
from koru.stdio_events import write_stdio_event
from koru.tasks import create_nl_task  # noqa: F401

_LEGACY_AUTONOMOUS_CYCLE_EXPORTS = (
    detect_terminal_host_ide_id,
    _plugin_required_for_ide,
    _autopilot_redrive_cooldown_seconds,
    _skip_due_to_recent_chat_activity,
    _extract_needs_input_question,
    _reply_chat_input_busy,
    _resolve_autopilot_drive_decision,
    _log_autopilot_result,
)


def _stdio_info(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def _emit_stdio_cycle_event(
    event_type: str,
    payload: dict,
    *,
    command: str | None = None,
    stdio_format: str,
    correlation_id: str,
) -> None:
    if stdio_format == "jsonl":
        write_stdio_event(
            sys.stdout,
            event_type=event_type,
            correlation_id=correlation_id,
            payload=payload,
            command=command,
        )


def _cycle_human_progress(msg: str, *, stdio_format: str) -> None:
    from koru.activity_log import activity, activity_info

    if msg.startswith("+ "):
        activity("RUN", msg[2:], fmt=stdio_format)
    elif msg.startswith("  scan:"):
        activity("SCAN", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  queue:"):
        activity("QUEUE", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  autopilot:"):
        activity("CHAT", msg.strip(), fmt=stdio_format)
    elif msg.startswith("- autopilot skipped"):
        activity("CHAT", msg[2:].strip(), fmt=stdio_format)
    elif msg.startswith(("  decision:", "  drive_effect:")):
        activity("DECISION", msg.strip(), fmt=stdio_format)
    elif msg.startswith("  planfile snapshot:") or msg.startswith(
        ("  what koru auto", "  to give koru work", "  →")
    ):
        activity("KORUAUTONOMOUS", msg.strip(), fmt=stdio_format)
    elif stdio_format == "human":
        activity_info(msg, fmt=stdio_format)
    else:
        activity_info(msg, fmt=stdio_format)


# Queue statuses that mean "misconfiguration", not "waiting for work/human".
_QUEUE_ERROR_STATUSES = frozenset({"planfile_error", "unsupported_executor", "claim_failed"})


def _error_stagnation_threshold() -> int:
    raw = os.environ.get("KORU_ERROR_STAGNATION_DIAG_THRESHOLD", "").strip()
    try:
        return max(1, int(raw)) if raw else 3
    except ValueError:
        return 3


def _escalate_error_stagnation(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    _hp: callable,
    _emit: callable,
) -> None:
    """Diagnose instead of sleeping when the same error repeats cycle after cycle.

    2026-07-03 incident: ``planfile_error`` repeated for 17 cycles (over four
    hours of 900 s sleeps) without a single diagnostic run. When an error-class
    queue status persists ``threshold`` cycles, run the runtime readiness
    checks and surface every issue with its fix command; re-alert every 10
    cycles after that instead of every cycle to avoid log spam.
    """
    if queue_result.last_status not in _QUEUE_ERROR_STATUSES:
        return
    threshold = _error_stagnation_threshold()
    streak = state.stagnation_streak
    if streak < threshold or (streak > threshold and (streak - threshold) % 10 != 0):
        return
    _hp(
        f"  stagnation: {queue_result.last_status} repeated {streak + 1} cycles — "
        "running runtime diagnostics",
    )
    if queue_result.last_message:
        _hp(f"  stagnation: last error: {queue_result.last_message}")
    try:
        from koru.autonomous_readiness import check_runtime_consistency

        readiness = check_runtime_consistency(project)
        issues = list(readiness.issues)
    except Exception as exc:  # noqa: BLE001 — diagnostics must never kill the loop
        _hp(f"  stagnation: readiness diagnostics failed: {exc}")
        issues = []
    for issue in issues:
        _hp(f"  stagnation: [{issue.severity.upper()}] {issue.code}: {issue.message}")
        if issue.fix_command:
            _hp(f"  stagnation: fix → {issue.fix_command}")
    if not issues:
        _hp(
            "  stagnation: runtime checks passed — the error is likely in "
            "project/planfile state; inspect the queue stderr above",
        )
    _emit(
        "ErrorStagnationEscalated",
        {
            "cycle": cycle,
            "status": queue_result.last_status,
            "streak": streak,
            "issues": [
                {"code": i.code, "severity": i.severity, "fix": i.fix_command}
                for i in issues
            ],
        },
    )


def _take_pre_drive_snapshot(
    project: Path,
    state: AutoloopState,
    wup_health: Any,
) -> None:
    """Compatibility wrapper; implementation lives in autonomous_cycle_post_drive."""
    _take_pre_drive_snapshot_impl(project, state, wup_health)


def _handle_post_drive_verification(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    drive_status: str,
    wup_health: Any,
    _hp: callable,
    _emit: callable,
) -> None:
    """Compatibility wrapper; implementation lives in autonomous_cycle_post_drive."""
    _handle_post_drive_verification_impl(
        project=project,
        state=state,
        cycle=cycle,
        queue_result=queue_result,
        drive_status=drive_status,
        wup_health=wup_health,
        _hp=_hp,
        _emit=_emit,
    )


def _record_decision_trace(
    *,
    project: Path,
    cycle: int,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    wup_health: WupHealthResult,
    drive_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
    stagnation_streak: int,
    _hp: callable,
) -> None:
    _record_decision_trace_impl(
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
        autopilot_status=drive_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        cycle_telemetry=cycle_telemetry,
        stagnation_streak=stagnation_streak,
        hp=_hp,
    )


def _decision_next_step_hint(
    *,
    queue_status: str,
    drive_status: str,
    cycle_telemetry: dict[str, Any],
) -> str:
    return _decision_next_step_hint_impl(
        queue_status=queue_status,
        autopilot_status=drive_status,
        cycle_telemetry=cycle_telemetry,
    )


def _emit_cycle_completion_events(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    wup_health: WupHealthResult,
    drive_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
    scan_after_idle_queue: bool,
    scan_after_idle_min_interval_seconds: float,
    autopilot_skip_drive_idle_streak: int,
    hp: callable,
    emit: callable,
) -> None:
    _emit_cycle_completion_events_impl(
        project=project,
        state=state,
        cycle=cycle,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
        autopilot_status=drive_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        cycle_telemetry=cycle_telemetry,
        scan_after_idle_queue=scan_after_idle_queue,
        scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
        autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
        hp=hp,
        emit=emit,
    )


def _cycle_callbacks(
    *,
    stdio_format: str,
    correlation_id: str,
) -> tuple[callable, callable]:
    def emit(event_type: str, payload: dict, command: str | None = None) -> None:
        _emit_stdio_cycle_event(
            event_type,
            payload,
            command=command,
            stdio_format=stdio_format,
            correlation_id=correlation_id,
        )

    def hp(msg: str) -> None:
        _cycle_human_progress(msg, stdio_format=stdio_format)

    return emit, hp


def _emit_pre_drive_control_route(
    *,
    autopilot_ide: str,
    plugin_connected: bool,
    cycle_telemetry: dict[str, Any],
    hp: callable,
    queue_status: str = "",
) -> None:
    """One line + telemetry: which control route gillm would pick, and why.

    Best-effort — older gillm without gillm.routing (<0.1.22) is skipped.
    """
    if queue_status.strip().lower() == "idle":
        cycle_telemetry["control_route"] = {
            "selected": None,
            "status": "skipped",
            "reason": "queue_idle",
        }
        return
    try:
        from koru.tillm_bridge import shell_drive_client_id

        shell_client = shell_drive_client_id(autopilot_ide)
    except Exception:
        shell_client = None
    if shell_client:
        # Shell clients (claude-code, codex, aider, …) never use IDE routes;
        # probing gillm here used to print a misleading "no viable control
        # route" even though the drive goes through tillm just fine.
        hp(
            f"- pre-drive: control route → tillm_shell (verified): "
            f"{shell_client} is driven headlessly via tillm, no IDE route needed"
        )
        cycle_telemetry["control_route"] = {
            "selected": "tillm_shell",
            "client": shell_client,
        }
        return
    try:
        from gillm.routing import route_for

        plan = route_for(autopilot_ide, plugin_connected=plugin_connected)
    except Exception:
        return
    selected = plan.selected
    if selected is not None:
        line = (
            f"- pre-drive: control route → {selected.solution_id} "
            f"({selected.confidence}): {selected.reason}"
        )
    else:
        blockers = "; ".join(
            f"{s.solution_id}: {s.reason}" for s in plan.solutions if not s.viable
        )
        line = f"- pre-drive: no viable control route — {blockers}"
    hp(line)
    cycle_telemetry["control_route"] = plan.to_dict()


def _apply_pre_drive_plugin_readiness(
    *,
    project: Path,
    state: AutoloopState,
    client: Any,
    autopilot_ide: str,
    socket_path: Path | None,
    queue_result: QueueLoopResult,
    cycle_telemetry: dict[str, Any],
    hp: callable,
) -> None:
    import os

    from koru.autonomous_readiness import (
        check_lane_terminal_socket_alignment,
        check_queue_runner_contention,
        format_readiness_lines,
        warn_pre_drive_queue_without_plugin,
    )
    from koru.autonomy.cycle.cycle_drive_retry import _client_has_usable_plugin

    lane_instance = (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip() or None
    for line in format_readiness_lines(
        check_lane_terminal_socket_alignment(
            autopilot_ide=autopilot_ide,
            lane_instance=lane_instance,
            socket_path=socket_path,
        ),
        prefix="- pre-drive",
    ):
        hp(line)
        cycle_telemetry.setdefault("autopilot_pre_drive_readiness_lines", []).append(line)

    for line in format_readiness_lines(
        check_queue_runner_contention(project),
        prefix="- pre-drive",
    ):
        hp(line)

    plugin_required = _plugin_required_for_ide(autopilot_ide)
    if not plugin_required or client is None:
        state.autopilot_plugin_ready = True
        _emit_pre_drive_control_route(
            autopilot_ide=autopilot_ide,
            plugin_connected=False,
            cycle_telemetry=cycle_telemetry,
            hp=hp,
            queue_status=queue_result.last_status,
        )
        return
    plugin_ok, plugin_reason = _client_has_usable_plugin(client, autopilot_ide)
    state.autopilot_plugin_ready = plugin_ok
    cycle_telemetry["autopilot_plugin_ready"] = plugin_ok
    _emit_pre_drive_control_route(
        autopilot_ide=autopilot_ide,
        plugin_connected=bool(plugin_ok),
        cycle_telemetry=cycle_telemetry,
        hp=hp,
        queue_status=queue_result.last_status,
    )
    if plugin_reason:
        cycle_telemetry["autopilot_plugin_ready_reason"] = plugin_reason
    warning = warn_pre_drive_queue_without_plugin(
        queue_result.last_status,
        plugin_required=plugin_required,
        plugin_ok=plugin_ok,
        plugin_reason=plugin_reason,
    )
    if warning:
        hp(f"- pre-drive readiness: {warning}")
        cycle_telemetry["autopilot_pre_drive_plugin_warning"] = warning


def _run_pre_drive_cycle_phases(
    context: CyclePhaseContext,
    config: QueueScanPhaseConfig,
    *,
    cycle_telemetry: dict[str, Any],
) -> PreDrivePhaseResult:
    project = context.project
    state = context.state
    cycle = context.cycle
    hp = context.callbacks.hp
    emit = context.callbacks.emit
    emit("CycleStarted", {"cycle": cycle, "project": str(project.resolve())})
    _queue_phase.handle_queue_hygiene(project, cycle, hp, emit)
    verify_config = _handle_post_run_verify_ide(project, state, cycle, hp, emit)
    scan_result = _handle_scan_phase(
        project,
        state,
        cycle,
        config.enable_scan,
        config.include_semcod_artifacts,
        config.scan_skip_if_clean,
        config.scan_skip_after,
        config.topology_integration,
        hp,
        emit,
    )
    queue_result, verify_config = _handle_queue_loop_phase(
        project,
        state,
        cycle,
        config.actor,
        config.queue_name,
        config.max_iterations,
        config.topology_integration,
        verify_config,
        hp,
        emit,
    )
    idle_scan_result = _handle_scan_after_idle(
        project,
        state,
        cycle,
        queue_result,
        config.scan_after_idle_queue,
        config.include_semcod_artifacts,
        config.scan_after_idle_min_interval_seconds,
        config.topology_integration,
        cycle_telemetry,
        hp,
        emit,
    )
    if idle_scan_result is not None:
        scan_result = idle_scan_result
    _update_stagnation_state(state, queue_result)
    _escalate_error_stagnation(project, state, cycle, queue_result, hp, emit)
    diag_result, wup_health = _handle_diagnostics(
        project,
        state,
        cycle,
        queue_result,
        config.idle_diagnostics,
        config.diagnostic_tickets,
        config.diagnostic_ticket_queue,
        config.diagnostic_ticket_priority,
        config.diagnostic_state_dir,
        config.wup_watch_enabled,
        config.wup_diagnostic_tickets,
        config.wup_ticket_queue,
        config.topology_integration,
        hp,
        emit,
    )
    return PreDrivePhaseResult(
        scan_result=scan_result,
        queue_result=queue_result,
        diag_result=diag_result,
        wup_health=wup_health,
    )


def _stop_on_strict_diagnostics_failure(
    *,
    strict_diagnostics: bool,
    diag_result: DiagnosticResult,
    cycle: int,
    stdio_format: str,
    emit: callable,
) -> None:
    if not (strict_diagnostics and diag_result.status == "failed"):
        return
    emit("AutonomousStopped", {"reason": "strict_diagnostics_failure", "cycle": cycle})
    _stdio_info(
        "koru autonomous: strict diagnostics enabled -> stopping on diagnostics failure",
        fmt=stdio_format,
    )
    raise SystemExit(2)


def _run_drive_and_finalize(
    context: CyclePhaseContext,
    config: DrivePhaseConfig,
    inputs: DrivePhaseInputs,
) -> tuple[str, QueueLoopResult]:
    # late-bound through the compat facade so legacy-path monkeypatches
    # (koru.autonomous_cycle._run_drive_phase) keep working
    from koru import autonomous_cycle as _facade_mod

    run_drive_phase_fn = getattr(_facade_mod, "_run_drive_phase", _run_drive_phase)
    drive_result = run_drive_phase_fn(
        context,
        config,
        inputs,
        take_pre_drive_snapshot=_take_pre_drive_snapshot,
        handle_autopilot_phase=_handle_autopilot_phase,
    )
    from dataclasses import replace

    from koru.autonomy.cycle.shell_reconciliation import reconcile_shell_cycle

    queue, status = reconcile_shell_cycle(
        context.project, context.state, inputs.queue_result, drive_result.status,
        inputs.cycle_telemetry,
    )
    inputs = replace(inputs, queue_result=queue)
    drive_result = replace(drive_result, status=status)
    run_post_drive_phase_fn = getattr(
        _facade_mod, "_run_post_drive_phase", _run_post_drive_phase
    )
    run_post_drive_phase_fn(
        context,
        config,
        inputs,
        drive_result,
        handle_post_drive_verification=_handle_post_drive_verification,
        run_advisory_hooks=_run_phase4_advisory_hooks,
        emit_cycle_completion_events=_emit_cycle_completion_events,
    )
    return drive_result.status, inputs.queue_result


def run_cycle(
    *,
    cycle: int,
    project: Path,
    actor: str,
    queue_name: str | None,
    enable_scan: bool,
    max_iterations: int,
    enable_autopilot: bool,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    include_semcod_artifacts: bool | None,
    client: Any,
    state: AutoloopState | None = None,
    idle_diagnostics: str = "off",
    diagnostic_tickets: bool = False,
    diagnostic_ticket_queue: str = "default",
    diagnostic_ticket_priority: str = "high",
    diagnostic_state_dir: Path | None = None,
    wup_watch_enabled: bool = False,
    wup_diagnostic_tickets: bool = True,
    wup_ticket_queue: str = "default",
    strict_diagnostics: bool = False,
    autopilot_action: str = "drive",
    autopilot_on_idle_only: bool = False,
    autopilot_skip_on_diagnostics_fail: bool = True,
    autopilot_skip_drive_idle_streak: int = 0,
    autopilot_skip_statuses: str = "waiting_input",
    scan_skip_if_clean: bool = False,
    scan_skip_after: int = 1,
    scan_after_idle_queue: bool = False,
    scan_after_idle_min_interval_seconds: float = 0.0,
    topology_integration: bool = True,
    stdio_format: str = "human",
    correlation_id: str = "",
) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    state = state or AutoloopState()
    cycle_telemetry = _initialize_cycle_telemetry()
    _attach_environment_profile(project, cycle_telemetry, autopilot_ide=autopilot_ide)
    _heal_stale_socket()
    _emit, _hp = _cycle_callbacks(
        stdio_format=stdio_format,
        correlation_id=correlation_id,
    )
    phase_context = CyclePhaseContext(
        project=project,
        state=state,
        cycle=cycle,
        callbacks=PhaseCallbacks(hp=_hp, emit=_emit),
    )

    _handle_autopilot_events(state, _hp, autopilot_ide=autopilot_ide)
    pre_drive_result = _run_pre_drive_cycle_phases(
        phase_context,
        QueueScanPhaseConfig(
            actor=actor,
            queue_name=queue_name,
            enable_scan=enable_scan,
            max_iterations=max_iterations,
            include_semcod_artifacts=include_semcod_artifacts,
            idle_diagnostics=idle_diagnostics,
            diagnostic_tickets=diagnostic_tickets,
            diagnostic_ticket_queue=diagnostic_ticket_queue,
            diagnostic_ticket_priority=diagnostic_ticket_priority,
            diagnostic_state_dir=diagnostic_state_dir,
            wup_watch_enabled=wup_watch_enabled,
            wup_diagnostic_tickets=wup_diagnostic_tickets,
            wup_ticket_queue=wup_ticket_queue,
            scan_skip_if_clean=scan_skip_if_clean,
            scan_skip_after=scan_skip_after,
            scan_after_idle_queue=scan_after_idle_queue,
            scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
            topology_integration=topology_integration,
        ),
        cycle_telemetry=cycle_telemetry,
    )
    scan_result = pre_drive_result.scan_result
    queue_result = pre_drive_result.queue_result
    diag_result = pre_drive_result.diag_result
    wup_health = pre_drive_result.wup_health

    _stop_on_strict_diagnostics_failure(
        strict_diagnostics=strict_diagnostics,
        diag_result=diag_result,
        cycle=cycle,
        stdio_format=stdio_format,
        emit=_emit,
    )
    _apply_pre_drive_plugin_readiness(
        project=project,
        state=state,
        client=client,
        autopilot_ide=autopilot_ide,
        socket_path=_cycle_socket_path(client),
        queue_result=queue_result,
        cycle_telemetry=cycle_telemetry,
        hp=_hp,
    )

    drive_status, queue_result = _run_drive_and_finalize(
        phase_context,
        DrivePhaseConfig(
            queue_name=queue_name,
            enable_autopilot=enable_autopilot,
            client=client,
            autopilot_ide=autopilot_ide,
            drive_prompt=drive_prompt,
            submit=submit,
            autopilot_action=autopilot_action,
            autopilot_on_idle_only=autopilot_on_idle_only,
            autopilot_skip_on_diagnostics_fail=autopilot_skip_on_diagnostics_fail,
            autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
            autopilot_skip_statuses=autopilot_skip_statuses,
            topology_integration=topology_integration,
            scan_after_idle_queue=scan_after_idle_queue,
            scan_after_idle_min_interval_seconds=scan_after_idle_min_interval_seconds,
        ),
        DrivePhaseInputs(
            queue_result=queue_result,
            diag_result=diag_result,
            wup_health=wup_health,
            cycle_telemetry=cycle_telemetry,
        ),
    )

    return scan_result, queue_result, drive_status, diag_result


__all__ = ["AutoloopState", "DiagnosticResult", "run_cycle"]
