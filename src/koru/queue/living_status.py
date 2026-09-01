"""Transport-neutral Living Status projection for Planfile tickets.

Koru writes one marker-delimited block into the canonical Planfile ticket.
Planfile's configured sync process owns any GitHub, OneDev, Jira or GitLab
effect; this module intentionally has no remote-tracker client or credential.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from koru.queue.types import CommandResult

LIVING_STATUS_START = "<!-- koru:living-status:start -->"
LIVING_STATUS_END = "<!-- koru:living-status:end -->"


def _inline(value: object, *, limit: int = 300) -> str:
    return " ".join(str(value or "-").split())[:limit]


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def lease_expiry_text(*, lease_seconds: int, now: datetime | None = None) -> str:
    moment = now or datetime.now(UTC)
    return _utc_text(moment + timedelta(seconds=lease_seconds))


def _control_url(ticket: dict[str, Any]) -> str:
    sync = ticket.get("sync") if isinstance(ticket.get("sync"), dict) else {}
    for backend in ("onedev", "github", "gitlab", "jira"):
        reference = sync.get(backend) if isinstance(sync.get(backend), dict) else {}
        if reference.get("url"):
            return _inline(reference["url"])
    return "planfile://ticket/" + _inline(ticket.get("id"))


def living_status_block(
    ticket: dict[str, Any],
    *,
    state: str,
    actor: str,
    lease_expires_at: str | None,
    urgent: bool = False,
    message: str | None = None,
) -> str:
    lines = [
        LIVING_STATUS_START,
        "### Koru Living Status",
        f"- Ticket: `{_inline(ticket.get('id'))}`",
        f"- State: `{_inline(state)}`",
        f"- Actor: `{_inline(actor)}`",
        f"- Lease expires: `{_inline(lease_expires_at) if lease_expires_at else '-'}`",
        f"- Control: {_control_url(ticket)}",
    ]
    if urgent:
        lines.append("- Triage: `waiting_human_triage` (`sla:urgent`)")
    if message:
        lines.append(f"- Detail: {_inline(message)}")
    lines.append(LIVING_STATUS_END)
    return "\n".join(lines)


def upsert_living_status(description: str, block: str) -> str:
    """Replace the one Koru block while preserving all source prose."""
    source = str(description or "")
    start = source.find(LIVING_STATUS_START)
    end = source.find(LIVING_STATUS_END, start + len(LIVING_STATUS_START))
    if start >= 0 and end >= 0:
        end += len(LIVING_STATUS_END)
        return f"{source[:start].rstrip()}\n\n{block}{source[end:]}".strip()
    return f"{source.rstrip()}\n\n{block}".strip()


def update_living_status(
    project: Path,
    ticket: dict[str, Any],
    *,
    state: str,
    actor: str,
    runner: Callable[[Sequence[str], Path], CommandResult],
    lease_expires_at: str | None = None,
    urgent: bool = False,
    message: str | None = None,
) -> CommandResult:
    """Update canonical Planfile state; remote publication is intentionally separate."""
    from koru.queue.planfile_sdk import planfile_lifecycle_command

    block = living_status_block(
        ticket,
        state=state,
        actor=actor,
        lease_expires_at=lease_expires_at,
        urgent=urgent,
        message=message,
    )
    description = upsert_living_status(str(ticket.get("description") or ""), block)
    return planfile_lifecycle_command(
        project,
        ["ticket", "update", str(ticket["id"]), "--description", description],
        runner=runner,
    )


__all__ = [
    "LIVING_STATUS_END",
    "LIVING_STATUS_START",
    "lease_expiry_text",
    "living_status_block",
    "update_living_status",
    "upsert_living_status",
]
