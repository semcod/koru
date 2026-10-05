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
from types import SimpleNamespace
from typing import NamedTuple

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
    promotion_mode,
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
from koru.queue.workspace import StagingAdmissionRequired, require_unmanaged_patch_workspace

ShellRunner = Callable[[str, Path], CommandResult]
Authorizer = Callable[[PatchPlan, dict], PatchOutcome | None]


class _ScreenedPatch(NamedTuple):
    """What survived the two screens that run before any plan exists."""

    diff: str | None
    proposal: dict | None
    refusal: PatchOutcome | None


def execute_patch_transaction(
    project: Path,
    result: CommandResult,
    ticket: dict,
    shell_runner: ShellRunner,
    manifest: dict | None = None,
    authorize: Authorizer | None = None,
) -> PatchTransactionResult:
    """Apply the diff an agent proposed, then verify it, rolling back on failure.

    A patch that fails its ticket's verify command is reversed when safe.
    A failed reversal is reported explicitly and requires reconciliation.

    Refusals that fire before a plan exists (no diff, symlink screen) are not
    journaled: there is no run identity yet, and nothing was going to change.
    """
    screened = _screen_before_plan(result)
    if screened.diff is None or screened.refusal is not None:
        return PatchTransactionResult(result, screened.refusal)

    # An arbitrary local authorizer, an isolation opt-out or a promotion flag
    # cannot grant protected repository admission. Artifact delivery proposes
    # a patch without applying it and remains available on governed projects.
    if promotion_mode(ticket) != PROMOTION_ARTIFACT:
        refusal = _workspace_admission_refusal(project)
        if refusal is not None:
            return PatchTransactionResult(result, refusal)

    plan = build_patch_plan(
        project,
        ticket,
        screened.diff,
        manifest,
        proposal=screened.proposal,
    )
    journal = _open_run_journal(project, plan, screened.proposal)
    if plan.verify_error is not None:
        # The ticket asked for a gate that cannot be honoured. Refusing beats
        # every alternative: falling through to a weaker gate would let a typo
        # disable verification, and artifact mode would still record a run
        # whose governance was misconfigured.
        return _refuse_invalid_verify_profile(result, plan, journal)
    freeze = ManifestFreeze(plan, manifest)

    if plan.mode == PROMOTION_ARTIFACT:
        return _deliver_artifact(result, plan, freeze, journal)

    refusal = _screen_promotion_gates(plan, journal)
    if refusal is not None:
        return PatchTransactionResult(result, refusal, plan=plan, manifest=freeze.manifest)

    outcome = _run_plan(plan, freeze, shell_runner, journal, authorize=authorize)
    return PatchTransactionResult(result, outcome, plan=plan, manifest=freeze.manifest)


def _workspace_admission_refusal(project: Path) -> PatchOutcome | None:
    """Share the staging boundary; local capability callbacks cannot bypass it."""
    try:
        require_unmanaged_patch_workspace(project)
    except StagingAdmissionRequired as exc:
        return PatchOutcome(code=PROMOTION_FAILED, message=str(exc))
    return None


def _screen_before_plan(result: CommandResult) -> _ScreenedPatch:
    """Refuse replies that never earn a run: no usable diff, or an unsafe one."""
    screened = _ScreenedPatch(*extract_patch(result))
    if screened.diff is not None:
        screened = screened._replace(refusal=screen_diff_contents(screened.diff))
    return screened


def _journal_step(journal: RunJournal, phase: str, **kwargs) -> None:
    """The single append point for run-journal events."""
    journal.append(phase, **kwargs)


def _refused(journal: RunJournal, outcome: PatchOutcome) -> PatchOutcome:
    """Journal a refusal decision and return the outcome unchanged."""
    _journal_step(journal, PHASE_REFUSED, data={"code": outcome.code})
    return outcome


