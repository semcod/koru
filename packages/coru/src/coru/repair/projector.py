"""Project repair events into LLM-readable case summaries (read model)."""

from __future__ import annotations

from collections import defaultdict
from typing import Any

from coru.repair.domain import RepairCaseSummary
from coru.repair.events import RepairEvent
from coru.repair.registry import playbook_for_codes


def project_repair_cases(events: list[RepairEvent]) -> list[RepairCaseSummary]:
    by_session: dict[str, list[RepairEvent]] = defaultdict(list)
    for event in events:
        session_id = str(event.payload.get("session_id") or "")
        if not session_id and event.event_type == "repair.session.started":
            session_id = str(event.payload.get("session_id") or event.event_id)
        if session_id:
            by_session[session_id].append(event)

    cases: list[RepairCaseSummary] = []
    for session_id, session_events in by_session.items():
        case = _project_one_session(session_id, session_events)
        if case is not None:
            cases.append(case)
    cases.sort(key=lambda row: row.occurred_at)
    return cases


def _project_one_session(session_id: str, events: list[RepairEvent]) -> RepairCaseSummary | None:
    started = next((e for e in events if e.event_type == "repair.session.started"), None)
    if started is None:
        return None

    ide = str(started.payload.get("ide") or "")
    instance = str(started.payload.get("instance") or "")
    trigger = str(started.payload.get("trigger") or "unknown")
    occurred_at = started.occurred_at

    problem_codes: list[str] = []
    for event in events:
        if event.event_type == "repair.problems.detected":
            for row in event.payload.get("problems") or []:
                if isinstance(row, dict):
                    code = str(row.get("code") or "").strip()
                    if code:
                        problem_codes.append(code)

    action_ids: list[str] = []
    resolved = False
    for event in events:
        if event.event_type == "repair.attempt.finished":
            action_id = str(event.payload.get("action_id") or "").strip()
            if action_id:
                action_ids.append(action_id)
        if event.event_type == "repair.session.finished":
            resolved = bool(event.payload.get("resolved"))

    playbook = playbook_for_codes(set(problem_codes))
    return RepairCaseSummary(
        session_id=session_id,
        occurred_at=occurred_at,
        ide=ide,
        instance=instance,
        trigger=trigger,
        problem_codes=tuple(dict.fromkeys(problem_codes)),
        action_ids=tuple(action_ids),
        resolved=resolved,
        playbook=playbook,
    )


def format_case_llm(case: RepairCaseSummary) -> str:
    status = "resolved" if case.resolved else "unresolved"
    problems = ", ".join(case.problem_codes) or "(none)"
    actions = " → ".join(case.action_ids) or "(none)"
    lines = [
        f"## {case.occurred_at} {case.ide}/{case.instance} [{status}]",
        f"- trigger: {case.trigger}",
        f"- problems: {problems}",
        f"- actions: {actions}",
    ]
    if case.playbook:
        lines.append("- playbook:")
        lines.append(case.playbook)
    return "\n".join(lines)


def format_history_llm(cases: list[RepairCaseSummary], *, limit: int = 20) -> str:
    if not cases:
        return "# coru repair history\n\n(no repair sessions recorded yet)\n"
    selected = cases[-limit:]
    body = "\n\n".join(format_case_llm(case) for case in selected)
    return (
        "# coru repair history (event-sourced)\n\n"
        "Use prior sessions to pick the same repair command sequence for similar problem codes.\n\n"
        f"{body}\n"
    )
