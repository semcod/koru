"""IDE-oriented work prompts for autonomous autopilot when the queue is idle."""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

_PRIORITY_RANK = {"critical": 0, "high": 1, "normal": 2, "low": 3}


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
        )
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
        f"Priority: {priority}" + (f", queue: {queue}" if queue else ""),
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
                f"- koru_list_tickets (project_root = this workspace)",
                f"- koru_run_ticket(ticket_id={ticket_id!r}, mode=apply)",
                "Implement the change, run local regression gates, then mark the ticket done in planfile.",
            ]
        )
    else:
        lines.append("")
        lines.append(
            "Implement the change, run tests/regression gates, then mark the ticket done in planfile."
        )
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

    Returns ``(prompt, kind)`` where ``kind`` is ``idle_ticket_prompt`` or
    ``drive_prompt``.
    """
    ticket = fetch_next_open_ticket(project, runner=runner)
    if ticket is None:
        return drive_prompt, "drive_prompt"
    return (
        build_ide_work_prompt(ticket, fallback=drive_prompt, include_mcp_hint=include_mcp_hint),
        "idle_ticket_prompt",
    )


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
    text = (result.stdout or "") + (result.stderr or "")
    match = re.search(r"Updated\s+(\d+)\s+ticket", text)
    if match:
        return int(match.group(1))
    return 0


__all__ = [
    "build_ide_work_prompt",
    "fetch_next_open_ticket",
    "release_in_progress_tickets",
    "resolve_idle_drive_prompt",
]
