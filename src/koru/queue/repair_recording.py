"""Recording — and now routing — queue patch runs through the durable store.

Every LLM invocation becomes a persisted model attempt (started before the
call, finished with its outcome and an output hash), and the run's coarse
status walks the repair lifecycle as the queue works. Recording itself is
still best-effort: a store failure never breaks the queue.

Routing is now live (commit 6): with a model registry configured, a
classified provider failure — policy block, sticky error, exhausted timeout —
routes to the next model *inside the same call*, on the same run and ledger,
and a fully burned roster parks the run ``safe_blocked`` rather than
improvising. The decision logic lives in ``repair_runs.router``
(``choose_model``/``classify_invocation``); this module only drives it. See
``tests/test_repair_router.py`` for the end-to-end milestone (model A blocked
→ model B completes as a second attempt on one run, surviving a restart).

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
    lc.PROBE_REQUIRED: lc.CONTEXT_REQUIRED,  # facts may exist by now; re-enter
    lc.VERIFICATION_FAILED: lc.CONTEXT_REQUIRED,
    lc.WORKSPACE_DRIFT: lc.CONTEXT_REQUIRED,
    lc.ROLLED_BACK: lc.CONTEXT_REQUIRED,
}


def _required_facts(ticket: dict) -> list:
    """Fact requests a ticket declares (``inputs.required_facts``)."""
    from koru.repair_runs.context_broker import FactRequest

    requests = []
    for entry in (ticket.get("inputs") or {}).get("required_facts") or []:
        if isinstance(entry, dict) and entry.get("schema") and entry.get("key"):
            requests.append(
                FactRequest(fact_schema=str(entry["schema"]), key=str(entry["key"])),
            )
    return requests


class RepairRecordingSession:
    """One queue run of one patch ticket, mirrored into the store."""

    def __init__(
        self,
        store: RepairRunStore,
        run: RepairRun,
        owner: str,
        registry: tuple = (),
    ) -> None:
        self._store = store
        self._run = run
        self._owner = owner
        self._attempt_no = 0
        # A fresh iteration must sit above everything already in the ledger,
        # not just above the run row — a crash may have recorded attempts the
        # run's counter never caught up with.
        recorded = max(
            (attempt.iteration for attempt in store.attempts(run.id)),
            default=0,
        )
        self._iteration = max(run.current_iteration, recorded) + 1
        self._registry = registry
        self._parked = False
        self._snapshot = None  # ContextSnapshot once the broker delivered

    @classmethod
    def begin(
        cls,
        project: Path,
        ticket: dict,
        actor: str,
        store: RepairRunStore | None = None,
        probes: dict | None = None,
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
            from koru.repair_runs.router import load_model_registry

            session = cls(store, claimed, actor, registry=load_model_registry(project))
            required = _required_facts(ticket)
            if required and not session._ensure_context(required, probes):
                # Declared facts could not be delivered: the run is parked
                # ``probe_required`` (visible to resume tooling), the lease is
                # given back, and the queue proceeds unrecorded — a model must
                # not run on a context the ticket said was mandatory.
                return None
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
        """Every model call goes through the store: start → invoke → persist.

        With a model registry configured, a classified provider failure routes
        to the next model *inside the same call* — same run, same ledger, same
        contract; the router hands out nothing but a model name. Without a
        registry the single configured model is invoked exactly as before.
        """
        from koru.repair_runs.router import (
            NO_SWITCH_CODES,
            choose_model,
            classify_invocation,
        )

        def recording_runner(action: dict[str, Any], project: Path) -> CommandResult:
            last_failure: str | None = None
            result: CommandResult | None = None
            while True:
                routed = action
                if self._registry:
                    spec = choose_model(
                        self._registry,
                        self._store.attempts(self._run.id),
                        last_failure=last_failure,
                    )
                    if spec is None:
                        self._park_exhausted()
                        return result if result is not None else _exhausted_result()
                    routed = {**action, "model": spec.model, "provider": spec.provider}
                if self._snapshot is not None:
                    # The model sees facts, not logs — and the snapshot hash is
                    # part of the attempt's input identity below.
                    routed = {**routed, "context_facts": self._snapshot.render()}

                attempt = self._start_attempt(routed)
                try:
                    result = llm_runner(routed, project)
                except Exception:
                    self._finish_attempt(
                        attempt, status="interrupted", failure_code="invoke_error",
                    )
                    raise
                failure = classify_invocation(result)
                if failure is None:
                    self._finish_attempt(
                        attempt,
                        status="succeeded",
                        output_hash=stable_hash(result.stdout or ""),
                    )
                    return result
                self._finish_attempt(attempt, status="failed", failure_code=failure)
                if not self._registry or failure in NO_SWITCH_CODES:
                    # No roster to route within, or an operation that is
                    # forbidden regardless of who performs it.
                    return result
                last_failure = failure

        return recording_runner

    def _ensure_context(self, required: list, probes: dict | None) -> bool:
        """Deliver the ticket's required facts through the broker, or park.

        Success pins the snapshot hash on the run (via the ``context_ready``
        transition) and stashes the snapshot for injection into every model
        call. Failure walks the run to ``probe_required`` and releases the
        lease — declared context is mandatory, and running the model without
        it would be answering a different question.
        """
        from koru.repair_runs.context_broker import ContextBroker, ContextSnapshot

        try:
            if self._run.status == lc.CREATED:
                self._run = self._store.transition(
                    self._run.id, lc.CONTEXT_REQUIRED,
                    expected_version=self._run.version,
                    current_iteration=self._iteration,
                )
            broker = ContextBroker(self._store, probes)
            delivered = broker.ensure(self._run, required)
            if isinstance(delivered, ContextSnapshot):
                self._snapshot = delivered
                if self._run.status == lc.CONTEXT_REQUIRED:
                    self._run = self._store.transition(
                        self._run.id, lc.CONTEXT_READY,
                        expected_version=self._run.version,
                        context_hash=delivered.hash,
                    )
                return True
            _logger.info(
                "koru.repair.probe_required run=%s: %s", self._run.id, delivered.reason,
            )
            if self._run.status == lc.CONTEXT_REQUIRED:
                self._run = self._store.transition(
                    self._run.id, lc.PROBE_REQUIRED, expected_version=self._run.version,
                )
            self._store.release(self._run.id, self._owner)
            return False
        except Exception:
            _logger.exception("koru.repair.context_failed run=%s", self._run.id)
            return False

    def _park_exhausted(self) -> None:
        """Every model on the roster is burned: park, never improvise."""
        try:
            self._walk(lc.MODEL_BLOCKED, lc.MODEL_EXHAUSTED, lc.SAFE_BLOCKED)
        except Exception:
            _logger.exception("koru.repair.park_failed run=%s", self._run.id)
        self._parked = True

    def finish(self, result: CommandResult, outcome: PatchOutcome | None) -> None:
        """Walk the run to its terminal status and give the lease back.

        The chain is coarse on purpose — the patch transaction's journal holds
        the fine-grained truth; this status is the queue-level summary the
        router and recovery will read.
        """
        try:
            if self._parked:
                self._store.release(self._run.id, self._owner)
                return
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
                    {
                        "prompt": action.get("prompt"),
                        "model": action.get("model"),
                        "context_hash": (action.get("context_facts") or {}).get(
                            "context_hash",
                        ),
                    },
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


def _exhausted_result() -> CommandResult:
    """The reply the queue sees when no model on the roster could answer."""
    from types import SimpleNamespace

    return SimpleNamespace(
        returncode=1,
        stdout="",
        stderr=(
            "model_exhausted: every configured repair model is blocked or burned "
            "for this run; the run is parked safe_blocked for a human."
        ),
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
