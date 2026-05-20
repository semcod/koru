"""koru queue clean — sweep stale test fixtures out of the planfile queue.

Test sessions accumulate fixture tickets (``test-only``, ``dryrun``,
``synthetic`` …). Without housekeeping they pile up, distract the agent
on every ``koru --context`` call, and gradually erode trust in the
queue. ``koru queue clean`` is the safe, auditable broom.

Safety contract
---------------
1. **Dry-run by default.** No ticket is mutated unless ``--apply`` is
   passed. The dry-run output is the list a human would otherwise
   produce by hand — it must be possible to read it and predict
   exactly what ``--apply`` will do.
2. **Active work is sacred.** Tickets with status ``in_progress`` or
   ``waiting_input`` are never touched unless the operator explicitly
   passes ``--include-active``. Default cleanup considers only
   ``open`` and ``ready`` tickets.
3. **Every closure leaves an audit trail.** Each completed ticket
   receives a single ``KORU-QUEUE-CLEAN`` note carrying the reason and
   matched rules — same parseable shape as ``KORU-GATE-AUTH`` so the
   audit-trail tooling can reuse the existing parser style.

Detection rules
---------------
A ticket is a cleanup candidate when **any** of the following holds:

* its ``labels`` intersect :data:`koru.context.FIXTURE_LABELS`
  (``test-only``, ``dryrun``, ``dry-run``, ``synthetic``, ``auto-close``);
* ``--include-names`` is enabled and the ticket name matches
  :data:`FIXTURE_NAME_PATTERN` (``Test …`` / ``TEST: …``);
* ``--max-age-days N`` is set and the ticket has been open longer than
  that many days (combined with the above — never a sole criterion).
"""


import json
import os
import re
import shlex
import subprocess
import sys
from collections.abc import Callable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from koru.context import FIXTURE_LABELS

QUEUE_CLEAN_TAG = "KORU-QUEUE-CLEAN"
"""Marker prefix written to ``outputs.notes`` on every cleaned ticket."""

FIXTURE_NAME_PATTERN = re.compile(r"^(test\b|TEST:)", re.IGNORECASE)
"""Conservative heuristic: only clearly-prefixed test/fixture names match."""

CLEANABLE_STATUSES_DEFAULT: frozenset[str] = frozenset({"open", "ready"})
ACTIVE_STATUSES: frozenset[str] = frozenset({"in_progress", "waiting_input"})


@dataclass(frozen=True)
class CleanupCandidate:
    """A planfile ticket selected for cleanup, with the reasons why."""

    ticket_id: str
    name: str
    status: str
    labels: tuple[str, ...]
    age_days: float | None
    matched_rules: tuple[str, ...]

    def explanation(self) -> str:
        """Human-readable one-liner used in dry-run output and notes."""
        rules = ", ".join(self.matched_rules) or "no-rule"
        age = f"{self.age_days:.1f}d" if self.age_days is not None else "?d"
        return f"{self.ticket_id} [{self.status}, {age}] — {rules}"


@dataclass
class CleanupReport:
    """Outcome of a (dry-run or applied) sweep."""

    candidates: list[CleanupCandidate] = field(default_factory=list)
    applied: list[str] = field(default_factory=list)
    failed: list[tuple[str, str]] = field(default_factory=list)
    skipped_active: list[str] = field(default_factory=list)
    dry_run: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "dry_run": self.dry_run,
            "candidate_count": len(self.candidates),
            "applied_count": len(self.applied),
            "failed_count": len(self.failed),
            "skipped_active_count": len(self.skipped_active),
            "candidates": [
                {
                    "ticket_id": c.ticket_id,
                    "name": c.name,
                    "status": c.status,
                    "labels": list(c.labels),
                    "age_days": c.age_days,
                    "matched_rules": list(c.matched_rules),
                }
                for c in self.candidates
            ],
            "applied": list(self.applied),
            "failed": [{"ticket_id": tid, "error": err} for tid, err in self.failed],
            "skipped_active": list(self.skipped_active),
        }


