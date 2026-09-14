"""Planfile reporting for actionable ``koru doctor`` findings."""

from __future__ import annotations

import json
import re
from collections.abc import Callable, Iterable
from pathlib import Path

from koru.doctor_constants import FAIL, WARN
from koru.doctor_models import Check
from koru.task_models import CreatedTask

_TICKETABLE_WARNINGS = frozenset({"python_venv_alignment", "dependency_lock_freshness"})


def _marker_path(project: Path, check_name: str) -> Path:
    safe_name = re.sub(r"[^A-Za-z0-9_.-]+", "-", check_name).strip(".-")
    return project / ".planfile" / ".koru" / "doctor-diagnostic-tickets" / f"{safe_name}.json"


def _load_marker(path: Path) -> str | None:
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return None
    value = payload.get("ticket_id") if isinstance(payload, dict) else None
    return str(value) if value else None


def _ticket_prompt(check: Check) -> str:
    return (
        f"[AUTO-DIAG] Resolve Koru doctor finding: {check.name}.\n\n"
        f"Status: {check.status}.\nEvidence: {check.detail}\n\n"
        "Make the smallest durable correction. Use the project .venv as the canonical "
        "environment, remove or document stale alternate environments, and update the "
        "lockfile only through the project dependency workflow. Run the relevant tests "
        "before completing this ticket."
    )


def report_actionable_findings(
    project: Path,
    checks: Iterable[Check],
    *,
    priority: str = "high",
    queue_name: str | None = None,
    create_task: Callable[..., CreatedTask] | None = None,
) -> list[str]:
    """Create one durable, synced Planfile ticket for each actionable finding.

    The marker is removed when a later doctor run no longer reports that finding,
    allowing a genuine recurrence to be reported again without duplicate tickets
    while the original problem remains open.
    """
    if create_task is None:
        from koru.tasks import create_nl_task

        task_creator = create_nl_task
    else:
        task_creator = create_task
    current = {check.name: check for check in checks}

    def is_actionable(check: Check | None) -> bool:
        return check is not None and (
            check.status == FAIL
            or (check.status == WARN and check.name in _TICKETABLE_WARNINGS)
        )

    marker_dir = project / ".planfile" / ".koru" / "doctor-diagnostic-tickets"
    for path in marker_dir.glob("*.json") if marker_dir.is_dir() else ():
        if not is_actionable(current.get(path.stem)):
            path.unlink(missing_ok=True)

    created: list[str] = []
    for check in current.values():
        actionable = is_actionable(check)
        if not actionable:
            continue
        marker = _marker_path(project, check.name)
        if _load_marker(marker):
            continue
        task = task_creator(
            project,
            _ticket_prompt(check),
            priority=priority,
            queue_name=queue_name,
            scaffold={
                "title": f"[AUTO-DIAG] Resolve {check.name}",
                "labels": ["auto-diag", "doctor"],
            },
        )
        marker.parent.mkdir(parents=True, exist_ok=True)
        marker.write_text(
            json.dumps({"ticket_id": task.ticket_id, "check": check.name}, indent=2) + "\n",
            encoding="utf-8",
        )
        created.append(task.ticket_id)
    return created
