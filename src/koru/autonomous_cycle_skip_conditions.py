import os
import re
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


def _auto_llm_ready_enabled() -> bool:
    raw = os.getenv("KORU_AUTOPILOT_AUTO_LLM_READY", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


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


def _waiting_ticket_path_and_ticket(
    project: Path,
    queue_result: QueueLoopResult,
) -> tuple[Path, dict[str, Any]] | None:
    ticket_id = _waiting_ticket_id(queue_result)
    if not ticket_id:
        return None
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
        return sprint_path, data
    return None


def _add_waiting_ticket_label(
    project: Path,
    queue_result: QueueLoopResult,
    label: str,
) -> bool:
    found = _waiting_ticket_path_and_ticket(project, queue_result)
    if found is None:
        return False
    sprint_path, data = found
    ticket_id = _waiting_ticket_id(queue_result)
    if _waiting_ticket_has_label(project, queue_result, label):
        return True
    try:
        text = sprint_path.read_text(encoding="utf-8")
    except OSError:
        return False
    updated = _add_label_to_ticket_yaml_text(text, ticket_id, label)
    if updated is None:
        return False
    try:
        sprint_path.write_text(updated, encoding="utf-8")
    except OSError:
        return False
    return True


def _add_label_to_ticket_yaml_text(text: str, ticket_id: str, label: str) -> str | None:
    """Text-preserving Planfile label insert for a single ticket block."""
    lines = text.splitlines(keepends=True)
    block = _ticket_yaml_block_bounds(lines, ticket_id)
    if block is None:
        return None
    start, end, ticket_indent = block
    item_indent = f"{ticket_indent}  "
    label_line_idx = _find_label_line_index(lines, start, end)
    if label_line_idx < 0:
        return _insert_missing_label_block(lines, start, item_indent, label)

    label_line = lines[label_line_idx]
    label_indent = label_line[: len(label_line) - len(label_line.lstrip())]
    stripped = label_line.strip()
    if "[" in stripped:
        return _append_inline_label(lines, label_line_idx, label_indent, label, text)
    return _append_block_label(lines, label_line_idx, end, label_indent, label, text)


def _ticket_yaml_block_bounds(
    lines: list[str],
    ticket_id: str,
) -> tuple[int, int, str] | None:
    start = -1
    ticket_indent = ""
    ticket_re = re.compile(rf"^(\s*){re.escape(ticket_id)}:\s*(?:#.*)?\n?$")
    for idx, line in enumerate(lines):
        match = ticket_re.match(line)
        if match:
            start = idx
            ticket_indent = match.group(1)
            break
    if start < 0:
        return None

    end = len(lines)
    next_ticket_re = re.compile(rf"^{re.escape(ticket_indent)}\S[^:]*:\s*(?:#.*)?\n?$")
    for idx in range(start + 1, len(lines)):
        if next_ticket_re.match(lines[idx]):
            end = idx
            break
    return start, end, ticket_indent


def _find_label_line_index(lines: list[str], start: int, end: int) -> int:
    label_line_idx = -1
    for idx in range(start + 1, end):
        if lines[idx].lstrip().startswith("labels:"):
            label_line_idx = idx
            break
    return label_line_idx


def _insert_missing_label_block(
    lines: list[str],
    start: int,
    item_indent: str,
    label: str,
) -> str:
    lines.insert(start + 1, f"{item_indent}labels:\n")
    lines.insert(start + 2, f"{item_indent}- {label}\n")
    return "".join(lines)


def _append_inline_label(
    lines: list[str],
    label_line_idx: int,
    label_indent: str,
    label: str,
    original_text: str,
) -> str:
    parsed = _parse_inline_label_line(lines[label_line_idx].strip())
    existing = [str(item) for item in parsed.get("labels", [])] if isinstance(parsed, dict) else []
    if label in existing:
        return original_text
    existing.append(label)
    replacement = [f"{label_indent}labels:\n"]
    replacement.extend(f"{label_indent}- {item}\n" for item in existing)
    lines[label_line_idx : label_line_idx + 1] = replacement
    return "".join(lines)


def _parse_inline_label_line(stripped_line: str) -> dict[str, Any]:
    try:
        parsed = yaml.safe_load(stripped_line) or {}
    except yaml.YAMLError:
        return {}
    return parsed if isinstance(parsed, dict) else {}


def _append_block_label(
    lines: list[str],
    label_line_idx: int,
    end: int,
    label_indent: str,
    label: str,
    original_text: str,
) -> str:
    insert_at, existing_items = _block_label_insert_at(lines, label_line_idx, end, label_indent)
    if label in existing_items:
        return original_text
    lines.insert(insert_at, f"{label_indent}- {label}\n")
    return "".join(lines)


def _block_label_insert_at(
    lines: list[str],
    label_line_idx: int,
    end: int,
    label_indent: str,
) -> tuple[int, set[str]]:
    insert_at = end
    existing_items: set[str] = set()
    item_re = re.compile(rf"^{re.escape(label_indent)}-\s*(.+?)\s*(?:#.*)?\n?$")
    for idx in range(label_line_idx + 1, end):
        line = lines[idx]
        if line.strip() == "":
            continue
        match = item_re.match(line)
        if not match:
            insert_at = idx
            break
        existing_items.add(match.group(1).strip().strip("'\""))
        insert_at = idx + 1
    return insert_at, existing_items


def _waiting_ticket_id(queue_result: QueueLoopResult) -> str:
    ticket_id = _queue_loop_waiting_ticket_label(queue_result)
    if ticket_id == "-":
        ticket_id = getattr(queue_result, "last_ticket_id", None) or ""
    return str(ticket_id or "")


def _autopromote_waiting_ticket_llm_ready(
    project: Path,
    queue_result: QueueLoopResult,
    *,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> bool:
    """Add ``llm-ready`` to the waiting ticket so autopilot can do the work.

    ``waiting_input`` is a safe default for human operators, but in autonomous
    mode it can strand runnable tickets until someone copies the suggested
    ``planfile bulk-update`` command. This promotion keeps the old guardrail
    opt-out-able while letting Koru unblock its own operator tickets.
    """
    if not _auto_llm_ready_enabled():
        return False
    ticket_id = _waiting_ticket_id(queue_result)
    if not ticket_id:
        return False
    if _waiting_ticket_has_label(project, queue_result, "llm-ready"):
        return True
    if not _add_waiting_ticket_label(project, queue_result, "llm-ready"):
        text = "ticket not found or sprint file is not writable"
        cycle_telemetry["autopilot_auto_llm_ready_failed"] = True
        cycle_telemetry["autopilot_auto_llm_ready_error"] = text
        _hp(f"- autopilot auto llm-ready failed ({ticket_id}: {text})")
        return False
    cycle_telemetry["autopilot_auto_llm_ready"] = True
    cycle_telemetry["autopilot_auto_llm_ready_ticket"] = ticket_id
    _hp(f"- autopilot auto llm-ready: added label to {ticket_id}")
    return True


def _diagnostics_fail_skip_result(
    *,
    enabled: bool,
    diag_result: DiagnosticResult,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> tuple[bool, str] | None:
    if not enabled or diag_result.status != "failed":
        return None
    _hp("- autopilot skipped (diagnostics_fail)")
    cycle_telemetry["autopilot_skipped_diagnostics_fail"] = True
    failed = list(getattr(diag_result, "failed", []) or [])
    if failed:
        cycle_telemetry["autopilot_skipped_diagnostics_failed_services"] = failed
    return True, "skipped(diagnostics_fail)"


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

    if autopilot_action == "off":
        _hp("- autopilot action set to off, skipping")
        return True, "skipped(action_off)"

    if autopilot_on_idle_only and queue_result.last_status != "idle":
        _hp("- autopilot skipped (idle_only)")
        return True, "skipped(idle_only)"

    diagnostics_skip = _diagnostics_fail_skip_result(
        enabled=autopilot_skip_on_diagnostics_fail,
        diag_result=diag_result,
        cycle_telemetry=cycle_telemetry,
        _hp=_hp,
    )
    if diagnostics_skip is not None:
        return diagnostics_skip

    manual_send_skip = _manual_send_required_skip_result(
        queue_result=queue_result,
        state=state,
        cycle_telemetry=cycle_telemetry,
        _hp=_hp,
    )
    if manual_send_skip is not None:
        return manual_send_skip

    if _should_skip_for_idle_streak(
        queue_result=queue_result,
        state=state,
        autopilot_skip_drive_idle_streak=autopilot_skip_drive_idle_streak,
    ):
        _hp(
            "- autopilot skipped "
            f"(idle_streak_{state.stagnation_streak}>={autopilot_skip_drive_idle_streak})",
        )
        state.telemetry_autopilot_idle_streak_skips += 1
        cycle_telemetry["autopilot_skipped_idle_streak"] = True
        return True, "skipped(idle_streak)"

    if _is_waiting_llm_ready_ticket(queue_result=queue_result, project=project):
        if _skip_due_to_recent_chat_activity(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            _hp=_hp,
        ):
            return True, "skipped(chat_activity)"

    if _is_stuck_status_skip_candidate(
        queue_result=queue_result,
        state=state,
        autopilot_skip_statuses=autopilot_skip_statuses,
    ):
        if _autopromote_waiting_ticket_llm_ready(
            project,
            queue_result,
            cycle_telemetry=cycle_telemetry,
            _hp=_hp,
        ):
            _hp(
                "- autopilot not skipped "
                f"(auto llm-ready, streak={state.stagnation_streak})",
            )
            return False, ""
        return _handle_stuck_status_skip_candidate(
            project=project,
            queue_result=queue_result,
            state=state,
            cycle_telemetry=cycle_telemetry,
            _hp=_hp,
        )

    return False, ""


def _should_skip_for_idle_streak(
    *,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    autopilot_skip_drive_idle_streak: int,
) -> bool:
    return (
        autopilot_skip_drive_idle_streak > 0
        and queue_result.last_status == "idle"
        and state.stagnation_streak >= autopilot_skip_drive_idle_streak
    )


def _is_stuck_status_skip_candidate(
    *,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    autopilot_skip_statuses: str,
) -> bool:
    return (
        0 < state.stagnation_streak < DEFAULT_ESCALATION_THRESHOLD
        and _status_in_skip_list(queue_result.last_status, autopilot_skip_statuses)
    )


def _is_waiting_llm_ready_ticket(*, queue_result: QueueLoopResult, project: Path) -> bool:
    return (
        queue_result.last_status == "waiting_input"
        and _waiting_ticket_has_label(project, queue_result, "llm-ready")
    )


def _previous_drive_needs_manual_send(state: AutoloopState) -> bool:
    return str(getattr(state, "last_autopilot_status", "") or "").startswith(
        "failed(submit_"
    )


def _manual_send_required_skip_result(
    *,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> tuple[bool, str] | None:
    if not _previous_drive_needs_manual_send(state):
        return None
    waiting_ticket = _waiting_ticket_id(queue_result)
    previous_ticket = str(getattr(state, "last_driven_ticket_id", "") or "")
    if not waiting_ticket or waiting_ticket != previous_ticket:
        cycle_telemetry["autopilot_submit_unverified_cleared_for_new_ticket"] = True
        cycle_telemetry["autopilot_submit_unverified_previous_ticket"] = previous_ticket
        cycle_telemetry["autopilot_submit_unverified_current_ticket"] = waiting_ticket
        state.last_autopilot_status = ""
        return None
    _hp("- autopilot skipped (manual_send_required after submit_unverified)")
    cycle_telemetry["autopilot_submit_unverified"] = True
    cycle_telemetry["autopilot_skipped_manual_send_required"] = True
    cycle_telemetry["autopilot_submit_unverified_reason"] = (
        "previous drive pasted text but submit was not verified; "
        "manual send or submit strategy fix required before redrive"
    )
    return True, "skipped(manual_send_required)"


def _handle_stuck_status_skip_candidate(
    *,
    project: Path,
    queue_result: QueueLoopResult,
    state: AutoloopState,
    cycle_telemetry: dict[str, Any],
    _hp: callable,
) -> tuple[bool, str]:
    if str(getattr(state, "last_autopilot_status", "") or "").startswith("failed"):
        _hp(
            "- autopilot not skipped "
            f"(previous drive failed, streak={state.stagnation_streak})",
        )
        return False, ""

    if _waiting_ticket_has_label(project, queue_result, "llm-ready"):
        _hp(
            "- autopilot not skipped "
            f"(waiting ticket is llm-ready, streak={state.stagnation_streak})",
        )
        return False, ""

    _hp(
        "- autopilot skipped "
        f"(stuck_{queue_result.last_status}_streak_{state.stagnation_streak})",
    )
    cycle_telemetry["autopilot_skipped_stuck_status"] = True
    cycle_telemetry["autopilot_skipped_stuck_status_queue"] = str(
        queue_result.last_status or ""
    )
    cycle_telemetry["autopilot_skipped_stuck_status_streak"] = int(
        state.stagnation_streak or 0
    )
    return True, f"skipped(stuck_{queue_result.last_status})"
