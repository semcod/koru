from pathlib import Path
from typing import Any

import yaml

from koru.autonomous_cycle_chat_activity import _skip_due_to_recent_chat_activity
from koru.autonomous_cycle_common import (
    DiagnosticResult,
    _queue_loop_waiting_ticket_label,
    _status_in_skip_list,
)
from koru.autonomy.prompts import DEFAULT_ESCALATION_THRESHOLD
from koru.autonomy.state import AutoloopState
from koru.queue import QueueLoopResult
from koru.topology import is_component_enabled, is_pipeline_enabled


def _is_topology_enabled(project: Path, key: str, *, fallback: bool, enabled: bool) -> bool:
    if not enabled:
        return fallback
    try:
        if key in {"idle-diagnostics", "autoloop:queue", "scan:on-change", "autopilot:drive"}:
            return is_pipeline_enabled(project, key)
        return is_component_enabled(project, key)
    except Exception:
        return fallback


def _waiting_ticket_has_label(
    project: Path,
    queue_result: QueueLoopResult,
    label: str,
) -> bool:
    ticket_id = _queue_loop_waiting_ticket_label(queue_result)
    if ticket_id == "-":
        ticket_id = getattr(queue_result, "last_ticket_id", None) or ""
    if not ticket_id:
        return False

    for sprint_path in (
        project / ".planfile" / "sprints" / "current.yaml",
        project / "planfile.yaml",
    ):
        if not sprint_path.is_file():
            continue
        try:
            data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
        except (OSError, yaml.YAMLError):
            continue
        tickets = data.get("tickets")
        if tickets is None and isinstance(data.get("sprint"), dict):
            tickets = data["sprint"].get("tickets")
        if not isinstance(tickets, dict):
            continue
        ticket = tickets.get(ticket_id)
        if not isinstance(ticket, dict):
            continue
        labels = ticket.get("labels") or []
        return label in {str(item) for item in labels}
    return False


def _check_autopilot_skip_conditions(
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    autopilot_action: str,
    autopilot_on_idle_only: bool,
    autopilot_skip_on_diagnostics_fail: bool,
    autopilot_skip_drive_idle_streak: int,
    autopilot_skip_statuses: str,
    diag_result: DiagnosticResult,
    topology_integration: bool,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> tuple[bool, str]:
    """Check if autopilot should be skipped and return (should_skip, skip_reason)."""
    if not _is_topology_enabled(
        project,
        "autopilot:drive",
        fallback=True,
        enabled=topology_integration,
    ):
        _hp("- autopilot skipped (autopilot:drive disabled in topology)")
        return True, "skipped(topology)"
    elif autopilot_action == "off":
        _hp("- autopilot action set to off, skipping")
        return True, "skipped(action_off)"
    elif autopilot_on_idle_only and queue_result.last_status != "idle":
        _hp("- autopilot skipped (idle_only)")
        return True, "skipped(idle_only)"
    elif autopilot_skip_on_diagnostics_fail and diag_result.status == "failed":
        _hp("- autopilot skipped (diagnostics_fail)")
        return True, "skipped(diagnostics_fail)"
    elif (
        autopilot_skip_drive_idle_streak > 0
        and queue_result.last_status == "idle"
        and state.stagnation_streak >= autopilot_skip_drive_idle_streak
    ):
        _hp(
            "- autopilot skipped "
            f"(idle_streak_{state.stagnation_streak}>={autopilot_skip_drive_idle_streak})",
        )
        state.telemetry_autopilot_idle_streak_skips += 1
        cycle_telemetry["autopilot_skipped_idle_streak"] = True
        return True, "skipped(idle_streak)"
    elif 0 < state.stagnation_streak < DEFAULT_ESCALATION_THRESHOLD and _status_in_skip_list(
        queue_result.last_status,
        autopilot_skip_statuses,
    ):
        if str(getattr(state, "last_autopilot_status", "") or "") == "failed":
            _hp(
                "- autopilot not skipped "
                f"(previous drive failed, streak={state.stagnation_streak})",
            )
            return False, ""
        if _waiting_ticket_has_label(project, queue_result, "llm-ready"):
            if _skip_due_to_recent_chat_activity(
                project=project,
                queue_result=queue_result,
                state=state,
                cycle_telemetry=cycle_telemetry,
                _hp=_hp,
            ):
                return True, "skipped(chat_activity)"
            _hp(
                "- autopilot not skipped "
                f"(waiting ticket is llm-ready, streak={state.stagnation_streak})",
            )
            return False, ""
        _hp(
            "- autopilot skipped "
            f"(stuck_{queue_result.last_status}_streak_{state.stagnation_streak})",
        )
        return True, f"skipped(stuck_{queue_result.last_status})"
    return False, ""