def _journal_outcome(journal: RunJournal, phase: str, outcome: PatchOutcome) -> PatchOutcome:
    """Journal a terminal phase for an outcome and return it unchanged."""
    _journal_step(journal, phase, data={"code": outcome.code})
    return outcome


def _journal_frozen(journal: RunJournal, frozen: dict) -> None:
    _journal_step(journal, PHASE_FROZEN, manifest_hash=frozen["manifest_hash"])


def _freeze_and_journal(freeze: ManifestFreeze, journal: RunJournal) -> dict:
    """Persist the manifest and journal the freeze, returning the frozen payload."""
    frozen = freeze.freeze()
    _journal_frozen(journal, frozen)
    return frozen


def _open_run_journal(
    project: Path,
    plan: PatchPlan,
    proposal: dict | None,
) -> RunJournal:
    """Give the run its identity and record what was resolved from the ticket."""
    journal = RunJournal(project, plan.run_id)
    _journal_step(
        journal,
        PHASE_RESOLVED,
        data={
            "mode": plan.mode,
            "verify_source": plan.verify_source,
            "isolated": plan.isolated,
            "targets": sorted(plan.targets),
            "proposal_sha256": (proposal or {}).get("proposal_sha256"),
        },
    )
    return journal


def _refuse_invalid_verify_profile(
    result: CommandResult,
    plan: PatchPlan,
    journal: RunJournal,
) -> PatchTransactionResult:
    """Refuse, as a journaled decision, a run whose declared gate cannot run."""
    return PatchTransactionResult(
        result,
        _refused(
            journal,
            PatchOutcome(code=VERIFY_PROFILE_INVALID, message=plan.verify_error),
        ),
        plan=plan,
    )


def _deliver_artifact(
    result: CommandResult,
    plan: PatchPlan,
    freeze: ManifestFreeze,
    journal: RunJournal,
) -> PatchTransactionResult:
    """Artifact mode: freeze the patch and hand it over, touching no workspace."""
    frozen = _freeze_and_journal(freeze, journal)
    deliver_patch_artifact(plan, frozen)
    _journal_step(journal, PHASE_COMPLETED, data={"delivery": "artifact"})
    return PatchTransactionResult(result, None, plan=plan, manifest=freeze.manifest)


def _screen_promotion_gates(plan: PatchPlan, journal: RunJournal) -> PatchOutcome | None:
    """Refuse a plan that may not attempt promotion, recording why.

    Two gates answer one question — may this run land anything at all? The
    precondition screen covers the mechanics; the branch screen holds the
    mode's own promise.
    """
    refusal = screen_promotion_preconditions(plan)
    if refusal is not None:
        return _refused(journal, refusal)
    if plan.mode != PROMOTION_BRANCH or plan.isolated:
        return None
    # Branch promises a verified commit and an untouched shared tree; a run
    # that cannot isolate (no gate to verify with, or no worktree support)
    # cannot keep either promise. Falling back to writing the workspace
    # would be the silent downgrade the mode exists to rule out.
    return _refused(
        journal,
        PatchOutcome(
            code=PROMOTION_FAILED,
            message=(
                "promotion_mode=branch requires a verify gate and worktree "
                "isolation, and this run has neither a resolvable verify "
                "command nor an isolatable checkout. Name a verify profile "
                "(or command), or explicitly choose promotion_mode=apply "
                "for an unverified local application."
            ),
        ),
    )


