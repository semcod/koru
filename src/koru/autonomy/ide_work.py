"""IDE-oriented work prompts for autonomous autopilot when the queue is idle."""


import json
import os
import re
import subprocess
from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from koru.autonomy.planfile_handoff import planfile_status_handoff_lines
from koru.project_pipeline import load_koru_project_pipeline
from koru.tasks import create_nl_task

_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}
_TICKET_ID_RE = re.compile(r"\b(PLF-\d+)\b", re.IGNORECASE)
_PROJECT_DISCOVERY_SOURCE = "koru-project-discovery"
_PROJECT_DISCOVERY_SIGNAL = "project_discovery"
_PROJECT_DISCOVERY_TITLE = "Project discovery: generate code2llm analysis and tickets"
_PROJECT_DISCOVERY_ACTIVE_STATUSES = {"open", "ready", "todo", "in_progress"}
_PROJECT_DISCOVERY_BODY = """Run a broad project discovery pass because the planfile queue is idle.

Goal: move Koru from local implementation mode back to whole-project strategy,
then create concrete tickets and let the normal queue work through them.

1. Generate fresh whole-project context:
    code2llm ./ -f all -o ./project --no-chunk --exclude '*.md'

2. Ask IDE LLM after the code2llm refresh:
    "Co jeszcze zostalo do wykonania? zrob z tego nastepne tickety do planfile."
    Keep the answer ticket-oriented (no broad multi-file edits in this step).

3. Convert findings into tickets:
    koru scan --apply --semcod-artifacts --source koru-scan

4. Prefer high-signal work: failing gates, god modules, duplicated code, high
    cyclomatic complexity, missing tests, and architecture seams that block future tickets.

5. When new tickets exist, stop broad discovery and work the tickets one by one.
    After those tickets are done and the queue is empty again, another discovery pass
    is allowed.
"""


def extract_ticket_id_from_text(text: str) -> str | None:
    """Return the first planfile ticket id embedded in ``text`` (e.g. IDE prompt)."""
    match = _TICKET_ID_RE.search(text or "")
    if not match:
        return None
    return match.group(1).upper()


