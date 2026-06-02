import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import DiagnosticResult, _queue_loop_waiting_ticket_label
from koru.autonomous_cycle_drive_retry import (
    _client_has_usable_plugin,
    _execute_autopilot_drive,
    _log_autopilot_result,
    _reply_requires_manual_chat_focus,
    _update_autopilot_state,
)
from koru.autonomous_cycle_skip_conditions import _check_autopilot_skip_conditions
from koru.autonomous_plugin import plugin_skip_code
from koru.autonomous_plugin_runtime import plugin_reason_requires_reload
from koru.autonomy.env import (
    autopilot_terminal_conflict_reason as _autopilot_terminal_conflict_reason,
)
from koru.autonomy.env import (
    plugin_required_for_ide as _plugin_required_for_ide,
)
from koru.autonomy.policy_decision import AutopilotPolicyDecision
from koru.autonomy.state import AutoloopState
from koru.observability_events import (
    emit_blocker,
    emit_decision,
    emit_failure,
    emit_intent,
    emit_next,
)
from koru.observability_writer import emit_terminal_observability_path
from koru.queue import QueueLoopResult


_PLUGIN_GATE_RECOVERY_COOLDOWN_SECONDS = 60.0
_PLUGIN_GATE_RECOVERY_LAST_TS: dict[tuple[str, str, str], float] = {}


def _drive_result_autopilot_status(
    *,
    queue_result: QueueLoopResult,
    reply: dict[str, Any],
    ok: bool,
    decision_kind: str | None,
    cycle_telemetry: dict[str, Any],
) -> str:
    normalized_decision_kind = (decision_kind or "").strip()
    if normalized_decision_kind == "skipped(idle_no_ticket)":
        normalized_decision_kind = "idle_no_ticket"
    elif normalized_decision_kind == "skipped(waiting_ticket_closed)":
        normalized_decision_kind = "waiting_ticket_closed"
    if normalized_decision_kind == "idle_no_ticket":
        cycle_telemetry["autopilot_skipped_idle_no_ticket"] = True
        return "skipped(idle_no_ticket)"
    if normalized_decision_kind == "waiting_ticket_closed":
        waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
        cycle_telemetry["autopilot_skipped_waiting_ticket_closed"] = True
        cycle_telemetry["autopilot_skipped_waiting_ticket_closed_ticket"] = waiting_ticket
        return "skipped(waiting_ticket_closed)"
    if ok:
        return "ok"
    if _reply_requires_manual_chat_focus(reply):
        cycle_telemetry["autopilot_skipped_manual_focus"] = True
        return "skipped(manual_focus)"
    verification = str(reply.get("verification") or "").strip().lower()
    if verification in {"submit_unverified", "submit_failed"}:
        cycle_telemetry["autopilot_submit_unverified"] = True
        cycle_telemetry["autopilot_submit_unverified_reason"] = (
            reply.get("submit_failure_reason")
            or reply.get("reason")
            or reply.get("message")
            or verification
        )
        return f"failed({verification})"
    return "failed"


def _handle_autopilot_phase(
    project: Path,
    state: AutoloopState,
    cycle: int,
    queue_result: QueueLoopResult,
    enable_autopilot: bool,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    autopilot_on_idle_only: bool,
    autopilot_skip_on_diagnostics_fail: bool,
    autopilot_skip_drive_idle_streak: int,
    autopilot_skip_statuses: str,
    diag_result: DiagnosticResult,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
    _emit: Callable[..., Any],
) -> tuple[str, str | None, str | None]:
    autopilot_status = "skipped"
    autopilot_backend: str | None = None
    autopilot_drive_kind: str | None = None

    if not enable_autopilot or client is None:
        return autopilot_status, autopilot_backend, autopilot_drive_kind
    if plugin_status := _plugin_gate_status(
        project,
        cycle,
        queue_result,
        client,
        autopilot_ide,
        drive_prompt,
        submit,
        cycle_telemetry,
        _hp,
    ):
        return plugin_status, None, None
    if conflict_status := _terminal_conflict_status(autopilot_ide, cycle_telemetry, _hp):
        return conflict_status, None, None
    should_skip, skip_reason = _check_autopilot_skip_conditions(
        project,
        queue_result,
        state,
        autopilot_action,
        autopilot_on_idle_only,
        autopilot_skip_on_diagnostics_fail,
        autopilot_skip_drive_idle_streak,
        autopilot_skip_statuses,
        diag_result,
        topology_integration,
        cycle_telemetry,
        _hp,
    )
    if should_skip:
        return skip_reason, None, None
    return _drive_autopilot_once(
        project,
        state,
        queue_result,
        client,
        autopilot_ide,
        drive_prompt,
        submit,
        autopilot_action,
        cycle,
        cycle_telemetry,
        _hp,
    )


