"""Where a verified patch is allowed to land, and the proof required first.

Promotion is the only phase that makes a change outlive the run, so each mode
here is paired with the check that earns it: a commit on main needs a workspace
that has not moved, a branch needs a worktree that verified, an artifact needs
nothing because it changes nothing.
"""

from __future__ import annotations

import logging
from pathlib import Path

from koru.queue.patch_mode import (
    MANIFEST_NOT_PERSISTED,
    PROMOTION_COMMIT,
    PROMOTION_CONFLICT,
    PROMOTION_FAILED,
    PatchOutcome,
    commit_on_main,
    commit_worktree,
    manifest_drift,
    persisted_manifest_mismatch,
    revert_files,
    write_patch_artifact,
)
from koru.queue.transaction.result import PatchPlan

_logger = logging.getLogger(__name__)


def guard_promotion(plan: PatchPlan, manifest: dict) -> PatchOutcome | None:
    """Refuse to promote onto a workspace that moved during verification."""
    persisted = persisted_manifest_mismatch(plan.project, manifest)
    if persisted:
        return PatchOutcome(
            code=MANIFEST_NOT_PERSISTED,
            message=(
                "the run manifest on disk does not match the frozen plan, so "
                f"promotion was refused ({persisted}). Re-run the ticket."
            ),
        )

    drift = manifest_drift(plan.project, manifest)
    if drift:
        return PatchOutcome(
            code=PROMOTION_CONFLICT,
            message=(
                "the workspace moved while the patch was being verified, so it was "
                f"not promoted ({drift}). Another session most likely edited it; "
                "re-run the ticket against the new state."
            ),
        )
    return None


def deliver_patch_artifact(plan: PatchPlan, manifest: dict) -> Path:
    """Deliver the patch as a reviewable file and change nothing.

    Useful on a shared checkout, and the only mode that needs no verification.
    """
    directory = write_patch_artifact(
        plan.project,
        plan.run_id,
        plan.diff,
        {
            "run_id": plan.run_id,
            "ticket_id": plan.ticket.get("id"),
            "targets": list(plan.targets),
            "verify_command": plan.verify_command,
            "promotion_mode": plan.mode,
            "manifest_hash": manifest["manifest_hash"],
        },
    )
    _logger.info("koru.queue.patch_artifact run_id=%s path=%s", plan.run_id, directory)
    return directory


def commit_on_run_branch(
    plan: PatchPlan,
    staged: Path,
    changed_files: tuple[str, ...],
) -> PatchOutcome | None:
    """Commit a worktree-verified patch onto ``koru/run-<id>``."""
    branch = f"koru/run-{plan.run_id}"
    ok, detail = commit_worktree(staged, branch, _commit_message(plan), changed_files)
    if not ok:
        return PatchOutcome(
            code=PROMOTION_FAILED,
            message=f"verified patch could not be committed to {branch}: {detail}",
        )
    _logger.info("koru.queue.patch_branch branch=%s commit=%s", branch, detail)
    return None


def commit_if_requested(plan: PatchPlan, changed_files: tuple[str, ...]) -> PatchOutcome | None:
    """Commit verified changes on main when ``promotion_mode=commit``."""
    if plan.mode != PROMOTION_COMMIT:
        return None
    ok, detail = commit_on_main(plan.project, _commit_message(plan), changed_files)
    if ok:
        _logger.info("koru.queue.patch_commit run_id=%s commit=%s", plan.run_id, detail)
        return None
    revert_files(plan.project, changed_files)
    return PatchOutcome(
        code=PROMOTION_FAILED,
        message=f"verified patch could not be committed on main: {detail}",
    )


def _commit_message(plan: PatchPlan) -> str:
    return f"koru({plan.ticket_id}): verified patch\n\nrun_id: {plan.run_id}"
