"""Proving a patch in a throwaway worktree before it touches the workspace.

Nothing reaches the real tree until the patch has both applied and passed its
gate in isolation, so a bad patch — or one racing another agent's edits — costs
a discarded directory rather than a broken workspace.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from koru.queue.patch_mode import (
    PATCH_DOES_NOT_APPLY,
    PROMOTION_BRANCH,
    VERIFY_BASELINE_FAILED,
    VERIFY_FAILED_ISOLATED,
    PatchOutcome,
    apply_unified_diff,
    staging_worktree,
)
from koru.queue.transaction.promotion import commit_on_run_branch
from koru.queue.transaction.result import PatchPlan
from koru.queue.transaction.verification import (
    BASELINE_OUTPUT_LIMIT,
    run_verify,
    skip_verify_baseline,
    verify_output,
)
from koru.queue.types import CommandResult


def stage_patch(
    plan: PatchPlan,
    shell_runner: Callable[[str, Path], CommandResult],
) -> PatchOutcome | None:
    """Apply and verify the patch in isolation; ``None`` means it may proceed.

    Under ``promotion_mode=branch`` the verified result is committed here and
    the branch ref outlives the worktree, so the shared tree is never written to.
    """
    with staging_worktree(plan.project, plan.targets) as staged:
        if staged is None:
            return None  # cannot isolate; the caller's dirty check still guards us

        baseline = _record_baseline(plan, staged, shell_runner)

        applied = apply_unified_diff(staged, plan.diff)
        if not applied.ok:
            return PatchOutcome(
                code=PATCH_DOES_NOT_APPLY,
                message=applied.detail,
                retryable=True,
                diagnostics=applied.detail,
            )

        verify = run_verify(shell_runner, plan.verify_command, staged)
        if verify.returncode != 0:
            return _staged_verify_failure(plan, baseline, verify)

        if plan.mode == PROMOTION_BRANCH:
            return commit_on_run_branch(plan, staged, applied.changed_files)
        return None


class _Baseline:
    """Whether the gate passed *before* the patch existed, and what it said."""

    def __init__(self, *, ok: bool = True, output: str = "") -> None:
        self.ok = ok
        self.output = output


def _record_baseline(
    plan: PatchPlan,
    staged: Path,
    shell_runner: Callable[[str, Path], CommandResult],
) -> _Baseline:
    """Run the gate on the unpatched worktree, but do not decide on it yet.

    A red baseline means two very different things: a suite that cannot run here
    at all (fixtures resolved outside the repo), or code that is broken precisely
    because this ticket is the repair. Only the post-patch result tells them
    apart — red→green is a fix.
    """
    if skip_verify_baseline(plan.ticket):
        return _Baseline()
    result = run_verify(shell_runner, plan.verify_command, staged)
    if result.returncode == 0:
        return _Baseline()
    return _Baseline(ok=False, output=verify_output(result, limit=BASELINE_OUTPUT_LIMIT))


def _staged_verify_failure(
    plan: PatchPlan,
    baseline: _Baseline,
    verify: CommandResult,
) -> PatchOutcome:
    """Explain a gate that failed in isolation, in the light of the baseline."""
    output = verify_output(verify)
    if baseline.ok:
        return PatchOutcome(
            code=VERIFY_FAILED_ISOLATED,
            message=(
                "patch failed verification in an isolated worktree, so the workspace "
                f"was left untouched. `{plan.verify_command}` exited "
                f"{verify.returncode}: {output}"
            ),
        )
    # Red before, red after: the patch is not what made it fail, so the agent
    # cannot be judged on this and re-asking will not help.
    return PatchOutcome(
        code=VERIFY_BASELINE_FAILED,
        message=(
            f"`{plan.verify_command}` already failed in a clean worktree before the "
            "patch and still fails after it, so the patch could not be judged "
            "there and nothing was promoted. Either the suite depends on paths "
            "outside the repository — re-run with KORU_QUEUE_WORKTREE=0 to verify "
            "in the checkout itself — or the patch does not fix the reported "
            f"defect. Before: {baseline.output} After: {output}"
        ),
    )
