"""The patch transaction, as a sequence of phases with no logic of its own.

This layer never talks to an LLM. It takes a diff that already exists and
decides — from the workspace state alone — whether it may land. Keeping the
model out of it is what makes the outcome reproducible: the same patch against
the same workspace always resolves the same way, so retry policy can live above
it without muddying the decision.

Every phase either refuses (returning a ``PatchOutcome``) or hands control on,
and every step is journaled as it happens — decisions once, mutations as an
intent/completion pair — so a restart can tell what was underway. Read top to
bottom, the orchestrator *is* the transaction's contract.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from koru.queue.journal import (
    PHASE_APPLIED,
    PHASE_APPLYING,
    PHASE_AUTHORIZED,
    PHASE_COMPLETED,
    PHASE_FROZEN,
    PHASE_PROMOTED,
    PHASE_PROMOTING,
    PHASE_REFUSED,
    PHASE_RESOLVED,
    PHASE_ROLLED_BACK,
    PHASE_STAGED,
    PHASE_STAGING,
    PHASE_STAGING_UNAVAILABLE,
    PHASE_VERIFIED,
    RunJournal,
)
from koru.queue.patch_mode import (
    PATCH_DOES_NOT_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_BRANCH,
    PROMOTION_COMMIT,
    PROMOTION_FAILED,
    VERIFY_PROFILE_INVALID,
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
Authorizer = Callable[[PatchPlan, dict], PatchOutcome | None]


def execute_patch_transaction(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: ShellRunner,
    manifest: dict | None = None,
    authorize: Authorizer | None = None,
) -> PatchTransactionResult:
    """Apply the diff an agent proposed, then verify it, rolling back on failure.

    A patch that fails its ticket's verify command is reverted, so a failed run
    leaves the workspace as it found it.

    Refusals that fire before a plan exists (no diff, symlink screen) are not
    journaled: there is no run identity yet, and nothing was going to change.
    """
    diff, proposal, refusal = extract_patch(result)
    if diff is None:
        return PatchTransactionResult(result, refusal)

    refusal = screen_diff_contents(diff)
    if refusal is not None:
        return PatchTransactionResult(result, refusal)

    plan = build_patch_plan(project, ticket, diff, manifest, proposal=proposal)
    journal = RunJournal(project, plan.run_id)
    journal.append(
        PHASE_RESOLVED,
        data={
            "mode": plan.mode,
            "verify_source": plan.verify_source,
            "isolated": plan.isolated,
            "targets": sorted(plan.targets),
            "proposal_sha256": (proposal or {}).get("proposal_sha256"),
        },
    )
    if plan.verify_error is not None:
        # The ticket asked for a gate that cannot be honoured. Refusing beats
        # every alternative: falling through to a weaker gate would let a typo
        # disable verification, and artifact mode would still record a run
        # whose governance was misconfigured.
        journal.append(PHASE_REFUSED, data={"code": VERIFY_PROFILE_INVALID})
        return PatchTransactionResult(
            result,
            PatchOutcome(code=VERIFY_PROFILE_INVALID, message=plan.verify_error),
            plan=plan,
        )
    freeze = ManifestFreeze(plan, manifest)

    if plan.mode == PROMOTION_ARTIFACT:
        frozen = freeze.freeze()
        journal.append(PHASE_FROZEN, manifest_hash=frozen["manifest_hash"])
        deliver_patch_artifact(plan, frozen)
        journal.append(PHASE_COMPLETED, data={"delivery": "artifact"})
        return PatchTransactionResult(result, None, plan=plan, manifest=freeze.manifest)

    refusal = screen_promotion_preconditions(plan)
    if refusal is not None:
        journal.append(PHASE_REFUSED, data={"code": refusal.code})
        return PatchTransactionResult(result, refusal, plan=plan, manifest=freeze.manifest)

    if plan.mode == PROMOTION_BRANCH and not plan.isolated:
        # Branch promises a verified commit and an untouched shared tree; a run
        # that cannot isolate (no gate to verify with, or no worktree support)
        # cannot keep either promise. Falling back to writing the workspace
        # would be the silent downgrade the mode exists to rule out.
        refusal = PatchOutcome(
            code=PROMOTION_FAILED,
            message=(
                "promotion_mode=branch requires a verify gate and worktree "
                "isolation, and this run has neither a resolvable verify command "
                "nor an isolatable checkout. Name a verify profile (or command), "
                "or explicitly choose promotion_mode=apply for an unverified "
                "local application."
            ),
        )
        journal.append(PHASE_REFUSED, data={"code": refusal.code})
        return PatchTransactionResult(result, refusal, plan=plan, manifest=freeze.manifest)

    run = _run_isolated if plan.isolated else _run_direct
    outcome = run(plan, freeze, shell_runner, journal, authorize=authorize)
    return PatchTransactionResult(result, outcome, plan=plan, manifest=freeze.manifest)


def _authorize(
    plan: PatchPlan,
    frozen: dict,
    journal: RunJournal,
    authorize: Authorizer | None,
) -> PatchOutcome | None:
    """Run the injected authorization against the frozen plan, journaled.

    Called after the freeze because the grant signs the manifest hash — there
    is nothing binding to authorize before the plan is pinned. No authorizer
    means legacy behaviour, and the journal shows no ``authorized`` event, so
    an audit can tell an unauthorized-but-legal run from an authorized one.
    """
    if authorize is None:
        return None
    refusal = authorize(plan, frozen)
    if refusal is not None:
        journal.append(PHASE_REFUSED, data={"code": refusal.code})
        return refusal
    journal.append(PHASE_AUTHORIZED, manifest_hash=frozen.get("manifest_hash"))
    return None


def _run_isolated(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    journal: RunJournal,
    *,
    authorize: Authorizer | None = None,
) -> PatchOutcome | None:
    """Verify in a worktree first; only a proven patch reaches the workspace."""
    frozen = freeze.freeze()
    journal.append(PHASE_FROZEN, manifest_hash=frozen["manifest_hash"])
    refusal = _authorize(plan, frozen, journal, authorize)
    if refusal is not None:
        return refusal

    journal.append(PHASE_STAGING, data={"mode": plan.mode})
    staged = stage_patch(plan, shell_runner)
    if not staged.isolated:
        journal.append(PHASE_STAGING_UNAVAILABLE)
        return _without_isolation(plan, freeze, shell_runner, journal)
    if staged.outcome is not None:
        journal.append(PHASE_REFUSED, data={"code": staged.outcome.code})
        return staged.outcome
    if plan.mode == PROMOTION_BRANCH:
        # The verified result already lives on its own ref; deliberately nothing
        # is written to the shared working tree. The branch commit happened
        # under the ``staging`` intent, so ``staged`` closes it and ``promoted``
        # records where the result now lives.
        journal.append(PHASE_STAGED, data={"verified": True})
        journal.append(PHASE_PROMOTED, data={"branch": f"koru/run-{plan.run_id}"})
        return None
    journal.append(PHASE_STAGED, data={"verified": True})

    conflict = guard_promotion(plan, frozen)
    if conflict is not None:
        journal.append(PHASE_REFUSED, data={"code": conflict.code})
        return conflict
    # Already verified in isolation — re-running the gate here would only
    # re-prove it against a workspace the manifest just confirmed unchanged.
    return _apply_to_workspace(plan, freeze, shell_runner, journal, verify=False)


def _without_isolation(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    journal: RunJournal,
) -> PatchOutcome | None:
    """Decide what a patch that could not be staged is still allowed to do.

    Reached on a read-only checkout, where no worktree can be created. Branch
    promotion is then impossible to honour — its whole promise is that the
    shared tree is never written to — so it is refused rather than quietly
    downgraded. The other modes fall back to patching in place, which brings
    its own dirty-file guard and runs the gate in the workspace itself.
    """
    if plan.mode == PROMOTION_BRANCH:
        journal.append(PHASE_REFUSED, data={"code": PROMOTION_FAILED})
        return PatchOutcome(
            code=PROMOTION_FAILED,
            message=(
                "promotion_mode=branch needs a staging worktree to commit into, and "
                "one could not be created here — a read-only checkout is the usual "
                "reason. Nothing was applied. Re-run with promotion_mode=apply to "
                "patch the workspace directly, or from a writable checkout."
            ),
        )
    # The isolated path already journaled `frozen`; re-announcing it here
    # would forge a second freeze that never happened.
    return _run_direct(plan, freeze, shell_runner, journal, frozen_journaled=True)


def _run_direct(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    journal: RunJournal,
    *,
    frozen_journaled: bool = False,
    authorize: Authorizer | None = None,
) -> PatchOutcome | None:
    """Patch the workspace in place, with ``git checkout --`` as the only undo."""
    refusal = screen_direct_apply(plan)
    if refusal is not None:
        journal.append(PHASE_REFUSED, data={"code": refusal.code})
        return refusal
    frozen = freeze.freeze()
    if not frozen_journaled:
        journal.append(PHASE_FROZEN, manifest_hash=frozen["manifest_hash"])
        refusal = _authorize(plan, frozen, journal, authorize)
        if refusal is not None:
            return refusal
    return _apply_to_workspace(
        plan, freeze, shell_runner, journal, verify=bool(plan.verify_command),
    )


def _apply_to_workspace(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    journal: RunJournal,
    *,
    verify: bool,
) -> PatchOutcome | None:
    """Write the patch into the real tree, gate it if asked, then promote."""
    freeze.freeze()

    journal.append(PHASE_APPLYING)
    applied = apply_unified_diff(plan.project, plan.diff)
    if not applied.ok:
        journal.append(PHASE_REFUSED, data={"code": PATCH_DOES_NOT_APPLY})
        return PatchOutcome(
            code=PATCH_DOES_NOT_APPLY,
            message=applied.detail,
            retryable=True,
            diagnostics=applied.detail,
        )
    journal.append(PHASE_APPLIED, data={"changed_files": sorted(applied.changed_files)})

    if verify:
        gate = shell_runner(plan.verify_command, plan.project)
        if gate.returncode != 0:
            outcome = roll_back_failed_verify(plan, applied.changed_files, gate)
            journal.append(PHASE_ROLLED_BACK, data={"code": outcome.code})
            return outcome
        journal.append(PHASE_VERIFIED)

    if plan.mode != PROMOTION_COMMIT:
        return None
    journal.append(PHASE_PROMOTING, data={"mode": plan.mode})
    outcome = commit_if_requested(plan, applied.changed_files)
    if outcome is not None:
        journal.append(PHASE_ROLLED_BACK, data={"code": outcome.code})
        return outcome
    journal.append(PHASE_PROMOTED, data={"mode": plan.mode})
    return None
