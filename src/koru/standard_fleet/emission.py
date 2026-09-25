"""Idempotent waiting-input Planfile ticket emission for stale repositories."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from koru.standard_fleet.models import SOURCE_TOOL, StandardCandidate, adoption_dedupe_key
from koru.tasks import create_nl_task


def _ticket_description(candidate: StandardCandidate) -> str:
    blockers: list[str] = []
    if candidate.dirty:
        blockers.append("target primary checkout is dirty")
    if candidate.linked_worktrees:
        blockers.append(f"{candidate.linked_worktrees} linked worktree(s) exist")
    blocker_text = "; ".join(blockers) if blockers else "no local blocker observed"
    return (
        f"Wellmanifest standard update is due for {candidate.identity}.\n\n"
        f"Target checkout: {candidate.path}\n"
        f"Pinned version/revision: {candidate.pinned_version or 'invalid'} / "
        f"{candidate.pinned_revision or 'invalid'}\n"
        f"Available version/revision: {candidate.latest_version} / "
        f"{candidate.latest_revision}\n"
        f"Detected: {', '.join(candidate.reasons)}; {blocker_text}.\n\n"
        "Use one target-owned governance adoption ticket and its canonical "
        "worktree. First re-read AGENTS.md, active tickets, dirty state and "
        "linked worktrees. Run 'goal governance adopt --latest --check' for "
        "evidence, then perform the reviewed adoption only inside that ticket. "
        "Do not reset, overwrite or delete unknown work. Commit, test, PR and "
        "protected Validator merge remain required; this notice grants no "
        "write or merge authority."
    )


def emit_adoption_tickets(
    planfile_project: Path,
    candidates: Sequence[StandardCandidate],
    *,
    create_task: Callable[..., Any] = create_nl_task,
) -> tuple[int, int, tuple[str, ...]]:
    """Emit idempotent waiting-input tickets through the single Planfile writer."""
    emitted = 0
    reused = 0
    errors: list[str] = []
    for candidate in candidates:
        try:
            created = create_task(
                planfile_project,
                _ticket_description(candidate),
                queue_name="governance-handoff",
                priority="high",
                scaffold={
                    "title": (f"[STANDARD-UPDATE] {candidate.identity} -> {candidate.latest_version}"),
                    "labels": ["standard-update", "wellmanifest", "waiting-input"],
                    "source_tool": SOURCE_TOOL,
                    "source_context": {
                        "signal": "wellmanifest_standard_stale",
                        "dedupe_key": adoption_dedupe_key(candidate),
                        "repository": candidate.identity,
                        "target_root": str(candidate.path),
                        "latest_version": candidate.latest_version,
                        "latest_revision": candidate.latest_revision,
                        "authority_required": "target-governance-adoption/v1",
                    },
                    "executor_kind": "human",
                    "executor_mode": "interactive",
                    "execution_state": "waiting_input",
                    "files": [],
                },
            )
        except (OSError, TypeError, ValueError) as exc:
            errors.append(f"{candidate.identity}: {exc}")
            continue
        if getattr(created, "reused", False):
            reused += 1
        else:
            emitted += 1
    return emitted, reused, tuple(errors)