def _run_plan(
    plan: PatchPlan,
    freeze: ManifestFreeze,
    shell_runner: ShellRunner,
    journal: RunJournal,
    *,
    authorize: Authorizer | None = None,
) -> PatchOutcome | None:
    """Verify the plan isolated when it can be, directly when it cannot."""
    run = _run_isolated if plan.isolated else _run_direct
    return run(plan, freeze, shell_runner, journal, authorize=authorize)


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
        return _refused(journal, refusal)
    record = getattr(authorize, "record", None) or {}
    _journal_step(
        journal,
        PHASE_AUTHORIZED,
        manifest_hash=frozen.get("manifest_hash"),
        data={"jti": record.get("jti")} if record.get("jti") else None,
    )
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
    frozen = _freeze_and_journal(freeze, journal)
    refusal = _authorize(plan, frozen, journal, authorize)
    if refusal is not None:
        return refusal

    _journal_step(journal, PHASE_STAGING, data={"mode": plan.mode})
    staged = stage_patch(plan, shell_runner)
    if not staged.isolated:
        _journal_step(journal, PHASE_STAGING_UNAVAILABLE)
        return _without_isolation(plan, freeze, shell_runner, journal)
    if staged.outcome is not None:
        return _refused(journal, staged.outcome)
    _journal_step(journal, PHASE_STAGED, data={"verified": True})
    if plan.mode == PROMOTION_BRANCH:
        # The verified result already lives on its own ref; deliberately nothing
        # is written to the shared working tree. The branch commit happened
        # under the ``staging`` intent, so ``staged`` closes it and ``promoted``
        # records where the result now lives.
        _journal_step(journal, PHASE_PROMOTED, data={"branch": f"koru/run-{plan.run_id}"})
        return None

    conflict = guard_promotion(plan, frozen)
    if conflict is not None:
        return _refused(journal, conflict)
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
        return _refused(
            journal,
            PatchOutcome(
                code=PROMOTION_FAILED,
                message=(
                    "promotion_mode=branch needs a staging worktree to commit into, and "
                    "one could not be created here — a read-only checkout is the usual "
                    "reason. Nothing was applied. Re-run with promotion_mode=apply to "
                    "patch the workspace directly, or from a writable checkout."
                ),
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
    """Patch the workspace in place, reversing the exact diff on failed verification."""
    refusal = screen_direct_apply(plan)
    if refusal is not None:
        return _refused(journal, refusal)
    frozen = freeze.freeze()
    if not frozen_journaled:
        _journal_frozen(journal, frozen)
        refusal = _authorize(plan, frozen, journal, authorize)
        if refusal is not None:
            return refusal
    return _apply_to_workspace(
        plan,
        freeze,
        shell_runner,
        journal,
        verify=bool(plan.verify_command),
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
    # Re-observe after authorizer callbacks or staging. Admission may have
    # changed since preflight; failed isolation never grants direct-write rights.
    refusal = _workspace_admission_refusal(plan.project)
    if refusal is not None:
        return _refused(journal, refusal)
    freeze.freeze()

    _journal_step(journal, PHASE_APPLYING)
    applied = apply_unified_diff(plan.project, plan.diff)
    if not applied.ok:
        return _refused(
            journal,
            PatchOutcome(
                code=PATCH_DOES_NOT_APPLY,
                message=applied.detail,
                retryable=True,
                diagnostics=applied.detail,
            ),
        )
    _journal_step(journal, PHASE_APPLIED, data={"changed_files": sorted(applied.changed_files)})

    if verify:
        try:
            gate = shell_runner(plan.verify_command, plan.project)
        except Exception as exc:
            gate = SimpleNamespace(returncode=1, stdout="", stderr=f"{type(exc).__name__}: {exc}")
        if gate.returncode != 0:
            outcome = roll_back_failed_verify(plan, applied.changed_files, gate)
            phase = PHASE_ROLLED_BACK if outcome.workspace_left_untouched else PHASE_REFUSED
            return _journal_outcome(journal, phase, outcome)
        _journal_step(journal, PHASE_VERIFIED)

    if plan.mode != PROMOTION_COMMIT:
        return None
    _journal_step(journal, PHASE_PROMOTING, data={"mode": plan.mode})
    outcome = commit_if_requested(plan, applied.changed_files)
    if outcome is not None:
        return _journal_outcome(journal, PHASE_ROLLED_BACK, outcome)
    _journal_step(journal, PHASE_PROMOTED, data={"mode": plan.mode})
    return None
