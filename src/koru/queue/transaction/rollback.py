"""Undoing a patch that landed in the workspace but failed its gate.

Only reachable on the unisolated path — when the patch was verified in a
worktree there is nothing in the workspace to undo. Reverse the exact diff;
if that is unsafe or fails, preserve the workspace and report recovery failure.
"""

from __future__ import annotations

from koru.queue.patch_mode import (
    VERIFY_FAILED_ROLLBACK_FAILED,
    VERIFY_FAILED_ROLLED_BACK,
    PatchOutcome,
)
from koru.queue.transaction.result import PatchPlan
from koru.queue.transaction.verification import verify_output
from koru.queue.types import CommandResult
from koru.queue.workspace import reverse_unified_diff


def roll_back_failed_verify(
    plan: PatchPlan,
    changed_files: tuple[str, ...],
    verify: CommandResult,
) -> PatchOutcome:
    """Restore the files the patch touched and explain why."""
    # Keep changed_files in the public call shape; the exact diff, not an index
    # checkout of path names, defines the inverse of this transaction.
    reversed_patch = reverse_unified_diff(plan.project, plan.diff)
    if not reversed_patch.ok:
        return PatchOutcome(
            code=VERIFY_FAILED_ROLLBACK_FAILED,
            message=(
                "verification failed and the patch could not be safely rolled back; "
                f"preserve the workspace and reconcile {', '.join(changed_files)}. "
                f"{reversed_patch.detail}. Verification: {verify_output(verify)}"
            ),
            workspace_left_untouched=False,
            diagnostics=reversed_patch.detail,
        )
    return PatchOutcome(
        code=VERIFY_FAILED_ROLLED_BACK,
        message=(
            "patch applied but verification failed, so it was rolled back. "
            f"`{plan.verify_command}` exited {verify.returncode}: {verify_output(verify)}"
        ),
        workspace_left_untouched=True,
    )
