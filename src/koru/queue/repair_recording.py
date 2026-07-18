"""Recording queue patch runs into the durable repair-run store (commit 4).

Every LLM invocation becomes a persisted model attempt — started before the
call, finished with the invocation's outcome and an output hash — and the
run's coarse status walks the repair lifecycle as the queue works. This layer
is deliberately *observational* for now: recording failures never break the
queue, and no routing decisions are made here. The router (commit 6) will
turn the same records into decisions; the shape of what is recorded is
already the shape it will need.

Dependency direction is law: this module imports ``repair_runs``; nothing in
``repair_runs`` may ever import the queue.
"""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path
from typing import Any

from koru.queue.patch_mode import (
    MANIFEST_MISMATCH,
    NO_PATCH_EMITTED,
    PATCH_DOES_NOT_APPLY,
    POLICY_DENIED,
    PROMOTION_CONFLICT,
    PatchOutcome,
)
from koru.queue.types import CommandResult
from koru.repair_runs import lifecycle as lc
from koru.repair_runs.models import RepairRun, stable_hash
from koru.repair_runs.sqlite_store import SqliteRepairRunStore, default_store_path
from koru.repair_runs.store import RepairRunStore, RunAlreadyExists

_logger = logging.getLogger(__name__)

_DEFAULT_LEASE_S = 900

#: How to take one step toward ``model_running`` from wherever a previous
#: (possibly crashed) session left the run. Anything not listed is a state
#: this coarse recorder does not understand — it then declines to record
#: rather than forging a history it cannot vouch for.
_TOWARD_MODEL_RUNNING: dict[str, str] = {
    lc.CREATED: lc.CONTEXT_READY,
    lc.CONTEXT_REQUIRED: lc.CONTEXT_READY,
    lc.CONTEXT_READY: lc.MODEL_RUNNING,
    lc.MODEL_BLOCKED: lc.MODEL_RUNNING,
    lc.PATCH_REJECTED: lc.MODEL_RUNNING,
    lc.VERIFICATION_FAILED: lc.CONTEXT_REQUIRED,
    lc.WORKSPACE_DRIFT: lc.CONTEXT_REQUIRED,
    lc.ROLLED_BACK: lc.CONTEXT_REQUIRED,
}


