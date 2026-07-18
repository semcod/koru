"""Undoing a patch that landed in the workspace but failed its gate.

Only reachable on the unisolated path — when the patch was verified in a
worktree there is nothing in the workspace to undo. A failed run must leave the
tree exactly as it found it, so the revert happens before the outcome is built.
"""

from __future__ import annotations

from koru.queue.patch_mode import (
    VERIFY_FAILED_ROLLED_BACK,
    PatchOutcome,
    revert_files,
)
from koru.queue.transaction.result import PatchPlan
from koru.queue.transaction.verification import verify_output
from koru.queue.types import CommandResult


def roll_back_failed_verify(
    plan: PatchPlan,
    changed_files: tuple[str, ...],
    verify: CommandResult,
) -> PatchOutcome:
    """Restore the files the patch touched and explain why."""
    revert_files(plan.project, changed_files)
    return PatchOutcome(
        code=VERIFY_FAILED_ROLLED_BACK,
        message=(
            "patch applied but verification failed, so it was rolled back. "
            f"`{plan.verify_command}` exited {verify.returncode}: {verify_output(verify)}"
        ),
        workspace_left_untouched=True,
    )
