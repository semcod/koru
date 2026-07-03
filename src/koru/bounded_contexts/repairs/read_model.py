"""Read models and formatters for repair history."""

from __future__ import annotations

from koru.cqrs import EventLogEntry, EventLogProjection

from .events import REPAIR_CONTEXT


class RepairEventLogProjection(EventLogProjection):
    """In-memory read model for repair history."""

    def __init__(self) -> None:
        super().__init__(context=REPAIR_CONTEXT)


def _format_status_lines(payload: dict) -> list[str]:
    status = payload.get("status")
    if not isinstance(status, dict):
        return []
    lines: list[str] = []
    ready = status.get("ready")
    if ready is not None:
        lines.append(f"  ready: {ready}")
    for key in ("daemon_running", "plugins_connected", "plugins_compatible"):
        if key in status:
            lines.append(f"  {key}: {status[key]}")
    return lines


def _format_hypothesis_lines(hypothesis: dict) -> list[str]:
    hid = hypothesis.get("id") or "unknown"
    confidence = hypothesis.get("confidence")
    evidence = str(hypothesis.get("evidence") or "").strip()
    remediation = str(hypothesis.get("remediation") or "").strip()
    first = f"    - {hid}"
    if confidence is not None:
        first += f" ({confidence}%)"
    lines = [first]
    if evidence:
        lines.append(f"      evidence: {evidence}")
    if remediation:
        lines.append(f"      remediation: {remediation}")
    return lines


def _format_hypotheses_lines(payload: dict) -> list[str]:
    hypotheses = payload.get("hypotheses")
    if not (isinstance(hypotheses, list) and hypotheses):
        return []
    lines = ["  hypotheses:"]
    for hypothesis in hypotheses[:5]:
        if isinstance(hypothesis, dict):
            lines.extend(_format_hypothesis_lines(hypothesis))
    return lines


def _format_action_lines(payload: dict) -> list[str]:
    actions = payload.get("actions")
    if not (isinstance(actions, list) and actions):
        return []
    return ["  actions:", *(f"    - {action}" for action in actions[:10])]


def _format_entry_details(payload: dict) -> list[str]:
    """Extract status/hypotheses/actions lines from a repair event payload."""
    return [
        *_format_status_lines(payload),
        *_format_hypotheses_lines(payload),
        *_format_action_lines(payload),
    ]


def format_repair_history_for_llm(entries: list[EventLogEntry]) -> str:
    """Render compact, chronological repair history for LLM context."""
    if not entries:
        return "repair history: empty"
    lines = ["repair history:"]
    for entry in entries:
        payload = entry.payload
        subject = entry.aggregate_id or str(payload.get("subject") or "unknown")
        summary = str(payload.get("summary") or "").strip()
        lines.append(
            f"- #{entry.sequence} {entry.occurred_at} "
            f"{entry.event_type} subject={subject}"
        )
        if summary:
            lines.append(f"  summary: {summary}")
        lines.extend(_format_entry_details(payload))
    return "\n".join(lines)


__all__ = [
    "EventLogEntry",
    "RepairEventLogProjection",
    "format_repair_history_for_llm",
]