class RepairRecordingSession:
    """One queue run of one patch ticket, mirrored into the store."""

    def __init__(self, store: RepairRunStore, run: RepairRun, owner: str) -> None:
        self._store = store
        self._run = run
        self._owner = owner
        self._attempt_no = 0
        self._iteration = run.current_iteration + 1

    @classmethod
    def begin(
        cls,
        project: Path,
        ticket: dict,
        actor: str,
        store: RepairRunStore | None = None,
    ) -> RepairRecordingSession | None:
        """Open (or resume) the ticket's repair run and take its lease.

        Returns ``None`` — and the queue proceeds unrecorded — when the run is
        already terminal, another worker holds the lease, or the store cannot
        be reached. Best-effort by design at this stage.
        """
        ticket_id = str(ticket.get("id") or "")
        if not ticket_id:
            return None
        try:
            store = store or SqliteRepairRunStore(default_store_path(project))
            run = store.find_run(ticket_id, str(project))
            if run is None:
                try:
                    run = store.create_run(
                        ticket_id=ticket_id,
                        project_root=str(project),
                        max_iterations=int(
                            (ticket.get("inputs") or {}).get("max_repair_iterations")
                            or 5,
                        ),
                    )
                except RunAlreadyExists:
                    run = store.find_run(ticket_id, str(project))
            if run is None or run.status in lc.TERMINAL_STATES:
                return None
            claimed = store.claim(run.id, actor, lease_s=_DEFAULT_LEASE_S)
            if claimed is None:
                _logger.info(
                    "koru.repair.lease_held_elsewhere run=%s ticket=%s", run.id, ticket_id,
                )
                return None
            session = cls(store, claimed, actor)
            return session if session._advance_to_model_running() else None
        except Exception:
            _logger.exception("koru.repair.recording_unavailable ticket=%s", ticket_id)
            return None

    @property
    def run_id(self) -> str:
        return self._run.id

    def wrap_llm(
        self,
        llm_runner: Callable[[dict[str, Any], Path], CommandResult],
    ) -> Callable[[dict[str, Any], Path], CommandResult]:
        """Every model call goes through the store: start → invoke → persist."""

        def recording_runner(action: dict[str, Any], project: Path) -> CommandResult:
            attempt = self._start_attempt(action)
            try:
                result = llm_runner(action, project)
            except Exception:
                self._finish_attempt(attempt, status="interrupted", failure_code="invoke_error")
                raise
            if attempt is not None:
                if result.returncode == 0:
                    self._finish_attempt(
                        attempt,
                        status="succeeded",
                        output_hash=stable_hash(result.stdout or ""),
                    )
                else:
                    self._finish_attempt(
                        attempt, status="failed", failure_code="invoke_failed",
                    )
            return result

        return recording_runner

    def finish(self, result: CommandResult, outcome: PatchOutcome | None) -> None:
        """Walk the run to its terminal status and give the lease back.

        The chain is coarse on purpose — the patch transaction's journal holds
        the fine-grained truth; this status is the queue-level summary the
        router and recovery will read.
        """
        try:
            if outcome is None and result.returncode == 0:
                self._walk(
                    lc.ACTION_PROPOSED, lc.ACTION_VALIDATED, lc.STAGING,
                    lc.VERIFYING, lc.PROMOTED, lc.COMPLETED,
                )
            elif outcome is None:
                # The model never produced a usable answer.
                self._walk(lc.FAILED)
            else:
                self._walk(*_terminal_chain_for(outcome))
            self._store.release(self._run.id, self._owner)
        except Exception:
            _logger.exception("koru.repair.finish_failed run=%s", self._run.id)

    # -- internals ----------------------------------------------------------
    def _advance_to_model_running(self) -> bool:
        try:
            guard = 0
            while self._run.status != lc.MODEL_RUNNING:
                step = _TOWARD_MODEL_RUNNING.get(self._run.status)
                if step is None or guard > 4:
                    return False
                self._run = self._store.transition(
                    self._run.id,
                    step,
                    expected_version=self._run.version,
                    current_iteration=self._iteration,
                )
                guard += 1
            return True
        except Exception:
            _logger.exception("koru.repair.advance_failed run=%s", self._run.id)
            return False

    def _start_attempt(self, action: dict[str, Any]):
        try:
            self._attempt_no += 1
            return self._store.start_attempt(
                self._run.id,
                iteration=self._iteration,
                attempt=self._attempt_no,
                provider=str(action.get("provider") or "openrouter"),
                model=str(action.get("model") or "default"),
                input_hash=stable_hash(
                    {"prompt": action.get("prompt"), "model": action.get("model")},
                ),
            )
        except Exception:
            _logger.exception("koru.repair.attempt_start_failed run=%s", self._run.id)
            return None

    def _finish_attempt(self, attempt, **kwargs) -> None:
        if attempt is None:
            return
        try:
            self._store.finish_attempt(attempt.id, **kwargs)
        except Exception:
            _logger.exception("koru.repair.attempt_finish_failed run=%s", self._run.id)

    def _walk(self, *statuses: str) -> None:
        for status in statuses:
            self._run = self._store.transition(
                self._run.id, status, expected_version=self._run.version,
            )


def _terminal_chain_for(outcome: PatchOutcome) -> tuple[str, ...]:
    """Map a patch outcome onto the repair lifecycle's legal terminal chains."""
    if outcome.code == POLICY_DENIED:
        return (lc.ACTION_PROPOSED, lc.ACTION_VALIDATED, lc.SAFE_BLOCKED)
    if outcome.code in {NO_PATCH_EMITTED, PATCH_DOES_NOT_APPLY}:
        return (lc.ACTION_PROPOSED, lc.PATCH_REJECTED, lc.FAILED)
    if outcome.code in {PROMOTION_CONFLICT, MANIFEST_MISMATCH}:
        return (
            lc.ACTION_PROPOSED, lc.ACTION_VALIDATED, lc.STAGING,
            lc.WORKSPACE_DRIFT, lc.SAFE_BLOCKED,
        )
    if outcome.code.startswith("verify"):
        return (
            lc.ACTION_PROPOSED, lc.ACTION_VALIDATED, lc.STAGING,
            lc.VERIFYING, lc.VERIFICATION_FAILED, lc.FAILED,
        )
    return (lc.ACTION_PROPOSED, lc.PATCH_REJECTED, lc.FAILED)