def _parse_open_tickets(stdout: str) -> list[dict[str, Any]]:
    try:
        payload = json.loads((stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    open_statuses = {"open", "ready", "todo"}
    tickets: list[dict[str, Any]] = []
    for entry in payload:
        if not isinstance(entry, dict):
            continue
        status = str(entry.get("status") or "").lower()
        if status in open_statuses:
            tickets.append(entry)
    tickets.sort(
        key=lambda t: (
            _PRIORITY_RANK.get(str(t.get("priority") or "normal"), 2),
            str(t.get("created_at") or ""),
        ),
    )
    return tickets


def fetch_next_open_ticket(
    project: Path,
    *,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> dict[str, Any] | None:
    """Return the highest-priority open ticket, if any."""
    try:
        result = runner(
            ["planfile", "ticket", "list", "--status", "open", "--format", "json"],
            project,
        )
    except (FileNotFoundError, OSError):
        return None
    if result.returncode != 0:
        return None
    tickets = _parse_open_tickets(result.stdout or "")
    return tickets[0] if tickets else None


def sprint_ticket_status_summary(project: Path | str) -> str:
    """Compact ``open=2 done=23`` snapshot for operator logs."""
    tickets = _current_sprint_tickets(Path(project))
    if not tickets:
        return "planfile: 0 tickets in current sprint"
    counts: dict[str, int] = {}
    for ticket in tickets:
        status = str(ticket.get("status") or "unknown").strip().lower() or "unknown"
        counts[status] = counts.get(status, 0) + 1
    parts = [f"{status}={count}" for status, count in sorted(counts.items())]
    return "planfile: " + ", ".join(parts)


def _current_sprint_tickets(project: Path) -> list[dict[str, Any]]:
    sprint_path = project / ".planfile" / "sprints" / "current.yaml"
    try:
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    sprint = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if isinstance(tickets, dict):
        return [ticket for ticket in tickets.values() if isinstance(ticket, dict)]
    if isinstance(tickets, list):
        return [ticket for ticket in tickets if isinstance(ticket, dict)]
    return []


def _is_active_project_discovery_ticket(ticket: dict[str, Any]) -> bool:
    status = str(ticket.get("status") or "").strip().lower()
    if status not in _PROJECT_DISCOVERY_ACTIVE_STATUSES:
        return False
    source = ticket.get("source")
    context = source.get("context") if isinstance(source, dict) else None
    if not isinstance(context, dict):
        return False
    return (
        source.get("tool") == _PROJECT_DISCOVERY_SOURCE
        and context.get("signal") == _PROJECT_DISCOVERY_SIGNAL
    )


def _active_project_discovery_ticket(project: Path) -> dict[str, Any] | None:
    tickets = [
        t for t in _current_sprint_tickets(project) if _is_active_project_discovery_ticket(t)
    ]
    tickets.sort(
        key=lambda t: (
            _PRIORITY_RANK.get(str(t.get("priority") or "normal"), 2),
            str(t.get("created_at") or ""),
        ),
    )
    return tickets[0] if tickets else None


def _ticket_from_created_discovery(ticket_id: str) -> dict[str, Any]:
    return {
        "id": ticket_id,
        "status": "open",
        "priority": "high",
        "name": _PROJECT_DISCOVERY_TITLE,
        "description": _PROJECT_DISCOVERY_BODY,
        "execution": {"queue": "operator"},
    }


def ensure_project_discovery_ticket(
    project: Path,
    *,
    auto_run_code2llm: bool = True,
) -> dict[str, Any] | None:
    """Run code2llm discovery automatically when possible; otherwise create ticket.

    When ``code2llm`` is installed we generate fresh artifacts and apply
    planfile tickets locally rather than sending a long checklist to the IDE
    LLM. The legacy human ticket is created only when:

    * ``auto_run_code2llm`` is ``False`` (test/CI override),
    * the ``code2llm`` binary is missing,
    * the discovery run failed.

    Returns the active discovery ticket (existing or newly created) or
    ``None`` when discovery succeeded and produced runnable tickets.
    """
    existing = _active_project_discovery_ticket(project)
    if existing is not None:
        return existing

    if auto_run_code2llm:
        from koru.autonomy.code2llm_discovery import (
            format_discovery_summary,
            run_code2llm_discovery,
        )

        outcome = run_code2llm_discovery(project)
        summary = format_discovery_summary(outcome)
        try:
            from koru.activity_log import activity

            activity("SCAN", summary)
        except Exception:  # noqa: BLE001 — activity log is best-effort
            print(f"koru autonomous: {summary}")
        if outcome.ran and outcome.code2llm_returncode == 0:
            # Real, actionable tickets were applied (or already up-to-date).
            return None
        if outcome.skipped_reason and outcome.applied_titles:
            return None

    generation = datetime.now(UTC).isoformat()
    try:
        created = create_nl_task(
            project,
            _PROJECT_DISCOVERY_BODY,
            queue_name="operator",
            priority="high",
            scaffold={
                "title": _PROJECT_DISCOVERY_TITLE,
                "labels": ["project-discovery", "code2llm", "scan", "strategy"],
                "files": ["project/analysis.toon.yaml"],
                "source_tool": _PROJECT_DISCOVERY_SOURCE,
                "source_context": {
                    "signal": _PROJECT_DISCOVERY_SIGNAL,
                    "generation": generation,
                    "dedupe_key": f"koru:project-discovery:{generation}",
                },
                "executor_kind": "human",
                "executor_mode": "interactive",
            },
        )
    except (OSError, ValueError):
        return None
    return _ticket_from_created_discovery(created.ticket_id)


def build_ide_work_prompt(
    ticket: dict[str, Any],
    *,
    fallback: str,
    include_mcp_hint: bool = True,
) -> str:
    """Build a concrete IDE/LLM handoff prompt for one planfile ticket."""
    ticket_id = str(ticket.get("id") or "").strip()
    name = str(ticket.get("name") or ticket_id or "ticket").strip()
    description = str(ticket.get("description") or "").strip()
    priority = str(ticket.get("priority") or "normal")
    queue = ""
    execution = ticket.get("execution")
    if isinstance(execution, dict) and execution.get("queue"):
        queue = str(execution["queue"])

    lines = [
        f"Work on planfile ticket {ticket_id}: {name}",
        f"Priority: {priority}{f', queue: {queue}' if queue else ''}",
    ]
    if description:
        lines.append("")
        lines.append("Description:")
        lines.append(description[:4000])
    if include_mcp_hint:
        lines.extend(
            [
                "",
                "Use koru MCP tools when available:",
                "- koru_list_tickets (project_root = this workspace)",
                f"- koru_run_ticket(ticket_id={ticket_id!r}, mode=apply)",
                "Implement the change and run local regression gates.",
                "",
                *planfile_status_handoff_lines(ticket_id),
            ],
        )
    else:
        lines.append("")
        lines.append("Implement the change and run tests/regression gates.")
        lines.append("")
        lines.extend(planfile_status_handoff_lines(ticket_id))
    prompt = "\n".join(lines).strip()
    return prompt if prompt else fallback


def resolve_idle_drive_prompt(
    project: Path,
    *,
    drive_prompt: str,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
    include_mcp_hint: bool = True,
) -> tuple[str, str]:
    """When the queue is idle, prefer a ticket-specific IDE prompt if work exists.

    Returns ``(prompt, kind)`` where ``kind`` is ``idle_ticket_prompt`` when
    runnable IDE work exists. If no ticket exists, return ``idle_no_ticket``;
    broad project discovery is handled locally by the idle scan/diagnostics
    phases rather than pasted into the IDE chat.
    """
    ticket = fetch_next_open_ticket(project, runner=runner)
    if ticket is None:
        return drive_prompt, "idle_no_ticket"
    return (
        build_ide_work_prompt(ticket, fallback=drive_prompt, include_mcp_hint=include_mcp_hint),
        "idle_ticket_prompt",
    )


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        dt = datetime.fromisoformat(text)
    except ValueError:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt


def _ticket_in_progress_started_at(ticket: dict[str, Any]) -> datetime | None:
    execution = ticket.get("execution")
    if isinstance(execution, dict):
        started = _parse_iso_datetime(execution.get("started_at"))
        if started is not None:
            return started
    return _parse_iso_datetime(ticket.get("updated_at"))


def _list_in_progress_tickets(
    project: Path,
    *,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> list[dict[str, Any]]:
    try:
        result = runner(
            [
                "planfile",
                "ticket",
                "list",
                "--status",
                "in_progress",
                "--format",
                "json",
            ],
            project,
        )
    except (FileNotFoundError, OSError):
        return []
    if result.returncode != 0:
        return []
    try:
        payload = json.loads((result.stdout or "").strip() or "[]")
    except json.JSONDecodeError:
        return []
    if not isinstance(payload, list):
        return []
    return [entry for entry in payload if isinstance(entry, dict)]


def release_stale_in_progress_tickets(
    project: Path,
    *,
    stale_minutes: float,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> int:
    """Reopen ``in_progress`` tickets older than ``stale_minutes``. Returns count."""
    if stale_minutes <= 0:
        return 0
    cutoff = datetime.now(UTC) - timedelta(minutes=stale_minutes)
    released = 0
    for ticket in _list_in_progress_tickets(project, runner=runner):
        ticket_id = str(ticket.get("id") or "").strip()
        if not ticket_id:
            continue
        started = _ticket_in_progress_started_at(ticket)
        if started is None or started > cutoff:
            continue
        note = (
            f"koru: stale in_progress (>{stale_minutes:.0f}m since "
            f"{started.isoformat()}) — reopened for queue/IDE"
        )
        result = runner(
            [
                "planfile",
                "ticket",
                "update",
                ticket_id,
                "--status",
                "open",
                "--note",
                note,
            ],
            project,
        )
        if result.returncode == 0:
            released += 1
    return released


def resolve_in_progress_stale_minutes(project: Path | None = None) -> float | None:
    """Env ``KORU_INPROGRESS_STALE_MINUTES`` or ``queue.in_progress_stale_minutes`` in koru.yaml."""
    env_raw = os.environ.get("KORU_INPROGRESS_STALE_MINUTES", "").strip()
    if env_raw:
        try:
            value = float(env_raw)
            return value if value > 0 else None
        except ValueError:
            return None
    if project is None:
        return None
    raw = load_koru_project_pipeline(project)
    if not isinstance(raw, dict):
        return None
    queue = raw.get("queue")
    if not isinstance(queue, dict):
        return None
    yaml_val = queue.get("in_progress_stale_minutes")
    if yaml_val is None:
        return None
    try:
        value = float(yaml_val)
    except (TypeError, ValueError):
        return None
    return value if value > 0 else None


def release_in_progress_tickets(
    project: Path,
    *,
    runner: Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]],
) -> int:
    """Move all ``in_progress`` tickets back to ``open``. Returns count updated."""
    try:
        result = runner(
            [
                "planfile",
                "ticket",
                "bulk-update",
                "--status-filter",
                "in_progress",
                "--new-status",
                "open",
                "--force",
            ],
            project,
        )
    except (FileNotFoundError, OSError):
        return 0
    if result.returncode != 0:
        return 0
    text = f"{result.stdout or ''}{result.stderr or ''}"
    match = re.search(r"Updated\s+(\d+)\s+ticket", text)
    if match:
        return int(match.group(1))
    return 0


__all__ = [
    "build_ide_work_prompt",
    "ensure_project_discovery_ticket",
    "extract_ticket_id_from_text",
    "fetch_next_open_ticket",
    "release_in_progress_tickets",
    "release_stale_in_progress_tickets",
    "resolve_idle_drive_prompt",
    "resolve_in_progress_stale_minutes",
    "sprint_ticket_status_summary",
]