def _plugin_gate_status(
    project: Path,
    cycle: int,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
) -> str | None:
    if not _plugin_required_for_ide(autopilot_ide):
        return None
    plugin_ok, plugin_reason = _client_has_usable_plugin(client, autopilot_ide)
    if plugin_ok:
        return None
    blocker = plugin_skip_code(plugin_reason)
    decision = AutopilotPolicyDecision.skip(
        blocker,
        because=plugin_reason,
        action_hint="reload IDE window and reconnect plugin",
    )
    _hp(f"- autopilot skipped ({blocker}: {plugin_reason})")
    _hp(
        "  → VSIX plugin is not connected to the daemon socket. "
        "In the IDE: Command Palette → `Developer: Reload Window`, then "
        "`koru: Connect autopilot daemon` (status bar should show koru: on). "
        "Check: `koru autopilot status --explain`.",
    )
    cycle_telemetry["autopilot_skipped_plugin_missing"] = True
    cycle_telemetry["autopilot_skipped_plugin_blocker"] = blocker
    cycle_telemetry["autopilot_skipped_plugin_missing_reason"] = plugin_reason
    if blocker == "plugin_version_mismatch" and plugin_reason_requires_reload(plugin_reason):
        recovered = _attempt_plugin_gate_recovery(
            project,
            client,
            autopilot_ide,
            plugin_reason,
            _hp,
        )
        cycle_telemetry["autopilot_plugin_recovery_attempted"] = recovered
    _emit_autopilot_preflight_skip(
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        autopilot_ide=autopilot_ide,
        drive_prompt=drive_prompt,
        submit=submit,
        blocker=blocker,
        reason=plugin_reason,
        next_action="reload_reconnect_plugin",
    )
    return decision.status


def _attempt_plugin_gate_recovery(
    project: Path,
    client: Any,
    autopilot_ide: str,
    plugin_reason: str,
    _hp: Callable[..., Any],
) -> bool:
    key = _plugin_gate_recovery_key(project, autopilot_ide, plugin_reason)
    now = time.monotonic()
    last = _PLUGIN_GATE_RECOVERY_LAST_TS.get(key)
    if last is not None and now - last < _PLUGIN_GATE_RECOVERY_COOLDOWN_SECONDS:
        remaining = _PLUGIN_GATE_RECOVERY_COOLDOWN_SECONDS - (now - last)
        _hp(
            "  → autopilot recovery: reload already attempted; "
            f"retry in {remaining:.0f}s",
        )
        return False
    _PLUGIN_GATE_RECOVERY_LAST_TS[key] = now

    from koru.autonomous_plugin_wait import (
        _restore_reuse_window_reload,
        _temporary_reuse_window_reload_if_same_workspace,
    )
    from koru.ide_adapters.ide_reload import try_reload_vscode_family_ide

    snapshot = _temporary_reuse_window_reload_if_same_workspace(
        client,
        autopilot_ide,
        project,
        plugin_reason,
    )
    try:
        outcome = try_reload_vscode_family_ide(autopilot_ide, project=project)
    finally:
        _restore_reuse_window_reload(snapshot)

    if outcome.attempted and outcome.ok:
        _hp(
            "  → autopilot recovery: requested IDE reload/reconnect; "
            "the next cycle will re-check the plugin session.",
        )
        return True
    detail = outcome.detail or outcome.method or "reload was not available"
    _hp(f"  → autopilot recovery: automatic reload failed ({detail})")
    return True


def _plugin_gate_recovery_key(
    project: Path,
    autopilot_ide: str,
    plugin_reason: str,
) -> tuple[str, str, str]:
    try:
        project_key = str(project.resolve())
    except OSError:
        project_key = str(project)
    return (
        project_key,
        autopilot_ide.strip().lower(),
        plugin_reason.strip().lower()[:240],
    )


def _terminal_conflict_status(
    autopilot_ide: str,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
) -> str | None:
    conflict_reason = _autopilot_terminal_conflict_reason(
        autopilot_ide,
        plugin_connected=_plugin_required_for_ide(autopilot_ide),
    )
    if not conflict_reason:
        return None
    decision = AutopilotPolicyDecision.skip(
        "ide_mismatch",
        because=conflict_reason,
        action_hint="align autopilot lane with active IDE",
    )
    _hp(f"- autopilot skipped (ide_mismatch: {conflict_reason})")
    cycle_telemetry["autopilot_skipped_ide_mismatch"] = True
    return decision.status


