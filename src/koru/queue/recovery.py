"""Waking up after a crash: decide what a half-finished run may still do.

The one rule recovery lives by: **it never applies a patch**. This module does
not import ``apply_unified_diff`` and has no path to it — re-deciding is always
safe, re-mutating never is, and a recovery that could mutate would be the very
bug it exists to prevent. What it can do is read the journal and the manifest,
prune orphaned worktrees, close a promotion whose commit provably exists, and
retire runs that demonstrably changed nothing. Everything it cannot *prove* is
handed to a human with the exact reason.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from koru.queue.evidence import (
    VERDICT_REFUSED,
    build_evidence_bundle,
    load_evidence,
    patch_attempt_record,
    persist_evidence,
)
from koru.queue.journal import (
    PHASE_COMPLETED,
    PHASE_PROMOTED,
    PHASE_REFUSED,
    RunJournal,
    interrupted_mutation,
    last_phase,
    read_events,
)
from koru.queue.manifest import load_persisted_manifest, manifest_drift
from koru.queue.workspace import branch_head, prune_stale_worktrees

# What a woken-up process should do with a run.
NOTHING_TO_DO = "nothing_to_do"  # terminal event or evidence already on disk
REPLAY_SAFE = "replay_safe"  # provably no workspace mutation — re-run the ticket
FINISH_PROMOTION = "finish_promotion"  # the commit exists; only bookkeeping died
NEEDS_HUMAN = "needs_human"  # a mutation may have half-run and cannot be proven either way

_TERMINAL_PHASES = {PHASE_COMPLETED, PHASE_REFUSED}


@dataclass(frozen=True)
class RecoveryAssessment:
    """What the journal and workspace prove about an interrupted run."""

    run_id: str
    recommendation: str
    reason: str
    interrupted_phase: str | None = None


def scan_incomplete_runs(project: Path) -> list[str]:
    """Run ids whose journal never reached a terminal event.

    Runs without a journal are invisible here by design: they either predate
    journaling or refused before a plan existed, and neither mutated anything.
    """
    runs_dir = project / ".koru" / "runs"
    if not runs_dir.is_dir():
        return []
    incomplete = []
    for journal_path in sorted(runs_dir.glob("*/events.jsonl")):
        run_id = journal_path.parent.name
        events = read_events(project, run_id)
        if events and last_phase(events) not in _TERMINAL_PHASES:
            incomplete.append(run_id)
    return incomplete


def assess_run(project: Path, run_id: str) -> RecoveryAssessment:
    """Judge one run strictly from durable state — journal, manifest, git.

    The decision table, most-proven first:

    - terminal event or persisted evidence → nothing to do;
    - open ``promoting`` whose branch commit exists → the mutation finished,
      only the bookkeeping died: finish the promotion records;
    - workspace identical to the frozen manifest base → whatever was underway
      never landed (worktree work is disposable by construction): safe to
      close this run and re-run the ticket;
    - anything else → a human, with the reason. A workspace that differs from
      base after an open ``applying`` cannot be told apart from a concurrent
      edit by any record we keep, and guessing is how work gets destroyed.
    """
    events = read_events(project, run_id)
    if not events:
        return RecoveryAssessment(
            run_id, NEEDS_HUMAN, "run directory exists but its journal is empty or unreadable",
        )
    if last_phase(events) in _TERMINAL_PHASES or load_evidence(project, run_id) is not None:
        return RecoveryAssessment(run_id, NOTHING_TO_DO, "run already reached a durable end")

    open_intent = interrupted_mutation(events)

    if branch_head(project, f"koru/run-{run_id}"):
        # The run's own ref exists, and it is only ever created after a green
        # verify — the mutation finished, whatever intent the crash left open.
        # (A commit-on-main promotion cannot be attributed this way: HEAD
        # moving is not proof this run moved it, so it falls through to the
        # conservative paths below.)
        return RecoveryAssessment(
            run_id,
            FINISH_PROMOTION,
            "the promotion commit exists on this run's ref; only the completion records died",
            interrupted_phase=open_intent,
        )

    manifest = load_persisted_manifest(project, run_id)
    if manifest is not None and not manifest_drift(project, manifest):
        # The workspace still matches the frozen base byte for byte, so no
        # mutation reached it — staging worktrees are siblings and disposable.
        return RecoveryAssessment(
            run_id,
            REPLAY_SAFE,
            "workspace is identical to the frozen manifest base; nothing landed",
            interrupted_phase=open_intent,
        )

    where = f"after `{open_intent}` was journaled" if open_intent else "between phases"
    return RecoveryAssessment(
        run_id,
        NEEDS_HUMAN,
        (
            f"the process died {where} and the workspace no longer matches the "
            "frozen base — the records cannot distinguish a half-applied patch "
            "from a concurrent edit, and guessing could destroy someone's work"
        ),
        interrupted_phase=open_intent,
    )


def recover_run(project: Path, run_id: str) -> RecoveryAssessment:
    """Perform only the actions the assessment proved safe, idempotently.

    Running this twice is a no-op the second time: every action lands durable
    state that the next assessment reads as terminal.
    """
    assessment = assess_run(project, run_id)

    if assessment.recommendation == FINISH_PROMOTION:
        journal = RunJournal(project, run_id)
        branch = f"koru/run-{run_id}"
        journal.append(
            PHASE_PROMOTED,
            data={"recovered": True, "branch": branch, "commit_sha": branch_head(project, branch)},
        )
        journal.append(PHASE_COMPLETED, data={"verdict": "verified", "recovered": True})
        _persist_interrupted_evidence(
            project, run_id, verdict="verified",
            note="promotion commit found on ref during crash recovery",
        )
        return assessment

    if assessment.recommendation == REPLAY_SAFE:
        journal = RunJournal(project, run_id)
        journal.append(
            PHASE_REFUSED,
            data={"code": "interrupted", "recovered": True, "reason": assessment.reason},
        )
        _persist_interrupted_evidence(
            project, run_id, verdict=VERDICT_REFUSED,
            note="run interrupted by a crash before any workspace mutation landed",
        )
        return assessment

    return assessment


def sweep(project: Path) -> list[RecoveryAssessment]:
    """Startup housekeeping: prune orphan worktrees, then triage every run.

    Worktrees are pruned first and unconditionally — they are disposable by
    construction, and a crashed run's worktree holds nothing the journal and
    manifest do not.
    """
    prune_stale_worktrees(project)
    return [recover_run(project, run_id) for run_id in scan_incomplete_runs(project)]


def _persist_interrupted_evidence(
    project: Path,
    run_id: str,
    *,
    verdict: str,
    note: str,
) -> None:
    """Write the evidence a crashed run never got to write, from durable state.

    Assembled strictly from the manifest and journal — recovery attests only
    what it can read, never what the run intended.
    """
    if load_evidence(project, run_id) is not None:
        return
    manifest = load_persisted_manifest(project, run_id)
    branch = f"koru/run-{run_id}"
    commit_sha = branch_head(project, branch)
    bundle = build_evidence_bundle(
        run_id=run_id,
        ticket={"id": (manifest or {}).get("ticket_id")},
        manifest=manifest,
        patch_attempts=[
            patch_attempt_record(
                1,
                patch_sha256=(manifest or {}).get("patch_sha256"),
                outcome_code=None if verdict == "verified" else "interrupted",
                message=note,
            ),
        ],
        verify={
            "command": (manifest or {}).get("verify_command") or "",
            "source": "manifest",
            "status": "passed" if verdict == "verified" else "not_reached",
        },
        promotion=(
            {"mode": "branch", "isolated": True, "branch": branch, "commit_sha": commit_sha}
            if commit_sha
            else {"recovered": True}
        ),
        verdict=verdict,
        actor="koru-recovery",
    )
    try:
        persist_evidence(project, bundle)
    except OSError:
        pass
