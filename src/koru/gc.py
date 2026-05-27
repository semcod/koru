"""Garbage collection for the planfile queue.

Removes stale tickets (done, failed, blocked) that exceed a
configurable age or count threshold.  Supports dry-run preview and
an optional JSONL archive so nothing is silently lost.

Usage (from CLI)::

    koru gc                        # dry-run: show what would be removed
    koru gc --apply                # actually delete stale tickets
    koru gc --max-age 7            # keep tickets younger than 7 days
    koru gc --keep-last 5          # always keep the 5 most recent done tickets
    koru gc --status done,failed   # only clean these statuses
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from importlib.util import find_spec
from pathlib import Path
from typing import Any

import yaml

# -- data types --------------------------------------------------------------


@dataclass(frozen=True)
class GcCandidate:
    """A ticket eligible for garbage collection."""

    ticket_id: str
    name: str
    status: str
    execution_state: str
    finished_at: datetime | None
    age_days: float


@dataclass
class GcResult:
    """Outcome of a gc run."""

    candidates: list[GcCandidate] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    removed: list[str] = field(default_factory=list)
    archived_to: Path | None = None
    dry_run: bool = True
    errors: list[str] = field(default_factory=list)

    def summary(self) -> str:
        parts = [
            f"candidates={len(self.candidates)}",
            f"removed={len(self.removed)}",
            f"kept={len(self.kept)}",
        ]
        if self.archived_to:
            parts.append(f"archive={self.archived_to}")
        if self.dry_run:
            parts.append("dry_run=true")
        return " ".join(parts)


# -- constants ---------------------------------------------------------------

DEFAULT_MAX_AGE_DAYS: int = 30
DEFAULT_KEEP_LAST: int = 0
GC_STATUSES: frozenset[str] = frozenset({"done", "failed", "blocked"})


# -- helpers -----------------------------------------------------------------


def _now_utc() -> datetime:
    return datetime.now(UTC)


def _parse_ts(raw: str | None) -> datetime | None:
    """Best-effort ISO-8601 timestamp parse."""
    if not raw:
        return None
    try:
        # Python 3.11+ handles trailing Z
        return datetime.fromisoformat(raw.replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None


def _planfile_env() -> dict[str, str]:
    return {**os.environ, "COLUMNS": "10000", "TERM": "dumb", "PYTHONWARNINGS": "ignore"}


def _run_planfile(
    args: Sequence[str],
    project: Path,
    runner: Callable[[Sequence[str], Path], Any] | None = None,
) -> Any:
    """Run a planfile CLI command."""
    if runner is not None:
        configured = os.getenv("KORU_PLANFILE_CMD")
        if configured:
            import shlex

            base = shlex.split(configured)
        elif find_spec("planfile") is not None:
            base = [sys.executable, "-m", "planfile.cli"]
        else:
            base = ["planfile"]
        return runner([*base, *args], project)

    configured = os.getenv("KORU_PLANFILE_CMD")
    if configured:
        import shlex

        base = shlex.split(configured)
    elif find_spec("planfile") is not None:
        base = [sys.executable, "-m", "planfile.cli"]
    else:
        base = ["planfile"]
    return subprocess.run(
        [*base, *args],
        cwd=project,
        text=True,
        capture_output=True,
        check=False,
        env=_planfile_env(),
    )


def _load_tickets_from_sprint(project: Path, sprint: str = "current") -> list[dict[str, Any]]:
    """Load tickets directly from the sprint YAML file."""
    sprint_path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
    if not sprint_path.exists():
        return []
    data = yaml.safe_load(sprint_path.read_text(encoding="utf-8")) or {}
    sprint_data = data.get("sprint") or {}
    tickets_map = sprint_data.get("tickets") or {}
    return [
        {**ticket, "id": tid} for tid, ticket in tickets_map.items() if isinstance(ticket, dict)
    ]


def _archive_tickets(
    tickets: list[dict[str, Any]],
    project: Path,
) -> Path:
    """Write removed tickets to a JSONL archive under .planfile/.koru/gc/."""
    gc_dir = project / ".planfile" / ".koru" / "gc"
    gc_dir.mkdir(parents=True, exist_ok=True)
    ts = _now_utc().strftime("%Y%m%d-%H%M%S")
    archive_path = gc_dir / f"gc-{ts}.jsonl"
    with archive_path.open("w", encoding="utf-8") as fh:
        for ticket in tickets:
            json.dump(ticket, fh, default=str, sort_keys=True)
            fh.write("\n")
    return archive_path


# -- core --------------------------------------------------------------------


def collect_gc_candidates(
    project: Path,
    *,
    statuses: frozenset[str] = GC_STATUSES,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    sprint: str = "current",
) -> list[GcCandidate]:
    """Scan the sprint for tickets eligible for garbage collection.

    A ticket is a candidate if:
    - Its ``status`` is in *statuses* (default: done, failed, blocked).
    - Its age (time since ``execution.finished_at`` or ``updated_at``)
      exceeds *max_age_days*.  If no timestamp is available the ticket
      is included (assumes it is old enough).
    """
    now = _now_utc()
    cutoff = now - timedelta(days=max_age_days)
    sprint_tickets = _load_tickets_from_sprint(project, sprint)

    candidates: list[GcCandidate] = []
    for ticket in sprint_tickets:
        status = ticket.get("status", "")
        if status not in statuses:
            continue

        execution = ticket.get("execution") or {}
        finished_raw = execution.get("finished_at") or ticket.get("updated_at")
        finished = _parse_ts(str(finished_raw) if finished_raw else None)

        if finished is not None and finished > cutoff:
            continue  # too recent

        age_days = (now - finished).total_seconds() / 86400 if finished else float("inf")

        candidates.append(
            GcCandidate(
                ticket_id=str(ticket.get("id", "")),
                name=str(ticket.get("name", "")),
                status=status,
                execution_state=str(execution.get("state", "")),
                finished_at=finished,
                age_days=round(age_days, 1),
            ),
        )

    # Sort oldest first
    candidates.sort(key=lambda c: c.age_days, reverse=True)
    return candidates


def _apply_keep_last(
    candidates: list[GcCandidate],
    keep_last: int,
    kept_ids: list[str],
) -> list[GcCandidate]:
    """Apply keep_last logic to filter candidates.

    Returns list of candidates that can be removed.
    """
    if keep_last <= 0:
        return list(candidates)

    to_remove: list[GcCandidate] = []
    by_status: dict[str, list[GcCandidate]] = {}
    for c in candidates:
        by_status.setdefault(c.status, []).append(c)
    for _status, group in by_status.items():
        # group is sorted oldest-first; the last keep_last are newest
        removable = group[:-keep_last] if len(group) > keep_last else []
        protected = group[-keep_last:] if len(group) > keep_last else group
        to_remove.extend(removable)
        kept_ids.extend(c.ticket_id for c in protected)
    return to_remove


def _archive_tickets_before_delete(
    to_remove: list[GcCandidate],
    project: Path,
    sprint: str,
) -> str | None:
    """Archive tickets before deletion.

    Returns archive file path if any tickets were archived, None otherwise.
    """
    archive_source_tickets = _load_tickets_from_sprint(project, sprint)
    remove_ids = {c.ticket_id for c in to_remove}
    tickets_to_archive = [t for t in archive_source_tickets if t.get("id") in remove_ids]
    if tickets_to_archive:
        return _archive_tickets(tickets_to_archive, project)
    return None


def _delete_tickets(
    to_remove: list[GcCandidate],
    project: Path,
    planfile_runner: Callable | None,
) -> tuple[list[str], list[str], list[str]]:
    """Delete tickets via planfile CLI.

    Returns tuple of (removed_ids, kept_ids, errors).
    """
    removed_ids: list[str] = []
    kept_ids: list[str] = []
    errors: list[str] = []
    remove_ids_list = [c.ticket_id for c in to_remove]

    proc = _run_planfile(
        ["ticket", "delete", "--force", *remove_ids_list],
        project,
        runner=planfile_runner,
    )
    if proc.returncode == 0:
        removed_ids = remove_ids_list
    else:
        # If bulk delete failed, try one by one
        for tid in remove_ids_list:
            proc = _run_planfile(
                ["ticket", "delete", "--force", tid],
                project,
                runner=planfile_runner,
            )
            if proc.returncode == 0:
                removed_ids.append(tid)
            else:
                errors.append(f"{tid}: {(proc.stderr or '').strip()[:200]}")
                kept_ids.append(tid)

    return removed_ids, kept_ids, errors


def run_gc(
    project: Path,
    *,
    apply: bool = False,
    statuses: frozenset[str] = GC_STATUSES,
    max_age_days: int = DEFAULT_MAX_AGE_DAYS,
    keep_last: int = DEFAULT_KEEP_LAST,
    sprint: str = "current",
    archive: bool = True,
    planfile_runner: Callable[[Sequence[str], Path], Any] | None = None,
) -> GcResult:
    """Run garbage collection on the planfile queue.

    Parameters
    ----------
    project : Path
        Project root containing ``.planfile/``.
    apply : bool
        When False (default), only preview — no tickets are deleted.
    statuses : frozenset[str]
        Which ticket statuses are eligible for cleanup.
    max_age_days : int
        Tickets finished more than this many days ago are candidates.
    keep_last : int
        Always keep the N most recently finished tickets per status,
        even if they exceed *max_age_days*.  0 = no minimum kept.
    sprint : str
        Sprint YAML to scan (default "current").
    archive : bool
        When True and *apply* is True, dump removed tickets to a JSONL
        archive under ``.planfile/.koru/gc/`` before deletion.
    planfile_runner : callable | None
        Optional injection point for planfile CLI calls (testing).
    """
    project = project.resolve()
    result = GcResult(dry_run=not apply)

    candidates = collect_gc_candidates(
        project,
        statuses=statuses,
        max_age_days=max_age_days,
        sprint=sprint,
    )
    result.candidates = candidates

    if not candidates:
        return result

    # Apply keep_last: per status, protect the N most recent tickets.
    to_remove = _apply_keep_last(candidates, keep_last, result.kept)

    if not to_remove:
        result.kept = [c.ticket_id for c in candidates]
        return result

    if not apply:
        # Dry run — mark all removable as "would remove"
        result.removed = [c.ticket_id for c in to_remove]
        result.kept = [c.ticket_id for c in candidates if c.ticket_id not in set(result.removed)]
        return result

    # Archive before delete
    if archive:
        result.archived_to = _archive_tickets_before_delete(to_remove, project, sprint)

    # Delete via planfile CLI
    removed_ids, kept_ids, errors = _delete_tickets(to_remove, project, planfile_runner)
    result.removed = removed_ids
    result.kept.extend(kept_ids)
    result.errors = errors
    # Update kept list to include all candidates that weren't removed
    result.kept = [c.ticket_id for c in candidates if c.ticket_id not in set(removed_ids)]

    return result
