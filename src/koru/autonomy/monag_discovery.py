"""Idle-time backlog promotion from the read-only ``monag`` inventory.

``planfile ticket next`` serves only the ``current`` sprint. When it is empty
and neither ``koru scan``, code2llm nor todo2code created a ticket, the idle
chain used to fall through to the paid ``nxdo`` planner, which invents new
tickets even when the backlog sprint already holds open work. This adapter
runs first: it reads ``monag --root <project> --json resume`` and moves a
bounded number of existing open tickets into the current sprint.

Only tickets that are unambiguous are promoted: a single ``open`` status,
listed by monag from the primary checkout's own sprint file, still present
there and absent from ``current``. Legacy root ``planfile.yaml``, worktree
copies and conflicting statuses are never touched. Unfinished ticket
worktrees reported by monag are returned read-only for the activity log;
Koru never resumes or takes them over.

Environment knobs:

- ``KORU_MONAG_ENABLE``: ``0``/``false`` disables the adapter (default on).
- ``KORU_MONAG_BIN``: explicit path to the ``monag`` executable (default:
  ``PATH`` lookup).
- ``KORU_MONAG_SPRINTS``: ``,``-separated sprint names to promote from
  (default ``backlog``).
- ``KORU_MONAG_MAX_PROMOTIONS``: cap of tickets moved per run (default 3).
- ``KORU_MONAG_TIMEOUT_SECONDS``: ``monag`` subprocess timeout (default 60).
"""

from __future__ import annotations

import json
import shutil
import subprocess
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

from koru.autonomy.env import env_get, env_int, env_truthy
from koru.queue.ticket import planfile_command

Runner = Callable[[Sequence[str], Path], subprocess.CompletedProcess[str]]

DEFAULT_SPRINTS = ("backlog",)
DEFAULT_MAX_PROMOTIONS = 3
DEFAULT_TIMEOUT_SECONDS = 60
TARGET_SPRINT = "current"
MAX_REPORTED_WORKTREES = 5


@dataclass
class MonagDiscoveryOutcome:
    """Result of one monag backlog promotion attempt."""

    ran: bool = False
    skipped_reason: str | None = None
    monag_path: str | None = None
    monag_duration_s: float | None = None
    remaining: int = 0
    promoted_ids: list[str] = field(default_factory=list)
    skipped_ids: list[str] = field(default_factory=list)
    unfinished_worktrees: list[dict[str, Any]] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "skipped_reason": self.skipped_reason,
            "monag_path": self.monag_path,
            "monag_duration_s": self.monag_duration_s,
            "remaining": self.remaining,
            "applied": list(self.promoted_ids),
            "skipped": list(self.skipped_ids),
            "unfinished_worktrees": list(self.unfinished_worktrees),
            "error": self.error,
        }


