"""Retry policy for patch tickets, and the evidence a finished run leaves.

Sits above the deterministic transaction: it decides *whether to ask the agent
again*, which is a policy question, while the transaction only decides whether
a given patch may land. Only mechanical failures — a malformed diff, one that
no longer applies — are retried, because those are the ones a model can fix
once it sees the diagnostic. A patch that applied but failed its gate is wrong
on the merits, and re-asking would spend another agent run on the same idea.

Because this layer owns the whole run — every attempt, the pinned base, the
final outcome — it is also where the evidence bundle is assembled and written.
"""

from __future__ import annotations

import hashlib
import os
from collections.abc import Callable
from pathlib import Path
from typing import Any
from uuid import uuid4

from koru.queue.evidence import (
    VERDICT_APPLIED,
    VERDICT_ARTIFACT,
    VERDICT_REFUSED,
    VERDICT_VERIFIED,
    build_evidence_bundle,
    patch_attempt_record,
    persist_evidence,
)
from koru.queue.journal import PHASE_COMPLETED, RunJournal
from koru.queue.patch_mode import (
    MANIFEST_MISMATCH,
    PATCH_DOES_NOT_APPLY,
    PROMOTION_ARTIFACT,
    PROMOTION_BRANCH,
    PatchOutcome,
    build_manifest,
    build_retry_prompt,
    current_file_excerpt,
    diff_target_files,
    extract_unified_diff,
    manifest_drift,
    persist_manifest,
    promotion_mode,
    redact_secrets,
)
from koru.queue.transaction.result import PatchPlan, PatchTransactionResult
from koru.queue.types import CommandResult


def patch_retry_budget(ticket: dict | None = None) -> int:
    """How many times to re-ask an agent whose diff would not apply."""
    if ticket is not None:
        per_ticket = (ticket.get("inputs") or {}).get("max_patch_attempts")
        if per_ticket is not None:
            try:
                return max(0, int(per_ticket))
            except (TypeError, ValueError):
                pass
        execution = ticket.get("execution") or {}
        exec_attempts = execution.get("max_attempts")
        if exec_attempts is not None:
            try:
                return max(0, int(exec_attempts))
            except (TypeError, ValueError):
                pass
    raw = (os.environ.get("KORU_QUEUE_PATCH_RETRIES") or "").strip()
    try:
        return max(0, int(raw)) if raw else 1
    except ValueError:
        return 1


def apply_patch_with_retry(
    project: Path,
    result: CommandResult,
    ticket: dict,
    action: dict[str, Any],
    llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    shell_runner: Callable[[str, Path], CommandResult],
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None = None,
) -> tuple[CommandResult, PatchOutcome | None, dict | None]:
    """Apply the agent's patch, re-asking with the exact rejection on failure.

    A malformed or stale diff is a mechanical problem the agent can fix once it
    sees ``git apply``'s complaint, so those attempts are retried. A patch that
    applies but fails verification is a *substantive* failure — retrying it
    would just burn another agent run on the same wrong idea — so it is not.

    Returns the final reply, the final outcome, and the evidence bundle for the
    whole run — every attempt's patch hash included, so a retry can never make
    its predecessor disappear from the record.

    ``enrich`` re-attaches project context to the retry request; it is injected
    rather than imported so this module stays independent of the queue runner.
    """
    # Imported at call time so the facade stays the single seam tests stub.
    from koru.queue.transaction.service import execute_patch_transaction

    base_prompt = str(action.get("prompt") or "")
    budget = patch_retry_budget(ticket)
    remaining = budget
    manifest: dict | None = None
    attempts: list[dict] = []

    while True:
        transaction = execute_patch_transaction(project, result, ticket, shell_runner, manifest)
        result, outcome = transaction.result, transaction.outcome
        attempts.append(_attempt_record(len(attempts) + 1, transaction))
        if outcome is None or not outcome.retryable or remaining <= 0:
            return result, outcome, _finish_run(project, ticket, transaction, manifest, attempts)

        manifest, aborted = _pin_or_detect_drift(
            project, ticket, result, budget, manifest, transaction, attempts,
        )
        if aborted is not None:
            return result, aborted, _finish_run(project, ticket, transaction, manifest, attempts)

        remaining -= 1
        retry_action = _build_retry_action(action, base_prompt, project, manifest, outcome, enrich)
        result = llm_runner(retry_action, project)
        if result.returncode != 0:
            return result, outcome, _finish_run(project, ticket, transaction, manifest, attempts)


def _pin_or_detect_drift(
    project: Path,
    ticket: dict,
    result: CommandResult,
    budget: int,
    manifest: dict | None,
    transaction: PatchTransactionResult,
    attempts: list[dict],
) -> tuple[dict | None, PatchOutcome | None]:
    """Pin the base on the first failure, or abort if it since drifted.

    Pinning happens under the run_id the transaction already used, so every
    manifest and the evidence of this run share one directory. Every later
    attempt is judged against that same snapshot, so a retry can never
    silently rebase onto a workspace another session has moved in the
    meantime.
    """
    if manifest is None:
        manifest = _pin_base(
            project,
            ticket,
            result,
            budget,
            run_id=transaction.plan.run_id if transaction.plan else None,
        )
        persist_manifest(project, manifest)
        return manifest, None

    drift = manifest_drift(project, manifest)
    if not drift:
        return manifest, None

    aborted = PatchOutcome(
        code=MANIFEST_MISMATCH,
        message=(
            "the workspace changed between patch attempts, so the retry was "
            f"abandoned rather than rebased onto a moving target ({drift}). "
            "Re-run the ticket against the new state."
        ),
    )
    attempts.append(
        patch_attempt_record(
            len(attempts) + 1,
            patch_sha256=None,
            outcome_code=aborted.code,
            message=aborted.message,
        ),
    )
    return manifest, aborted


