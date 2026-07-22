"""Resuming repair runs after a restart (commit 5).

At startup a worker sweeps the store: every non-terminal run whose lease is
dead gets its dangling ``running`` model attempts closed as ``interrupted``
(the worker died mid-call; the answer, if any, was never recorded), and the
run is classified into the one action a resumed worker may take. The
classification mirrors the plan's table — retry the model, don't re-apply a
staged patch, don't promote twice — and the two moves that are provably safe
from the store alone are performed here directly:

- ``model_running`` with a dead lease → ``model_blocked`` (the attempt is
  interrupted; the router picks the *next* model, same run, same ledger);
- ``promoted`` → ``completed`` (the mutation finished; only bookkeeping died);
- ``model_exhausted`` → ``safe_blocked`` (nothing left to try — never
  "do whatever closes the ticket").

Everything that touches a workspace (staging, verify, rollback) is only
*classified* here; execution belongs to the queue, whose journal-based
recovery owns workspace truth.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.store import RepairRunStore, StaleVersion

# What a resumed worker should do with a run.
RETRY_MODEL = "retry_model"  # ask again — next model, same run, same ledger
RESUME_STAGING = "resume_staging"  # delegate to workspace recovery; never re-apply
RESUME_VERIFY = "resume_verify"  # patch is staged; run the gate, don't re-apply
RESUME_ROLLBACK = "resume_rollback"  # finish the rollback that was underway
COMPLETED_PROMOTION = "completed_promotion"  # promoted → records closed here
NEXT_ITERATION = "next_iteration"  # drift/verify-fail: fresh context, new loop
PARKED = "parked"  # terminal after self-healing; nothing to resume


@dataclass(frozen=True)
class ResumeAction:
    run_id: str
    kind: str
    status: str  # the run's status after the sweep's own self-healing
    interrupted_attempts: int = 0


def sweep_resumable(
    store: RepairRunStore,
    *,
    now: datetime | None = None,
) -> list[ResumeAction]:
    """Close dangling attempts, self-heal what the store can prove, classify the rest."""
    actions: list[ResumeAction] = []
    for run in store.resumable_runs(now=now):
        interrupted = _interrupt_dangling_attempts(store, run.id, now=now)
        try:
            action = _classify_and_heal(store, run, interrupted, now=now)
        except StaleVersion:
            # Another worker moved the run between our read and our write —
            # that worker owns the resume; this sweep leaves it alone.
            continue
        actions.append(action)
    return actions


def _interrupt_dangling_attempts(
    store: RepairRunStore,
    run_id: str,
    *,
    now: datetime | None = None,
) -> int:
    """A ``running`` attempt on a lease-dead run is a worker that died mid-call."""
    count = 0
    for attempt in store.attempts(run_id):
        if attempt.status == "running":
            store.finish_attempt(
                attempt.id, status="interrupted", failure_code="worker_died", now=now,
            )
            count += 1
    return count


def _classify_and_heal(
    store: RepairRunStore,
    run,
    interrupted: int,
    *,
    now: datetime | None = None,
):
    status = run.status

    if status == lc.MODEL_RUNNING:
        # The plan's row: model_attempt_started without an end → mark it
        # interrupted (done above) and route to the next model.
        run = store.transition(
            run.id, lc.MODEL_BLOCKED, expected_version=run.version, now=now,
        )
        return ResumeAction(run.id, RETRY_MODEL, run.status, interrupted)

    if status == lc.PROMOTED:
        run = store.transition(
            run.id, lc.COMPLETED, expected_version=run.version, now=now,
        )
        return ResumeAction(run.id, COMPLETED_PROMOTION, run.status, interrupted)

    if status == lc.MODEL_EXHAUSTED:
        run = store.transition(
            run.id, lc.SAFE_BLOCKED, expected_version=run.version, now=now,
        )
        return ResumeAction(run.id, PARKED, run.status, interrupted)

    kind = {
        lc.CREATED: RETRY_MODEL,
        lc.CONTEXT_REQUIRED: RETRY_MODEL,
        lc.CONTEXT_READY: RETRY_MODEL,
        lc.MODEL_BLOCKED: RETRY_MODEL,
        lc.ACTION_PROPOSED: RETRY_MODEL,
        lc.ACTION_VALIDATED: RETRY_MODEL,
        lc.PATCH_REJECTED: RETRY_MODEL,
        lc.STAGING: RESUME_STAGING,
        lc.VERIFYING: RESUME_VERIFY,
        lc.ROLLBACK_STARTED: RESUME_ROLLBACK,
        lc.VERIFICATION_FAILED: NEXT_ITERATION,
        lc.WORKSPACE_DRIFT: NEXT_ITERATION,
        lc.ROLLED_BACK: NEXT_ITERATION,
    }.get(status, PARKED)
    return ResumeAction(run.id, kind, status, interrupted)
