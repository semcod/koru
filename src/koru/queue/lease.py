"""Ticket execution lease coordination: heartbeat, deadline and takeover.

The lease itself lives on the Planfile ticket's ``execution`` field
(``assigned_to`` + ``lease_expires_at``), so the ticket remains the single
authoritative store and no second lease registry is introduced. This module
adds the ownership rules around that field plus an append-only actor/lease
audit trail:

- **one active lease** — a claim is refused while an unexpired lease is held by
  a different actor, and it is refused again during the grace window that
  follows expiry;
- **heartbeat / renew** — only the current owner may extend the deadline;
- **takeover** — after ``deadline + grace`` a new actor may claim, preserving
  the ticket's history and scope (files, branch and worktree are never reset);
- **release** — only the current owner may clear the lease;
- **restart** — the append-only audit survives a process restart, so a stale
  worker cannot renew a lease that a takeover has already transferred.

Nothing here performs a Planfile mutation. Callers translate the returned
decisions into ``planfile ticket claim/start/done``; the audit log is evidence
only and never grants authority.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

TAKEOVER_GRACE_SECONDS = 600

ACTION_CLAIM = "claim"
ACTION_RENEW = "renew"
ACTION_TAKEOVER = "takeover"
ACTION_RELEASE = "release"


def parse_lease_datetime(value: object) -> datetime | None:
    """Parse a Planfile ``lease_expires_at`` value into a UTC-aware datetime."""
    if not value:
        return None
    text = str(value).strip()
    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def utc_text(value: datetime | None) -> str | None:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z") if value else None


def _execution(ticket: dict[str, Any]) -> dict[str, Any]:
    value = ticket.get("execution")
    return value if isinstance(value, dict) else {}


def lease_deadline(ticket: dict[str, Any]) -> datetime | None:
    """Return the ticket's current lease deadline, if any."""
    return parse_lease_datetime(_execution(ticket).get("lease_expires_at"))


def projected_deadline(lease_seconds: int, *, now: datetime | None = None) -> datetime:
    """Return the deadline a fresh claim/renew would write for ``lease_seconds``."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    return moment + timedelta(seconds=max(0, int(lease_seconds)))


def projected_takeover_at(lease_seconds: int, *, now: datetime | None = None) -> datetime:
    """Return the takeover boundary a fresh claim/renew would project."""
    return projected_deadline(lease_seconds, now=now) + timedelta(seconds=TAKEOVER_GRACE_SECONDS)


def takeover_at(ticket: dict[str, Any]) -> datetime | None:
    """Return the boundary after which a different actor may take the lease over.

    An explicit ``execution.takeover_at`` wins; otherwise the boundary is
    ``lease_expires_at + TAKEOVER_GRACE_SECONDS``.
    """
    execution = _execution(ticket)
    direct = parse_lease_datetime(execution.get("takeover_at"))
    if direct is not None:
        return direct
    deadline = parse_lease_datetime(execution.get("lease_expires_at"))
    return deadline + timedelta(seconds=TAKEOVER_GRACE_SECONDS) if deadline else None


@dataclass(frozen=True)
class LeaseSnapshot:
    assigned_to: str | None
    deadline: datetime | None
    takeover_at: datetime | None
    active: bool
    takeover_eligible: bool


def lease_snapshot(ticket: dict[str, Any], *, now: datetime | None = None) -> LeaseSnapshot:
    """Project the current lease state at ``now``."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    execution = _execution(ticket)
    assigned = execution.get("assigned_to")
    deadline = lease_deadline(ticket)
    boundary = takeover_at(ticket)
    return LeaseSnapshot(
        assigned_to=str(assigned) if assigned else None,
        deadline=deadline,
        takeover_at=boundary,
        active=deadline is not None and moment < deadline,
        takeover_eligible=boundary is not None and moment >= boundary,
    )


@dataclass(frozen=True)
class LeaseDecision:
    ok: bool
    reason: str
    action: str = ACTION_CLAIM


def can_claim(ticket: dict[str, Any], actor: str, *, now: datetime | None = None) -> LeaseDecision:
    """Whether ``actor`` may claim (or renew/takeover) the ticket's lease."""
    snap = lease_snapshot(ticket, now=now)
    if snap.assigned_to is None:
        return LeaseDecision(True, "claim available", ACTION_CLAIM)
    if snap.assigned_to == actor:
        if snap.deadline is None:
            return LeaseDecision(True, "claim available", ACTION_CLAIM)
        return LeaseDecision(True, "renew existing lease", ACTION_RENEW)
    if snap.active:
        return LeaseDecision(
            False,
            f"lease held by {snap.assigned_to} until {utc_text(snap.deadline)}",
        )
    if snap.deadline is None:
        return LeaseDecision(True, "stale assignment, no active lease", ACTION_CLAIM)
    if not snap.takeover_eligible:
        return LeaseDecision(
            False,
            "lease expired but within grace period; takeover not yet eligible",
        )
    return LeaseDecision(True, "takeover after lease expiry and grace period", ACTION_TAKEOVER)


