"""Auto-archive non-useful planfile tickets so autonomy is not blocked by noise.

Junk targets (venv, site-packages, PNG dumps, globs, …) cannot be implemented
and must leave the open queue without a human. Koru marks them ``done`` with an
explicit auto-archive note (fail would look like a real implementation error).
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koru.autonomy.code_change_usefulness import is_useful_code_change_path, useful_paths

DEFAULT_ACTOR = "koru-ticket-hygiene"
OPENISH = frozenset(
    {
        "open",
        "todo",
        "ready",
        "backlog",
        "new",
        "blocked",
        "waiting",
        "waiting_input",
        "in_progress",
        "in-progress",
        "doing",
        "",
    }
)


@dataclass
class HygieneOutcome:
    ran: bool = False
    archived: list[str] = field(default_factory=list)
    kept: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        return {
            "ran": self.ran,
            "archived": list(self.archived),
            "kept": list(self.kept),
            "errors": list(self.errors),
        }


def _load_tickets(project: Path, *, sprint: str = "current") -> dict[str, dict[str, Any]]:
    try:
        import yaml

        path = project / ".planfile" / "sprints" / f"{sprint}.yaml"
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, Exception):  # noqa: BLE001
        return {}
    sprint_data = data.get("sprint") if isinstance(data, dict) else None
    tickets = sprint_data.get("tickets") if isinstance(sprint_data, dict) else None
    if not isinstance(tickets, dict):
        return {}
    return {
        str(tid): ticket
        for tid, ticket in tickets.items()
        if isinstance(ticket, dict)
    }


def _status(ticket: dict[str, Any]) -> str:
    return str(ticket.get("status") or "").strip().lower()


def _ticket_paths(ticket: dict[str, Any]) -> list[str]:
    raw = ticket.get("files") or ticket.get("paths") or []
    if isinstance(raw, str):
        raw = [raw]
    return [str(p).strip().replace("\\", "/") for p in raw if str(p).strip()]


def _path_exists_in_project(project: Path, rel_path: str) -> bool:
    candidate = Path(rel_path)
    if candidate.is_file():
        return True
    return (project / rel_path).is_file()


def ticket_has_stale_paths(ticket: dict[str, Any], *, project: Path | None = None) -> bool:
    """True when declared ticket paths no longer exist (common after refactors)."""
    if project is None:
        return False
    paths = _ticket_paths(ticket)
    if not paths:
        return False
    return any(not _path_exists_in_project(project, path) for path in paths)


def ticket_is_junk(ticket: dict[str, Any], *, project: Path | None = None) -> bool:
    """True when every declared path is non-implementable (or a bare glob)."""
    paths = _ticket_paths(ticket)
    if not paths:
        # Empty-file tickets are not auto-junk unless labelled as todo2code noise.
        name = str(ticket.get("name") or "")
        source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
        tool = str(source.get("tool") or "")
        return name.startswith("[todo2code]") or "todo2code" in tool
    useful = useful_paths(paths, project=project)
    return not useful and any(
        not is_useful_code_change_path(path, project=project) or "*" in path
        for path in paths
    )


def _archive_ticket(project: Path, ticket_id: str, *, reason: str, actor: str) -> None:
    note = f"koru auto-archive: {reason}"
    # Prefer done so the queue is free; attach a clear note for audit.
    cmd = [
        "planfile",
        "ticket",
        "done",
        ticket_id,
        "--note",
        note,
        "--actor",
        actor,
    ]
    result = subprocess.run(
        cmd,
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result.returncode == 0:
        return
    # Fallback: status update when done is refused for state reasons.
    cmd2 = [
        "planfile",
        "ticket",
        "update",
        ticket_id,
        "--status",
        "done",
        "--note",
        note,
    ]
    result2 = subprocess.run(
        cmd2,
        cwd=project,
        capture_output=True,
        text=True,
        check=False,
        timeout=60,
    )
    if result2.returncode != 0:
        detail = (result.stderr or result.stdout or result2.stderr or result2.stdout or "").strip()
        raise RuntimeError(detail or f"planfile rc={result.returncode}/{result2.returncode}")


def run_ticket_hygiene(
    project: Path,
    *,
    sprint: str = "current",
    actor: str = DEFAULT_ACTOR,
    only_todo2code: bool = False,
    dry_run: bool = False,
) -> HygieneOutcome:
    project = project.resolve()
    outcome = HygieneOutcome(ran=True)
    tickets = _load_tickets(project, sprint=sprint)
    if not tickets:
        return outcome

    for ticket_id, ticket in tickets.items():
        if _status(ticket) not in OPENISH:
            continue
        if only_todo2code:
            name = str(ticket.get("name") or "")
            source = ticket.get("source") if isinstance(ticket.get("source"), dict) else {}
            tool = str(source.get("tool") or "")
            if not (name.startswith("[todo2code]") or "todo2code" in tool):
                continue
        if not ticket_is_junk(ticket, project=project):
            if ticket_has_stale_paths(ticket, project=project):
                paths = _ticket_paths(ticket)
                reason = f"stale declared paths after refactor: {', '.join(paths[:6])}"
                if dry_run:
                    outcome.archived.append(f"{ticket_id} (dry-run stale)")
                    continue
                try:
                    _archive_ticket(project, ticket_id, reason=reason, actor=actor)
                    outcome.archived.append(ticket_id)
                except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
                    outcome.errors.append(f"{ticket_id}: {exc}")
                continue
            outcome.kept.append(ticket_id)
            continue
        paths = _ticket_paths(ticket)
        reason = (
            f"non-useful target paths: {', '.join(paths[:6])}"
            if paths
            else "todo2code ticket without implementable paths"
        )
        if dry_run:
            outcome.archived.append(f"{ticket_id} (dry-run)")
            continue
        try:
            _archive_ticket(project, ticket_id, reason=reason, actor=actor)
            outcome.archived.append(ticket_id)
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as exc:
            outcome.errors.append(f"{ticket_id}: {exc}")
    return outcome


def format_hygiene_summary(outcome: HygieneOutcome) -> str:
    if not outcome.ran:
        return "ticket hygiene skipped"
    return (
        f"ticket hygiene: archived={len(outcome.archived)} "
        f"kept={len(outcome.kept)} errors={len(outcome.errors)}"
    )


__all__ = [
    "HygieneOutcome",
    "format_hygiene_summary",
    "run_ticket_hygiene",
    "ticket_has_stale_paths",
    "ticket_is_junk",
]