def _build_retry_action(
    action: dict[str, Any],
    base_prompt: str,
    project: Path,
    manifest: dict | None,
    outcome: PatchOutcome,
    enrich: Callable[[dict[str, Any], Path], dict[str, Any]] | None,
) -> dict[str, Any]:
    # git and test output can quote file contents, so redact before it
    # travels back out to the model.
    diagnostic = redact_secrets(outcome.diagnostics or outcome.message)
    prompt = build_retry_prompt(base_prompt, diagnostic)
    if manifest and outcome.code == PATCH_DOES_NOT_APPLY:
        # Safe only because the manifest guarantees these contents are still
        # the ones the patch must apply to.
        prompt += current_file_excerpt(project, tuple(manifest.get("touched_files") or ()))
    retry_action = {**action, "prompt": prompt}
    if enrich is not None:
        retry_action = enrich(retry_action, project)
    return retry_action


def _attempt_record(attempt: int, transaction: PatchTransactionResult) -> dict:
    """One transaction attempt, as it will be remembered."""
    plan = transaction.plan
    outcome = transaction.outcome
    return patch_attempt_record(
        attempt,
        patch_sha256=(
            hashlib.sha256(plan.diff.encode("utf-8")).hexdigest() if plan else None
        ),
        outcome_code=outcome.code if outcome else None,
        message=outcome.message if outcome else "",
        retryable=bool(outcome and outcome.retryable),
    )


def _finish_run(
    project: Path,
    ticket: dict,
    transaction: PatchTransactionResult,
    manifest: dict | None,
    attempts: list[dict],
) -> dict:
    """Assemble and persist the run's evidence bundle.

    A failed write does not raise: the bundle is still returned, and the
    completion gate — which judges the *persisted* copy — will refuse to close
    the ticket, which is the correct consequence of unprovable success.
    """
    plan = transaction.plan
    frozen = manifest or transaction.manifest
    run_id = str(
        (frozen or {}).get("run_id")
        or (plan.run_id if plan else None)
        or uuid4().hex[:12],
    )
    verify = (
        {"command": plan.verify_command, "source": plan.verify_source} if plan else {}
    )
    promotion: dict = {"mode": plan.mode, "isolated": plan.isolated} if plan else {}
    if plan and plan.mode == PROMOTION_BRANCH and transaction.outcome is None:
        promotion["branch"] = f"koru/run-{run_id}"

    bundle = build_evidence_bundle(
        run_id=run_id,
        ticket=ticket,
        manifest=frozen,
        patch_attempts=attempts,
        verify=verify,
        promotion=promotion,
        verdict=_verdict(plan, transaction.outcome),
    )
    try:
        persist_evidence(project, bundle)
    except OSError:
        pass
    _journal_terminal(project, run_id, bundle, transaction)
    return bundle


def _journal_terminal(
    project: Path,
    run_id: str,
    bundle: dict,
    transaction: PatchTransactionResult,
) -> None:
    """Close the run's journal with its verdict.

    Refusals were journaled by the transaction as they happened, and artifact
    delivery writes its own ``completed`` — only a landed patch still owes the
    journal its terminal event. Best-effort by design: the journal aids
    recovery, while the completion *gate* is the evidence bundle.
    """
    plan = transaction.plan
    if transaction.outcome is not None or plan is None or plan.mode == PROMOTION_ARTIFACT:
        return
    try:
        RunJournal(project, run_id).append(
            PHASE_COMPLETED, data={"verdict": bundle["verdict"]},
        )
    except OSError:
        pass


def _verdict(plan: PatchPlan | None, outcome: PatchOutcome | None) -> str:
    if outcome is not None or plan is None:
        return VERDICT_REFUSED
    if plan.mode == PROMOTION_ARTIFACT:
        return VERDICT_ARTIFACT
    return VERDICT_VERIFIED if plan.verify_command else VERDICT_APPLIED


def _pin_base(
    project: Path,
    ticket: dict,
    result: CommandResult,
    budget: int,
    run_id: str | None = None,
) -> dict:
    """Freeze the base the remaining attempts must target.

    The first attempt is pinned precisely when it failed for a reason that still
    let us read its targets. A corrupt diff yields none — ``git apply
    --numstat`` cannot parse it — which is exactly the case retries exist for,
    so fall back to the files the ticket declared. A manifest that pins nothing
    would silently permit the rebase it is meant to prevent.
    """
    from koru.queue.verify.resolver import resolve_verify

    diff = extract_unified_diff(result.stdout) or ""
    targets = diff_target_files(project, diff) or tuple(
        str(rel) for rel in (ticket.get("files") or [])
    )
    return build_manifest(
        project,
        run_id=run_id or uuid4().hex[:12],
        ticket=ticket,
        diff=diff,
        targets=targets,
        verify_command=resolve_verify(project, ticket, targets).command,
        mode=promotion_mode(ticket),
        attempt=1,
        max_attempts=budget + 1,
    )