def _planfile_base() -> list[str]:
    """Resolve the planfile CLI invocation prefix (mirrors gate.py)."""
    configured = os.environ.get("KORU_PLANFILE_CMD")
    if configured:
        return shlex.split(configured)
    try:
        from importlib.util import find_spec

        if find_spec("planfile") is not None:
            return [sys.executable, "-m", "planfile.cli"]
    except Exception:  # pragma: no cover
        pass
    return ["planfile"]


def _parse_age_days(ticket: dict[str, Any], *, now: datetime | None = None) -> float | None:
    """Best-effort parse of a ticket's age in days from ``created_at``."""
    raw = ticket.get("created_at") or ticket.get("created")
    if not raw:
        return None
    try:
        # Pydantic emits ISO-8601; tolerate trailing 'Z'.
        if isinstance(raw, str) and raw.endswith("Z"):
            raw = raw[:-1] + "+00:00"
        created = datetime.fromisoformat(str(raw))
    except (TypeError, ValueError):
        return None
    if created.tzinfo is None:
        created = created.replace(tzinfo=UTC)
    reference = now or datetime.now(UTC)
    delta = reference - created
    return max(delta.total_seconds() / 86_400.0, 0.0)


def _matched_rules(
    ticket: dict[str, Any],
    *,
    include_names: bool,
    max_age_days: float | None,
    age_days: float | None,
) -> tuple[str, ...]:
    """Return the rule names that consider this ticket a cleanup target."""
    rules: list[str] = []
    labels = ticket.get("labels") or []
    label_set = {str(x).strip().lower() for x in labels} if isinstance(labels, list) else set()
    label_hits = label_set & FIXTURE_LABELS
    if label_hits:
        rules.append(f"fixture-label({','.join(sorted(label_hits))})")

    if include_names:
        name = ticket.get("name") or ""
        if isinstance(name, str) and FIXTURE_NAME_PATTERN.match(name.strip()):
            rules.append("fixture-name")

    age_rule: str | None = None
    if max_age_days is not None and age_days is not None and age_days >= max_age_days:
        age_rule = f"age>={max_age_days:g}d"
        rules.append(age_rule)

    # Age alone never qualifies — it's a *modifier* on top of label/name match.
    # If only the age rule fires, drop it: better to leave the ticket alone.
    if age_rule is not None and rules == [age_rule]:
        return ()
    return tuple(rules)


def _cleanable_statuses(*, include_active: bool) -> frozenset[str]:
    return CLEANABLE_STATUSES_DEFAULT | (ACTIVE_STATUSES if include_active else frozenset())


def _maybe_skip_active_ticket(
    ticket: dict[str, Any],
    ticket_id: str,
    status: str,
    *,
    include_names: bool,
    include_active: bool,
    max_age_days: float | None,
    now: datetime | None,
) -> bool:
    """Return True when an active ticket would match but is protected."""
    if status in ACTIVE_STATUSES and not include_active:
        age = _parse_age_days(ticket, now=now)
        rules = _matched_rules(
            ticket,
            include_names=include_names,
            max_age_days=max_age_days,
            age_days=age,
        )
        return bool(rules)
    return False


def _candidate_from_ticket(
    ticket: dict[str, Any],
    ticket_id: str,
    status: str,
    *,
    include_names: bool,
    max_age_days: float | None,
    now: datetime | None,
) -> CleanupCandidate | None:
    age_days = _parse_age_days(ticket, now=now)
    rules = _matched_rules(
        ticket,
        include_names=include_names,
        max_age_days=max_age_days,
        age_days=age_days,
    )
    if not rules:
        return None
    labels = ticket.get("labels") or []
    return CleanupCandidate(
        ticket_id=ticket_id,
        name=str(ticket.get("name") or ""),
        status=status,
        labels=tuple(str(x) for x in (labels if isinstance(labels, list) else [])),
        age_days=age_days,
        matched_rules=rules,
    )


