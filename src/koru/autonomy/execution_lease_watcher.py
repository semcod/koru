"""Bounded Planfile lease-expiry notices for autonomous queue hygiene.

This is a compatibility adapter for Planfile's existing ``lease_expires_at``
field. It emits an informational handoff ticket after the one-hour lease and
ten-minute grace period; it never treats that ticket as takeover authority.
The replacement agent still needs an authoritative controller takeover receipt
with the current generation and fencing values before writing a worktree.
"""

from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import yaml

from koru.queue.planfile_sdk import planfile_lifecycle_command
from koru.queue.types import CommandResult
from koru.tasks import create_nl_task

TAKEOVER_GRACE_SECONDS = 600
TAKEOVER_NOTICE_SOURCE = "koru-execution-lease-watcher"
TAKEOVER_NOTICE_SIGNAL = "execution_lease_takeover"
TAKEOVER_NOTICE_DEDUPE_PREFIX = "koru:execution-lease-takeover:"


def _parse_datetime(value: object) -> datetime | None:
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


def _utc_text(value: datetime) -> str:
    return value.astimezone(UTC).isoformat().replace("+00:00", "Z")


def _execution(ticket: dict[str, Any]) -> dict[str, Any]:
    value = ticket.get("execution")
    return value if isinstance(value, dict) else {}


def takeover_at(ticket: dict[str, Any]) -> datetime | None:
    """Return the takeover boundary projected by the ticket lease."""
    execution = _execution(ticket)
    direct = _parse_datetime(execution.get("takeover_at"))
    if direct is not None:
        return direct
    expires = _parse_datetime(execution.get("lease_expires_at"))
    return expires + timedelta(seconds=TAKEOVER_GRACE_SECONDS) if expires else None


def _notice_context(ticket: dict[str, Any]) -> dict[str, Any] | None:
    source = ticket.get("source")
    context = source.get("context") if isinstance(source, dict) else None
    if not isinstance(context, dict):
        return None
    if source.get("tool") != TAKEOVER_NOTICE_SOURCE:
        return None
    return context if context.get("signal") == TAKEOVER_NOTICE_SIGNAL else None


def _current_tickets(project: Path) -> list[dict[str, Any]]:
    path = project / ".planfile" / "sprints" / "current.yaml"
    try:
        payload = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    except (OSError, yaml.YAMLError):
        return []
    sprint = payload.get("sprint") if isinstance(payload, dict) else None
    tickets = sprint.get("tickets") if isinstance(sprint, dict) else None
    if isinstance(tickets, dict):
        return [item for item in tickets.values() if isinstance(item, dict)]
    if isinstance(tickets, list):
        return [item for item in tickets if isinstance(item, dict)]
    return []


def _notice_description(ticket: dict[str, Any], boundary: datetime) -> str:
    execution = _execution(ticket)
    expires = _parse_datetime(execution.get("lease_expires_at"))
    assigned = str(execution.get("assigned_to") or "unknown")
    target_id = str(ticket.get("id") or "unknown")
    return (
        f"Planfile ticket {target_id} has an observed execution lease.\n\n"
        f"Lease expires: {_utc_text(expires) if expires else 'unknown'}\n"
        f"Takeover eligible at: {_utc_text(boundary)}\n"
        f"Current actor: {assigned}\n\n"
        "This is an informational handoff signal, not write authority. Before "
        "editing the target worktree, obtain a fresh authoritative takeover "
        "receipt with the exact lease id, generation and fencing values. Re-read "
        "the branch, HEAD and dirty state; do not reset or overwrite unknown work."
    )


def _notice_scaffold(ticket: dict[str, Any], boundary: datetime) -> dict[str, Any]:
    target_id = str(ticket.get("id") or "unknown")
    dedupe_key = f"{TAKEOVER_NOTICE_DEDUPE_PREFIX}{target_id}"
    execution = _execution(ticket)
    source_context = {
        "signal": TAKEOVER_NOTICE_SIGNAL,
        "dedupe_key": dedupe_key,
        "target_ticket_id": target_id,
        "takeover_at": _utc_text(boundary),
        "lease_expires_at": str(execution.get("lease_expires_at") or ""),
        "authority_required": "wellmanifest.ticket-execution-lease/v1",
    }
    return {
        "title": f"[LEASE-TAKEOVER] {target_id} may be reclaimed",
        "labels": ["lease-takeover", "handoff", "waiting-input"],
        "source_tool": TAKEOVER_NOTICE_SOURCE,
        "source_context": source_context,
        "executor_kind": "human",
        "executor_mode": "interactive",
        "execution_state": "waiting_input",
        "files": [],
    }


def _update_notice(
    project: Path,
    notice: dict[str, Any],
    description: str,
    *,
    runner: Callable[[Sequence[str], Path], CommandResult],
) -> bool:
    notice_id = str(notice.get("id") or "").strip()
    if not notice_id:
        return False
    result = runner(
        ["planfile", "ticket", "update", notice_id, "--description", description],
        project,
    )
    return result.returncode == 0


def _finish_notice(
    project: Path,
    notice: dict[str, Any],
    *,
    reason: str,
    runner: Callable[[Sequence[str], Path], CommandResult],
) -> bool:
    notice_id = str(notice.get("id") or "").strip()
    if not notice_id:
        return False
    result = planfile_lifecycle_command(
        project,
        ["ticket", "done", notice_id, "--note", reason, "--actor", "koru"],
        runner=runner,
    )
    return result.returncode == 0


def emit_takeover_notices(
    project: Path,
    *,
    now: datetime | None = None,
    runner: Callable[[Sequence[str], Path], CommandResult],
    create_task: Callable[..., Any] = create_nl_task,
) -> int:
    """Create or refresh one non-runnable notice per target ticket.

    The return value counts newly emitted or refreshed notices. Existing
    notices use a stable dedupe key, so repeated autonomous cycles are safe.
    """
    moment = (now or datetime.now(UTC)).astimezone(UTC)
    tickets = _current_tickets(project)
    targets = {
        str(ticket.get("id") or ""): ticket
        for ticket in tickets
        if str(ticket.get("status") or "").lower() == "in_progress"
    }
    notices = {
        str(context.get("target_ticket_id")): notice
        for notice in tickets
        if (context := _notice_context(notice)) is not None
        and str(notice.get("status") or "").lower() not in {"done", "canceled", "cancelled"}
    }
    changed = 0

    for target_id, target in targets.items():
        boundary = takeover_at(target)
        if boundary is None:
            continue
        notice = notices.get(target_id)
        if moment < boundary:
            if notice is not None:
                reason = f"Lease renewed for {target_id}; takeover notice resolved."
                if _finish_notice(project, notice, reason=reason, runner=runner):
                    changed += 1
            continue

        description = _notice_description(target, boundary)
        if notice is not None:
            if _update_notice(project, notice, description, runner=runner):
                changed += 1
            continue
        try:
            create_task(
                project,
                description,
                queue_name="handoff",
                priority="high",
                scaffold=_notice_scaffold(target, boundary),
            )
        except (OSError, TypeError, ValueError):
            continue
        changed += 1
    return changed


__all__ = ["TAKEOVER_GRACE_SECONDS", "emit_takeover_notices", "takeover_at"]