def _drive_autopilot_once(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
    cycle: int,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
) -> tuple[str, str | None, str | None]:
    reply, ok, decision_kind, idle_prompt_kind = _execute_autopilot_drive(
        project,
        state,
        queue_result,
        client,
        autopilot_ide,
        drive_prompt,
        submit,
        autopilot_action,
        _hp,
    )
    autopilot_drive_kind = idle_prompt_kind or decision_kind
    autopilot_status = _drive_result_autopilot_status(
        queue_result=queue_result,
        reply=reply,
        ok=ok,
        decision_kind=decision_kind,
        cycle_telemetry=cycle_telemetry,
    )
    autopilot_backend = str(reply.get("backend")) if reply.get("backend") is not None else None
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    if ok:
        state.last_message_sent_ts = time.time()
        state.last_message_sent_ide = autopilot_ide
        state.last_driven_ticket_id = waiting_ticket
        if autopilot_backend:
            state.last_driven_backend = autopilot_backend
    elif autopilot_status.startswith("failed(submit_") and reply.get("delivered") is True:
        state.last_driven_ticket_id = waiting_ticket
    state.last_autopilot_status = autopilot_status
    _update_autopilot_state(
        state, ok, decision_kind, autopilot_drive_kind, reply.get("prompt", "")
    )
    _log_autopilot_result(ok, queue_result, autopilot_ide, decision_kind, reply, _hp)
    _emit_autopilot_observability_outcome(
        project=project,
        cycle=cycle,
        queue_result=queue_result,
        reply=reply,
        ok=ok,
        autopilot_status=autopilot_status,
        decision_kind=decision_kind,
        autopilot_ide=autopilot_ide,
    )
    return autopilot_status, autopilot_backend, autopilot_drive_kind


def _emit_autopilot_preflight_skip(
    *,
    project: Path,
    cycle: int,
    queue_result: QueueLoopResult,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    blocker: str,
    reason: str,
    next_action: str,
) -> None:
    corr = f"auto-{cycle}-preflight"
    ticket = _queue_loop_waiting_ticket_label(queue_result)
    ticket_id = None if ticket == "-" else ticket
    events = [
        emit_intent(
            project,
            corr=corr,
            cycle=cycle,
            ticket=ticket_id,
            goal="deliver_prompt_to_ide_chat",
            target=autopilot_ide,
            ide=autopilot_ide,
            submit=submit,
            require_plugin=_plugin_required_for_ide(autopilot_ide),
            chars=len(drive_prompt or ""),
        ),
        emit_decision(
            project,
            corr=corr,
            cycle=cycle,
            ticket=ticket_id,
            name="preflight_plugin_gate",
            chosen="skip",
            because=blocker,
            ide=autopilot_ide,
            reason=reason,
        ),
        emit_failure(
            project,
            corr=corr,
            cycle=cycle,
            ticket=ticket_id,
            code=blocker,
            message=reason,
            ide=autopilot_ide,
            verification="plugin_connected",
        ),
        emit_blocker(
            project,
            corr=corr,
            cycle=cycle,
            ticket=ticket_id,
            name=blocker,
            because=reason,
            ide=autopilot_ide,
            status=f"skipped({blocker})",
        ),
        emit_next(
            project,
            corr=corr,
            cycle=cycle,
            ticket=ticket_id,
            action=next_action,
            ide=autopilot_ide,
            decision_kind="preflight_plugin_gate",
        ),
    ]
    emit_terminal_observability_path(events)


def _emit_autopilot_observability_outcome(
    *,
    project: Path,
    cycle: Any,
    queue_result: QueueLoopResult,
    reply: dict[str, Any],
    ok: bool,
    autopilot_status: str,
    decision_kind: str,
    autopilot_ide: str,
) -> None:
    if ok:
        return
    if not (autopilot_status.startswith("failed") or autopilot_status.startswith("skipped(")):
        return
    corr = str(reply.get("id") or "cli-drive")
    ticket = _queue_loop_waiting_ticket_label(queue_result)
    cycle_number = cycle if isinstance(cycle, int) else None
    blocker = "drive_failed"
    next_action = "retry_next_cycle"
    verification = str(reply.get("verification") or "").strip().lower()
    if verification in {"submit_unverified", "submit_failed"}:
        blocker = "manual_send_required"
        next_action = "validate_submit_or_mark_ticket_input"
    if autopilot_status == "skipped(manual_focus)":
        blocker = "manual_focus_required"
        next_action = "focus_chat_or_open_interfaces"
    elif decision_kind in {
        "idle_no_ticket",
        "waiting_ticket_closed",
        "skipped(idle_no_ticket)",
        "skipped(waiting_ticket_closed)",
    }:
        return
    emit_blocker(
        project,
        corr=corr,
        cycle=cycle_number,
        ticket=None if ticket == "-" else ticket,
        name=blocker,
        because=str(reply.get("reason") or reply.get("message") or "autopilot_failed"),
        ide=autopilot_ide,
        status=autopilot_status,
    )
    emit_next(
        project,
        corr=corr,
        cycle=cycle_number,
        ticket=None if ticket == "-" else ticket,
        action=next_action,
        ide=autopilot_ide,
        decision_kind=decision_kind,
    )
