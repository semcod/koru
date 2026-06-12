from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.autonomous_cycle_common import DiagnosticResult, _queue_loop_waiting_ticket_label
from koru.autonomous_wup import WupHealthResult
from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.decision_trace import (
    append_decision_record,
    build_decision_record,
    human_skip_reason,
)
from koru.queue import QueueLoopResult

_TELEMETRY_NEXT_STEP_HINTS: tuple[tuple[str, str], ...] = (
    (
        "autopilot_skipped_plugin_missing",
        "wait for plugin reconnect (manual reload may be needed)",
    ),
    (
        "autopilot_skipped_ide_mismatch",
        "switch lane or set KORU_AUTOPILOT_INSTANCE for target IDE",
    ),
    ("autopilot_skipped_chat_activity", "wait for chat cooldown to expire"),
    ("autopilot_skipped_idle_no_ticket", "scan / reopen done ticket / `koru --ticket`"),
    ("autopilot_skipped_idle_streak", "let idle backoff drain before next drive"),
    ("autopilot_skipped_manual_focus", "operator must foreground the chat surface"),
    (
        "autopilot_skipped_stuck_status",
        "mark ticket llm-ready OR move it to input/done before next drive",
    ),
    (
        "autopilot_skipped_diagnostics_fail",
        (
            "fix failing WUP/diagnostics, OR mark the diag ticket done, "
            "OR rerun with --no-autopilot-skip-on-diagnostics-fail"
        ),
    ),
)


def _telemetry_next_step_hint(cycle_telemetry: dict[str, Any]) -> str | None:
    for key, hint in _TELEMETRY_NEXT_STEP_HINTS:
        if cycle_telemetry.get(key):
            return hint
    return None


def decision_next_step_hint(
    *,
    queue_status: str,
    autopilot_status: str,
    cycle_telemetry: dict[str, Any],
) -> str:
    """Compact ``next=`` token for the decision trace."""
    status = parse_autopilot_status(autopilot_status)
    if status.ok:
        return "wait for IDE response, then advance queue"
    if status.submit_unverified or cycle_telemetry.get("autopilot_submit_unverified"):
        return "manual send required; validate submit trace before any redrive"
    telemetry_hint = _telemetry_next_step_hint(cycle_telemetry)
    if telemetry_hint is not None:
        return telemetry_hint
    if status.failed:
        return "retry next cycle (cached winner discarded)"
    queue_status = (queue_status or "").lower()
    if queue_status == "waiting_input":
        return "keep waiting ticket scoped; rerun queue next cycle"
    if queue_status == "idle":
        return "run idle scan / intake strategy"
    return "rerun queue + diagnostics"


def record_decision_trace(
    *,
    project: Path,
    cycle: int,
    queue_result: QueueLoopResult,
    diag_result: DiagnosticResult,
    wup_health: WupHealthResult,
    autopilot_status: str,
    autopilot_ide: str,
    autopilot_backend: str | None,
    autopilot_drive_kind: str | None,
    cycle_telemetry: dict[str, Any],
    stagnation_streak: int,
    hp: Callable[[str], None],
) -> None:
    """Build + persist + log a structured ``DecisionRecord`` for this cycle."""
    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    next_step = decision_next_step_hint(
        queue_status=str(queue_result.last_status or ""),
        autopilot_status=autopilot_status,
        cycle_telemetry=cycle_telemetry,
    )
    record = build_decision_record(
        cycle=cycle,
        queue_status=str(queue_result.last_status or ""),
        waiting_ticket=waiting_ticket,
        stagnation_streak=stagnation_streak,
        autopilot_status=autopilot_status,
        autopilot_ide=autopilot_ide,
        autopilot_backend=autopilot_backend,
        autopilot_drive_kind=autopilot_drive_kind,
        diag_status=str(getattr(diag_result, "status", "") or ""),
        wup_status=str(getattr(wup_health, "status", "") or ""),
        cycle_telemetry=cycle_telemetry,
        next_step=next_step,
    )
    append_decision_record(project, record)
    hp(f"  decision: {record.compact_line()}")
    if record.skip_code not in ("ok",):
        reason = human_skip_reason(record.skip_code, fallback=record.skip_code)
        because = record.skip_because
        suffix = f" — {because}" if because else ""
        hp(f"  decision: because[{record.skip_code}] {reason}{suffix}")


__all__ = ["decision_next_step_hint", "record_decision_trace"]
