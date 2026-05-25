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
from koru.autonomy.env import (
    autopilot_terminal_conflict_reason as _autopilot_terminal_conflict_reason,
)
from koru.autonomy.env import (
    plugin_required_for_ide as _plugin_required_for_ide,
)
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult


def _drive_result_autopilot_status(
    *,
    queue_result: QueueLoopResult,
    reply: dict[str, Any],
    ok: bool,
    decision_kind: str | None,
    cycle_telemetry: dict[str, Any],
) -> str:
    if decision_kind == "idle_no_ticket":
        cycle_telemetry["autopilot_skipped_idle_no_ticket"] = True
        return "skipped(idle_no_ticket)"
    if decision_kind == "waiting_ticket_closed":
        waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
        cycle_telemetry["autopilot_skipped_waiting_ticket_closed"] = True
        cycle_telemetry["autopilot_skipped_waiting_ticket_closed_ticket"] = waiting_ticket
        return "skipped(waiting_ticket_closed)"
    if ok:
        return "ok"
    if _reply_requires_manual_chat_focus(reply):
        cycle_telemetry["autopilot_skipped_manual_focus"] = True
        return "skipped(manual_focus)"
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
    if plugin_status := _plugin_gate_status(client, autopilot_ide, cycle_telemetry, _hp):
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
        cycle_telemetry,
        _hp,
    )


def _plugin_gate_status(
    client: Any,
    autopilot_ide: str,
    cycle_telemetry: dict[str, Any],
    _hp: Callable[..., Any],
) -> str | None:
    if not _plugin_required_for_ide(autopilot_ide):
        return None
    plugin_ok, plugin_reason = _client_has_usable_plugin(client, autopilot_ide)
    if plugin_ok:
        return None
    blocker = plugin_skip_code(plugin_reason)
    _hp(f"- autopilot skipped ({blocker}: {plugin_reason})")
    _hp(
        "  → VSIX plugin is not connected to the daemon socket. "
        "In the IDE: Command Palette → `koru: Connect autopilot daemon` "
        "(status bar should show koru: on). If you just installed or "
        "upgraded the VSIX, run `Developer: Reload Window` first, then "
        "connect again. Check: `koru autopilot status --explain`.",
    )
    cycle_telemetry["autopilot_skipped_plugin_missing"] = True
    cycle_telemetry["autopilot_skipped_plugin_blocker"] = blocker
    cycle_telemetry["autopilot_skipped_plugin_missing_reason"] = plugin_reason
    return f"skipped({blocker})"


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
    _hp(f"- autopilot skipped (ide_mismatch: {conflict_reason})")
    cycle_telemetry["autopilot_skipped_ide_mismatch"] = True
    return "skipped(ide_mismatch)"


def _drive_autopilot_once(
    project: Path,
    state: AutoloopState,
    queue_result: QueueLoopResult,
    client: Any,
    autopilot_ide: str,
    drive_prompt: str,
    submit: bool,
    autopilot_action: str,
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
    if ok:
        state.last_message_sent_ts = time.time()
        state.last_message_sent_ide = autopilot_ide
        state.last_driven_ticket_id = _queue_loop_waiting_ticket_label(queue_result)
    state.last_autopilot_status = autopilot_status
    _update_autopilot_state(
        state, ok, decision_kind, autopilot_drive_kind, reply.get("prompt", "")
    )
    _log_autopilot_result(ok, queue_result, autopilot_ide, decision_kind, reply, _hp)
    return autopilot_status, autopilot_backend, autopilot_drive_kind