def find_candidates(
    tickets: Sequence[dict[str, Any]],
    *,
    include_names: bool = False,
    include_active: bool = False,
    max_age_days: float | None = None,
    now: datetime | None = None,
) -> tuple[list[CleanupCandidate], list[str]]:
    """Inspect a ticket list and return ``(candidates, skipped_active_ids)``.

    Pure function — no I/O, no mutation. The caller decides whether to
    actually close anything. The split between *candidates* and
    *skipped_active* lets the CLI surface "would have cleaned but
    you're working on it — pass --include-active to override."
    """
    cleanable_statuses = _cleanable_statuses(include_active=include_active)
    candidates: list[CleanupCandidate] = []
    skipped_active: list[str] = []
    for ticket in tickets:
        ticket_id = str(ticket.get("id") or "")
        if not ticket_id:
            continue
        status = str(ticket.get("status") or "").lower()
        if status not in cleanable_statuses:
            if _maybe_skip_active_ticket(
                ticket,
                ticket_id,
                status,
                include_names=include_names,
                include_active=include_active,
                max_age_days=max_age_days,
                now=now,
            ):
                skipped_active.append(ticket_id)
            continue
        candidate = _candidate_from_ticket(
            ticket,
            ticket_id,
            status,
            include_names=include_names,
            max_age_days=max_age_days,
            now=now,
        )
        if candidate is not None:
            candidates.append(candidate)
    return candidates, skipped_active


def _build_close_note(candidate: CleanupCandidate, reason: str) -> str:
    payload = {
        "kind": "queue_cleanup",
        "rules": list(candidate.matched_rules),
        "reason": reason,
        "cleaned_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    return f"{QUEUE_CLEAN_TAG} {json.dumps(payload, sort_keys=True)}"


def _list_tickets(
    project: Path,
    runner: Callable[..., Any],
) -> list[dict[str, Any]]:
    """Fetch all tickets via ``planfile ticket list --format json``."""
    cmd = [*_planfile_base(), "ticket", "list", "--format", "json"]
    result = runner(cmd, cwd=str(project), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            f"planfile ticket list failed (exit {result.returncode}): "
            f"{(result.stderr or result.stdout or '').strip()}",
        )
    stdout = (result.stdout or "").strip()
    if not stdout:
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"planfile ticket list returned invalid JSON: {exc}") from exc
    if isinstance(data, list):
        return [t for t in data if isinstance(t, dict)]
    if isinstance(data, dict):
        return [data]
    return []


def _close_ticket(
    project: Path,
    candidate: CleanupCandidate,
    reason: str,
    runner: Callable[..., Any],
) -> None:
    note = _build_close_note(candidate, reason)
    cmd = [
        *_planfile_base(),
        "ticket",
        "complete",
        candidate.ticket_id,
        "--note",
        note,
    ]
    result = runner(cmd, cwd=str(project), capture_output=True, text=True, check=False)
    if result.returncode != 0:
        raise RuntimeError(
            (result.stderr or result.stdout or "").strip() or f"exit {result.returncode}",
        )


def clean_queue(
    project: Path,
    *,
    include_names: bool = False,
    include_active: bool = False,
    max_age_days: float | None = None,
    apply: bool = False,
    reason: str = "swept by koru queue clean",
    runner: Callable[..., Any] | None = None,
    now: datetime | None = None,
) -> CleanupReport:
    """End-to-end: list, classify, optionally close fixture tickets.

    Returns a :class:`CleanupReport` so callers (CLI, tests, future
    automation) can decide what to print or surface.
    """
    run = runner or subprocess.run
    tickets = _list_tickets(project, run)
    candidates, skipped_active = find_candidates(
        tickets,
        include_names=include_names,
        include_active=include_active,
        max_age_days=max_age_days,
        now=now,
    )
    report = CleanupReport(
        candidates=candidates,
        skipped_active=skipped_active,
        dry_run=not apply,
    )
    if not apply:
        return report

    for candidate in candidates:
        try:
            _close_ticket(project, candidate, reason, run)
            report.applied.append(candidate.ticket_id)
        except RuntimeError as exc:
            report.failed.append((candidate.ticket_id, str(exc)))
    return report


__all__ = [
    "ACTIVE_STATUSES",
    "CLEANABLE_STATUSES_DEFAULT",
    "CleanupCandidate",
    "CleanupReport",
    "FIXTURE_NAME_PATTERN",
    "QUEUE_CLEAN_TAG",
    "clean_queue",
    "find_candidates",
]
