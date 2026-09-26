"""TaskPlan parsing and planfile ticket filing for ``nxdo`` output.

Tickets are created through :func:`koru.tasks.create_nl_task` (same path
as code2llm discovery), so they carry proper ``execution``/``executor``
fields and STARTER-prefixed ids that the queue loop can pick up.
``nxdo``'s own ``--sync-planfile`` is intentionally not used: it writes
``LANE-*`` tickets without an ``execution`` block, which the queue would
never select. ``KORU_NXDO_MAX_TICKETS`` caps tickets created per run
(default 5), and a sprint-wide ``nxdo:`` dedupe key guards against filing
the same task twice.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any, NamedTuple

DEFAULT_SOURCE = "koru-nxdo-discovery"
DEFAULT_MAX_TICKETS = 5

# nxdo Priority -> planfile priority accepted by create_nl_task.
_PRIORITY_MAP = {"high": "high", "medium": "normal", "low": "low"}


def _plan_from_output(stdout: str) -> dict[str, Any] | None:
    """Extract the TaskPlan JSON object from ``nxdo plan --json`` output."""
    text = (stdout or "").strip()
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end <= start:
        return None
    try:
        data = json.loads(text[start : end + 1])
    except ValueError:
        return None
    return data if isinstance(data, dict) else None


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")[:80]


def _dedupe_key(repo: Path, task: dict[str, Any]) -> str:
    return f"nxdo:{repo.name}:{_slug(str(task.get('title') or ''))}"


def _existing_nxdo_dedupe_keys(project: Path, *, sprint: str = "current") -> set[str]:
    try:
        import yaml  # local import; yaml is already a runtime dep of koru

        sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001 - best-effort duplicate guard
        return set()
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return set()
    keys: set[str] = set()
    for ticket in tickets.values():
        if not isinstance(ticket, dict):
            continue
        source = ticket.get("source")
        context = source.get("context") if isinstance(source, dict) else None
        if not isinstance(context, dict):
            continue
        key = str(context.get("dedupe_key") or "").strip()
        if key.startswith("nxdo:"):
            keys.add(key)
    return keys


def _ticket_text(task: dict[str, Any], *, repo: Path, project: Path) -> str:
    lines: list[str] = []
    if repo != project:
        lines.append(f"[repo: {repo}] Zadanie dotyczy repozytorium {repo} (nie {project.name}).")
    description = str(task.get("description") or "").strip()
    lines.append(description or str(task.get("title") or "nxdo task").strip())
    criteria = [str(c).strip() for c in (task.get("acceptance_criteria") or []) if str(c).strip()]
    if criteria:
        lines.append("Acceptance criteria:")
        lines.extend(f"- {c}" for c in criteria)
    return "\n".join(lines)


def _ticket_scaffold(task: dict[str, Any], *, repo: Path, project: Path) -> dict[str, Any]:
    labels = ["nxdo", "discovery"]
    task_type = str(task.get("task_type") or "").strip()
    if task_type:
        labels.append(task_type)
    if repo != project:
        labels.append("cross-repo")
    return {
        "title": str(task.get("title") or "nxdo discovery ticket").strip(),
        "labels": labels,
        "files": [],
        "source_tool": DEFAULT_SOURCE,
        "source_context": {
            "signal": "nxdo_plan",
            "dedupe_key": _dedupe_key(repo, task),
            "repo": str(repo),
        },
        "executor_kind": "human",
        "executor_mode": "interactive",
    }


class _PlanFiling(NamedTuple):
    """Ticket-filing result of :func:`_apply_plan_tickets`."""

    applied: list[str]
    skipped: list[str]


def _apply_plan_tickets(
    project: Path,
    repo: Path,
    plan: dict[str, Any],
    *,
    limit: int,
) -> _PlanFiling:
    from koru.tasks import create_nl_task

    tasks = [t for t in (plan.get("tasks") or []) if isinstance(t, dict)]
    created_titles: list[str] = []
    skipped_titles: list[str] = []
    existing_keys = _existing_nxdo_dedupe_keys(project)
    for task in tasks:
        if len(created_titles) >= limit:
            break
        scaffold = _ticket_scaffold(task, repo=repo, project=project)
        title = str(scaffold["title"])
        key = str(scaffold["source_context"]["dedupe_key"])
        if key in existing_keys:
            skipped_titles.append(title)
            continue
        priority = _PRIORITY_MAP.get(str(task.get("priority") or "").lower(), "normal")
        try:
            created = create_nl_task(
                project,
                _ticket_text(task, repo=repo, project=project),
                sprint="current",
                priority=priority,
                scaffold=scaffold,
            )
        except (OSError, ValueError) as exc:
            skipped_titles.append(f"{title}: {exc}")
            continue
        if getattr(created, "reused", False):
            skipped_titles.append(title)
        else:
            created_titles.append(title)
            existing_keys.add(key)
    return _PlanFiling(created_titles, skipped_titles)
