"""The patch transaction, as a sequence of phases with no logic of its own.

This layer never talks to an LLM. It takes a diff that already exists and
decides — from the workspace state alone — whether it may land. Keeping the
model out of it is what makes the outcome reproducible: the same patch against
the same workspace always resolves the same way, so retry policy can live above
it without muddying the decision.

Every phase either refuses (returning a ``PatchOutcome``) or hands control on.
Read top to bottom, the orchestrator *is* the transaction's contract.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from koru.queue.patch_mode import (
    PATCH_DOES_NOT_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_BRANCH,
    PROMOTION_FAILED,
    PatchOutcome,
    apply_unified_diff,
)
from koru.queue.transaction.preflight import (
    ManifestFreeze,
    build_patch_plan,
    extract_patch,
    screen_diff_contents,
    screen_direct_apply,
    screen_promotion_preconditions,
)
from koru.queue.transaction.promotion import (
    commit_if_requested,
    deliver_patch_artifact,
    guard_promotion,
)
from koru.queue.transaction.result import PatchPlan, PatchTransactionResult
from koru.queue.transaction.rollback import roll_back_failed_verify
from koru.queue.transaction.staging import stage_patch
from koru.queue.types import CommandResult

ShellRunner = Callable[[str, Path], CommandResult]


def execute_patch_transaction(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: ShellRunner,
    manifest: dict | None = None,
) -> PatchTransactionResult:
    """Apply the diff an agent proposed, then verify it, rolling back on failure.

    A patch that fails its ticket's verify command is reverted, so a failed run
    leaves the workspace as it found it.
    """
    diff, refusal = extract_patch(result)
    if diff is None:
        return PatchTransactionResult(result, refusal)

    refusal = screen_diff_contents(diff)
    if refusal is not None:
        return PatchTransactionResult(result, refusal)

    plan = build_patch_plan(project, ticket, diff, manifest)
    freeze = ManifestFreeze(plan, manifest)

    if plan.mode == PROMOTION_ARTIFACT:
        deliver_patch_artifact(plan, freeze.freeze())
        return PatchTransactionResult(result, None)

    refusal = screen_promotion_preconditions(plan)
    if refusal is not None:
        return PatchTransactionResult(result, refusal)

    run = _run_isolated if plan.isolated else _run_direct
    return PatchTransactionResult(result, run(plan, freeze, shell_runner))


def _run_isolated(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
) -> PatchOutcome | None:
    """Verify in a worktree first; only a proven patch reaches the workspace."""
    frozen = freeze.freeze()

    staged = stage_patch(plan, shell_runner)
    if not staged.isolated:
        return _without_isolation(plan, freeze, shell_runner)
    if staged.outcome is not None:
        return staged.outcome
    if plan.mode == PROMOTION_BRANCH:
        # The verified result already lives on its own ref; deliberately nothing
        # is written to the shared working tree.
        return None

    conflict = guard_promotion(plan, frozen)
    if conflict is not None:
        return conflict
    # Already verified in isolation — re-running the gate here would only
    # re-prove it against a workspace the manifest just confirmed unchanged.
    return _apply_to_workspace(plan, freeze, shell_runner, verify=False)


def _without_isolation(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
) -> PatchOutcome | None:
    """Decide what a patch that could not be staged is still allowed to do.

    Reached on a read-only checkout, where no worktree can be created. Branch
    promotion is then impossible to honour — its whole promise is that the
    shared tree is never written to — so it is refused rather than quietly
    downgraded. The other modes fall back to patching in place, which brings
    its own dirty-file guard and runs the gate in the workspace itself.
    """
    if plan.mode == PROMOTION_BRANCH:
        return PatchOutcome(
            code=PROMOTION_FAILED,
            message=(
                "promotion_mode=branch needs a staging worktree to commit into, and "
                "one could not be created here — a read-only checkout is the usual "
                "reason. Nothing was applied. Re-run with promotion_mode=apply to "
                "patch the workspace directly, or from a writable checkout."
            ),
        )
    return _run_direct(plan, freeze, shell_runner)


def _run_direct(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
) -> PatchOutcome | None:
    """Patch the workspace in place, with ``git checkout --`` as the only undo."""
    refusal = screen_direct_apply(plan)
    if refusal is not None:
        return refusal
    return _apply_to_workspace(plan, freeze, shell_runner, verify=bool(plan.verify_command))


def _apply_to_workspace(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    *,
    verify: bool,
) -> PatchOutcome | None:
    """Write the patch into the real tree, gate it if asked, then promote."""
    freeze.freeze()

    applied = apply_unified_diff(plan.project, plan.diff)
    if not applied.ok:
        return PatchOutcome(
            code=PATCH_DOES_NOT_APPLY,
            message=applied.detail,
            retryable=True,
            diagnostics=applied.detail,
        )

    if verify:
        gate = shell_runner(plan.verify_command, plan.project)
        if gate.returncode != 0:
            return roll_back_failed_verify(plan, applied.changed_files, gate)

    return commit_if_requested(plan, applied.changed_files)