def _default_runner(cmd: Sequence[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        list(cmd),
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
        timeout=env_int("KORU_MONAG_TIMEOUT_SECONDS", DEFAULT_TIMEOUT_SECONDS),
    )


def monag_enabled() -> bool:
    return env_truthy("KORU_MONAG_ENABLE", True)


def _monag_executable() -> str | None:
    override = env_get("KORU_MONAG_BIN", None)
    if override:
        return override if Path(override).is_file() else None
    return shutil.which("monag")


def _source_sprints() -> tuple[str, ...]:
    raw = env_get("KORU_MONAG_SPRINTS", None)
    if raw is None:
        return DEFAULT_SPRINTS
    names = tuple(name.strip() for name in raw.split(",") if name.strip())
    return tuple(name for name in names if name != TARGET_SPRINT) or DEFAULT_SPRINTS


def _sprint_ticket_statuses(project: Path, sprint: str) -> dict[str, str]:
    """Ticket id -> status read from ``.planfile/sprints/<sprint>.yaml``."""
    try:
        data = yaml.safe_load((project / ".planfile" / "sprints" / f"{sprint}.yaml").read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError):
        return {}
    container = data.get("sprint") if isinstance(data, dict) and isinstance(data.get("sprint"), dict) else data
    tickets = container.get("tickets") if isinstance(container, dict) else None
    if isinstance(tickets, dict):
        rows = [(key, value) for key, value in tickets.items() if isinstance(value, dict)]
    elif isinstance(tickets, list):
        rows = [(None, value) for value in tickets if isinstance(value, dict)]
    else:
        return {}
    return {
        str(value.get("id") or key): str(value.get("status") or "").lower()
        for key, value in rows
        if value.get("id") or key
    }


def _monag_project(payload: dict[str, Any], project: Path) -> dict[str, Any] | None:
    for entry in payload.get("projects") or []:
        if isinstance(entry, dict) and Path(str(entry.get("path") or "")).resolve() == project:
            return entry
    return None


def _unfinished_worktrees(entry: dict[str, Any]) -> list[dict[str, Any]]:
    return [
        {
            "ticket": checkout.get("ticket"),
            "path": checkout.get("path"),
            "stage": checkout.get("stage"),
            "readiness": checkout.get("readiness"),
            "lease_status": checkout.get("lease_status"),
        }
        for checkout in entry.get("checkouts") or []
        if isinstance(checkout, dict) and checkout.get("unfinished") and checkout.get("ticket")
    ]


def _promotion_candidates(project: Path, entry: dict[str, Any]) -> tuple[list[tuple[str, str]], list[str]]:
    """Return ``(ticket_id, sprint)`` pairs in monag priority order plus rejected ids."""
    sprints = _source_sprints()
    source_to_sprint = {str(project / ".planfile" / "sprints" / f"{name}.yaml"): name for name in sprints}
    sprint_statuses = {name: _sprint_ticket_statuses(project, name) for name in sprints}
    current_ids = set(_sprint_ticket_statuses(project, TARGET_SPRINT))
    planfile = entry.get("planfile") if isinstance(entry.get("planfile"), dict) else {}
    candidates: list[tuple[str, str]] = []
    rejected: list[str] = []
    for ticket in planfile.get("remaining_tickets") or []:
        if not isinstance(ticket, dict):
            continue
        ticket_id = str(ticket.get("id") or "")
        sprint = source_to_sprint.get(str(ticket.get("source") or ""))
        if not ticket_id or sprint is None:
            continue
        if (
            ticket.get("status") != "open"
            or ticket_id in current_ids
            or sprint_statuses[sprint].get(ticket_id) != "open"
        ):
            rejected.append(ticket_id)
            continue
        candidates.append((ticket_id, sprint))
    return candidates, rejected


def run_monag_discovery(
    project: Path,
    *,
    runner: Runner = _default_runner,
) -> MonagDiscoveryOutcome:
    """Promote open backlog tickets reported by ``monag`` into the current sprint."""
    project = project.resolve()
    outcome = MonagDiscoveryOutcome()

    if not monag_enabled():
        outcome.skipped_reason = "disabled via KORU_MONAG_ENABLE"
        return outcome

    binary = _monag_executable()
    if binary is None:
        outcome.skipped_reason = "monag not on PATH (set KORU_MONAG_BIN)"
        return outcome
    outcome.monag_path = binary

    start = time.monotonic()
    try:
        result = runner([binary, "--root", str(project), "--json", "resume"], project)
    except subprocess.TimeoutExpired as exc:
        outcome.error = f"monag timed out after {exc.timeout}s"
        return outcome
    except (OSError, ValueError) as exc:
        outcome.error = f"monag exec failed: {exc}"
        return outcome
    finally:
        outcome.monag_duration_s = time.monotonic() - start
    outcome.ran = True

    if result.returncode != 0:
        lines = (result.stderr or result.stdout or "").strip().splitlines()
        outcome.error = (lines[-1:] or [f"monag rc={result.returncode}"])[0]
        return outcome
    try:
        payload = json.loads(result.stdout)
    except ValueError:
        outcome.error = "monag produced no parseable resume JSON"
        return outcome
    entry = _monag_project(payload, project) if isinstance(payload, dict) else None
    if entry is None:
        outcome.error = "monag resume did not report this project"
        return outcome

    planfile = entry.get("planfile") if isinstance(entry.get("planfile"), dict) else {}
    outcome.remaining = int(planfile.get("remaining") or 0)
    outcome.unfinished_worktrees = _unfinished_worktrees(entry)
    candidates, outcome.skipped_ids = _promotion_candidates(project, entry)

    limit = max(1, env_int("KORU_MONAG_MAX_PROMOTIONS", DEFAULT_MAX_PROMOTIONS))
    for ticket_id, _sprint in candidates[:limit]:
        moved = planfile_command(project, ["ticket", "move", ticket_id, TARGET_SPRINT], runner=runner)
        if moved.returncode == 0:
            outcome.promoted_ids.append(ticket_id)
        else:
            outcome.skipped_ids.append(ticket_id)
    return outcome


def format_monag_summary(outcome: MonagDiscoveryOutcome) -> str:
    """One-line summary suitable for the koru activity log."""
    if outcome.skipped_reason and not outcome.ran:
        return f"monag backlog promotion skipped: {outcome.skipped_reason}"
    if outcome.error:
        return f"monag backlog promotion error: {outcome.error}"
    pieces = [f"remaining={outcome.remaining}", f"promoted={len(outcome.promoted_ids)}"]
    if outcome.promoted_ids:
        pieces.append(f"ids={','.join(outcome.promoted_ids)}")
    pieces.append(f"skipped={len(outcome.skipped_ids)}")
    pieces.append(f"unfinished_worktrees={len(outcome.unfinished_worktrees)}")
    return "monag backlog promotion: " + " ".join(pieces)


def format_unfinished_worktrees(outcome: MonagDiscoveryOutcome) -> list[str]:
    """Read-only hint lines; resuming a worktree needs its own lease."""
    return [
        f"  unfinished {row['ticket']}: {row['stage']} / {row['readiness']} "
        f"(lease={row['lease_status']}) {row['path']}"
        for row in outcome.unfinished_worktrees[:MAX_REPORTED_WORKTREES]
    ]


__all__ = [
    "MonagDiscoveryOutcome",
    "Runner",
    "format_monag_summary",
    "format_unfinished_worktrees",
    "monag_enabled",
    "run_monag_discovery",
]