def can_renew(ticket: dict[str, Any], actor: str, *, now: datetime | None = None) -> LeaseDecision:
    """Whether ``actor`` may heartbeat/renew the lease they currently hold."""
    snap = lease_snapshot(ticket, now=now)
    if snap.assigned_to is None:
        return LeaseDecision(False, "no lease to renew")
    if snap.assigned_to != actor:
        return LeaseDecision(False, f"lease held by {snap.assigned_to}")
    return LeaseDecision(True, "renew", ACTION_RENEW)


def can_takeover(ticket: dict[str, Any], actor: str, *, now: datetime | None = None) -> LeaseDecision:
    """Whether ``actor`` may take the lease over from a lapsed owner."""
    snap = lease_snapshot(ticket, now=now)
    if snap.assigned_to == actor:
        return LeaseDecision(False, "already the lease owner; renew instead")
    if not snap.takeover_eligible:
        return LeaseDecision(False, "takeover not yet eligible (deadline + grace)")
    return LeaseDecision(True, "takeover", ACTION_TAKEOVER)


def can_release(ticket: dict[str, Any], actor: str, *, now: datetime | None = None) -> LeaseDecision:
    """Whether ``actor`` may clear the lease they currently hold."""
    snap = lease_snapshot(ticket, now=now)
    if snap.assigned_to and snap.assigned_to != actor:
        return LeaseDecision(False, f"lease held by {snap.assigned_to}")
    return LeaseDecision(True, "release", ACTION_RELEASE)


def _audit_path(project: Path, ticket_id: str) -> Path:
    return project / ".koru" / "leases" / f"{ticket_id.strip()}.jsonl"


def read_lease_audit(project: Path, ticket_id: str) -> list[dict[str, Any]]:
    """Read the append-only lease audit for a ticket, oldest first."""
    records: list[dict[str, Any]] = []
    try:
        lines = _audit_path(project, ticket_id).read_text(encoding="utf-8").splitlines()
    except OSError:
        return records
    for line in lines:
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(item, dict):
            records.append(item)
    return records


def current_generation(project: Path, ticket_id: str) -> int:
    """The latest audit generation (0 when no lease event was ever recorded)."""
    records = read_lease_audit(project, ticket_id)
    if not records:
        return 0
    generations = [int(record.get("generation") or 0) for record in records]
    return max(generations, default=0)


def record_lease_event(
    project: Path,
    ticket_id: str,
    *,
    action: str,
    actor: str,
    deadline: datetime | None = None,
    takeover_boundary: datetime | None = None,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Append one actor/lease transition to the durable audit trail."""
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    path = _audit_path(project, ticket_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with _audit_lock(project, ticket_id):
        record: dict[str, Any] = {
            "generation": current_generation(project, ticket_id) + 1,
            "action": action,
            "actor": actor,
            "at": utc_text(moment),
            "lease_expires_at": utc_text(deadline),
            "takeover_at": utc_text(takeover_boundary),
        }
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, sort_keys=True) + "\n")
    return record


def _audit_lock(project: Path, ticket_id: str):
    """Serialize audit appends so generation stays monotonic across processes."""
    import contextlib
    import os

    @contextlib.contextmanager
    def _noop():
        yield

    if os.name != "posix":
        return _noop()

    import fcntl

    lock_path = _audit_path(project, ticket_id).with_suffix(".lock")
    lock_path.parent.mkdir(parents=True, exist_ok=True)

    @contextlib.contextmanager
    def _locked():
        fd = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o644)
        try:
            fcntl.flock(fd, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(fd, fcntl.LOCK_UN)
            os.close(fd)

    return _locked()


__all__ = [
    "ACTION_CLAIM",
    "ACTION_RENEW",
    "ACTION_RELEASE",
    "ACTION_TAKEOVER",
    "LeaseDecision",
    "LeaseSnapshot",
    "TAKEOVER_GRACE_SECONDS",
    "can_claim",
    "can_release",
    "can_renew",
    "can_takeover",
    "current_generation",
    "lease_deadline",
    "lease_snapshot",
    "parse_lease_datetime",
    "projected_deadline",
    "projected_takeover_at",
    "read_lease_audit",
    "record_lease_event",
    "takeover_at",
    "utc_text",
]
