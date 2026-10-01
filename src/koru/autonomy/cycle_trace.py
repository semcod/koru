from __future__ import annotations

import re
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.decision_trace import (
    append_decision_record,
    build_decision_record,
    human_skip_reason,
)

if TYPE_CHECKING:
    from koru.autonomy.cycle.cycle_common import DiagnosticResult
    from koru.autonomy.operator.operator_wup import WupHealthResult
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
    from koru.autonomy.cycle.cycle_common import _queue_loop_waiting_ticket_label

    waiting_ticket = _queue_loop_waiting_ticket_label(queue_result)
    if waiting_ticket == "-":
        candidate = getattr(queue_result, "waiting_ticket", None)
        if candidate:
            waiting_ticket = str(candidate)
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
    repeated_idle = (
        str(queue_result.last_status or "").lower() == "idle"
        and waiting_ticket == "-"
        and stagnation_streak > 1
    )
    if repeated_idle:
        return
    for formatted_line in record.to_uri_formatted_trace(color=True):
        hp(f"  {formatted_line}")
    if record.skip_code not in ("ok",):
        reason = human_skip_reason(record.skip_code, fallback=record.skip_code)
        because = record.skip_because
        suffix = f" — {because}" if because else ""
        hp(f"  \033[33mdecision:\033[0m because[{record.skip_code}] {reason}{suffix}")

    # Append markdown-formatted console log to project/ticket-*/koru.log.md
    append_ticket_markdown_log(project, waiting_ticket, record)


def find_ticket_dir(project: Path, ticket_id: str) -> Path | None:
    """Resolve only explicit Wellmanifest IDs; Planfile IDs are a separate namespace.

    Never infer ownership from a shared numeric suffix or choose an arbitrary
    slugged directory when several tickets match.
    """
    raw = ticket_id.strip().lower()
    if not re.fullmatch(r"ticket-[0-9]+(?:--?[a-z0-9]+(?:-[a-z0-9]+)*)?", raw):
        return None
    project_dir = project / "project"
    if not project_dir.is_dir():
        return None
    exact = project_dir / raw
    if exact.is_dir() and not exact.is_symlink():
        return exact
    if not re.fullmatch(r"ticket-[0-9]+", raw):
        return None
    matches = [
        path for path in project_dir.glob(f"{raw}-*")
        if path.is_dir() and not path.is_symlink()
    ]
    return matches[0] if len(matches) == 1 else None


def append_ticket_markdown_log(
    project: Path,
    waiting_ticket: str,
    record: Any,
) -> None:
    """Append decision trace to project/ticket-*/koru.log.md with markdown codeblocks."""
    ticket_dir = find_ticket_dir(project, waiting_ticket)
    if not ticket_dir:
        return

    log_file = ticket_dir / "koru.log.md"
    timestamp = getattr(record, "at", "")
    cycle = getattr(record, "cycle", 0)

    # Format trace as markdown with yaml codeblock
    content_blocks = [
        f"### Cycle {cycle} (`{timestamp}`)\n\n",
        "```yaml\n",
        f"uri: koru://cycle/{cycle}/decision/{record.action}\n",
        f"observed: {record.observed}\n",
        f"decided: {record.decided}\n",
        f"action: {record.action}\n",
        f"evidence: {record.evidence}\n",
    ]
    if getattr(record, "skip_because", ""):
        content_blocks.append(f"because: {record.skip_because}\n")
    if getattr(record, "next_step", ""):
        content_blocks.append(f"next: {record.next_step}\n")
    content_blocks.append("```\n\n")

    # Add alternating NL/DSL trace block
    content_blocks.extend([
        "```yaml\n",
        f'NL: "Cykl {cycle}: {record.decided} ({record.observed})"\n',
        f'DSL: "action: {record.action} [evidence: {record.evidence}]"\n',
        "```\n\n",
    ])

    try:
        if not log_file.exists():
            header = f"# Koru Autonomy Log: `{ticket_dir.name}`\n\n"
            log_file.write_text(header + "".join(content_blocks), encoding="utf-8")
        else:
            with log_file.open("a", encoding="utf-8") as f:
                f.write("".join(content_blocks))
    except OSError:
        pass


def append_queue_ticket_markdown_log(
    project: Path,
    result: Any,
) -> None:
    """Append queue execution event to project/ticket-*/koru.log.md if project has wellmanifest layout."""
    ticket_id = getattr(result, "ticket_id", None)
    if not ticket_id:
        return
    ticket_dir = find_ticket_dir(project, str(ticket_id))
    if not ticket_dir:
        return

    log_file = ticket_dir / "koru.log.md"
    from datetime import UTC, datetime

    timestamp = datetime.now(UTC).replace(microsecond=0).isoformat()
    status = getattr(result, "status", "unknown")
    executor = getattr(result, "executor_kind", "unknown")
    exit_code = getattr(result, "exit_code", 0)
    message = getattr(result, "message", "")

    content_blocks = [
        f"### Queue Run (`{timestamp}`)\n\n",
        "```yaml\n",
        f"uri: koru://queue/task/{ticket_id}/{status}\n",
        f"ticket: {ticket_id}\n",
        f"executor: {executor}\n",
        f"status: {status}\n",
        f"exit_code: {exit_code}\n",
        "```\n\n",
    ]
    if message:
        content_blocks.extend([
            "```text\n",
            f"{message}\n",
            "```\n\n",
        ])

    try:
        if not log_file.exists():
            header = f"# Koru Autonomy Log: `{ticket_dir.name}`\n\n"
            log_file.write_text(header + "".join(content_blocks), encoding="utf-8")
        else:
            with log_file.open("a", encoding="utf-8") as f:
                f.write("".join(content_blocks))
    except OSError:
        pass


__all__ = [
    "append_queue_ticket_markdown_log",
    "append_ticket_markdown_log",
    "decision_next_step_hint",
    "find_ticket_dir",
    "record_decision_trace",
]
