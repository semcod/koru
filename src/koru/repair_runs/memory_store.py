"""In-memory repair-run store — for contract tests only.

Same promises as SQLite, enforced with a lock and dictionaries. If a test
passes here and fails on SQLite (or the reverse), the contract is ambiguous
and that ambiguity is the bug.
"""

from __future__ import annotations

import threading
from dataclasses import replace
from datetime import datetime, timedelta

from koru.repair_runs.lifecycle import TERMINAL_STATES, validate_transition
from koru.repair_runs.models import (
    ModelAttempt,
    RepairArtifact,
    RepairEvent,
    RepairFact,
    RepairRun,
    new_id,
    utcnow,
)
from koru.repair_runs.store import (
    RepairRunStore,
    RunAlreadyExists,
    StaleVersion,
    UnknownRun,
)


class MemoryRepairRunStore(RepairRunStore):
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._runs: dict[str, RepairRun] = {}
        self._events: dict[str, list[RepairEvent]] = {}
        self._events_by_key: dict[str, RepairEvent] = {}
        self._attempts: dict[str, list[ModelAttempt]] = {}
        self._facts: dict[str, list[RepairFact]] = {}
        self._artifacts: dict[str, list[RepairArtifact]] = {}

    # -- runs ---------------------------------------------------------------
    def create_run(
        self,
        *,
        ticket_id: str,
        project_root: str,
        max_iterations: int,
        now: datetime | None = None,
    ) -> RepairRun:
        moment = now or utcnow()
        with self._lock:
            for run in self._runs.values():
                if run.ticket_id == ticket_id and run.project_root == project_root:
                    raise RunAlreadyExists(
                        f"a repair run for ticket {ticket_id} in {project_root} "
                        "already exists",
                    )
            run = RepairRun(
                id=new_id("run"),
                ticket_id=ticket_id,
                project_root=project_root,
                status="created",
                max_iterations=max_iterations,
                created_at=moment,
                updated_at=moment,
            )
            self._runs[run.id] = run
            return run

    def get_run(self, run_id: str) -> RepairRun | None:
        return self._runs.get(run_id)

    def find_run(self, ticket_id: str, project_root: str) -> RepairRun | None:
        for run in self._runs.values():
            if run.ticket_id == ticket_id and run.project_root == project_root:
                return run
        return None

    def transition(
        self,
        run_id: str,
        new_status: str,
        *,
        expected_version: int,
        now: datetime | None = None,
        current_iteration: int | None = None,
        base_head: str | None = None,
        manifest_hash: str | None = None,
        context_hash: str | None = None,
    ) -> RepairRun:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                raise UnknownRun(run_id)
            validate_transition(run.status, new_status)
            if run.version != expected_version:
                raise StaleVersion(
                    f"run {run_id} moved past version {expected_version}; "
                    "re-read and retry",
                )
            updated = replace(
                run,
                status=new_status,
                version=run.version + 1,
                updated_at=now or utcnow(),
                current_iteration=(
                    current_iteration
                    if current_iteration is not None
                    else run.current_iteration
                ),
                base_head=base_head if base_head is not None else run.base_head,
                manifest_hash=(
                    manifest_hash if manifest_hash is not None else run.manifest_hash
                ),
                context_hash=(
                    context_hash if context_hash is not None else run.context_hash
                ),
            )
            self._runs[run_id] = updated
            return updated

    # -- leasing ------------------------------------------------------------
    def claim(
        self,
        run_id: str,
        owner: str,
        *,
        lease_s: int,
        now: datetime | None = None,
    ) -> RepairRun | None:
        moment = now or utcnow()
        with self._lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            free = (
                run.lease_expires_at is None
                or run.lease_expires_at < moment
                or run.lease_owner == owner
            )
            if not free:
                return None
            updated = replace(
                run,
                lease_owner=owner,
                lease_expires_at=moment + timedelta(seconds=lease_s),
                version=run.version + 1,
                updated_at=moment,
            )
            self._runs[run_id] = updated
            return updated

    def release(self, run_id: str, owner: str) -> None:
        with self._lock:
            run = self._runs.get(run_id)
            if run is None or run.lease_owner != owner:
                return
            self._runs[run_id] = replace(
                run, lease_owner=None, lease_expires_at=None, version=run.version + 1,
            )

    # -- events -------------------------------------------------------------
    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict,
        *,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> RepairEvent:
        with self._lock:
            existing = self._events_by_key.get(idempotency_key)
            if existing is not None:
                return existing
            sequence = len(self._events.get(run_id, [])) + 1
            event = RepairEvent(
                id=sequence,
                run_id=run_id,
                sequence=sequence,
                event_type=event_type,
                payload=payload,
                idempotency_key=idempotency_key,
                created_at=now or utcnow(),
            )
            self._events.setdefault(run_id, []).append(event)
            self._events_by_key[idempotency_key] = event
            return event

    def events(self, run_id: str) -> list[RepairEvent]:
        return list(self._events.get(run_id, []))

    # -- model attempts -----------------------------------------------------
    def start_attempt(
        self,
        run_id: str,
        *,
        iteration: int,
        attempt: int,
        provider: str,
        model: str,
        input_hash: str,
        now: datetime | None = None,
    ) -> ModelAttempt:
        with self._lock:
            for record in self._attempts.get(run_id, []):
                if record.iteration == iteration and record.attempt == attempt:
                    raise ValueError(
                        f"attempt ({run_id}, {iteration}, {attempt}) already recorded",
                    )
            record = ModelAttempt(
                id=new_id("att"),
                run_id=run_id,
                iteration=iteration,
                attempt=attempt,
                provider=provider,
                model=model,
                status="running",
                input_hash=input_hash,
                started_at=now or utcnow(),
            )
            self._attempts.setdefault(run_id, []).append(record)
            return record

    def finish_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        failure_code: str | None = None,
        output_hash: str | None = None,
        now: datetime | None = None,
    ) -> None:
        with self._lock:
            for records in self._attempts.values():
                for index, record in enumerate(records):
                    if record.id == attempt_id:
                        records[index] = replace(
                            record,
                            status=status,
                            failure_code=failure_code,
                            output_hash=output_hash,
                            completed_at=now or utcnow(),
                        )
                        return

    def attempts(self, run_id: str) -> list[ModelAttempt]:
        return sorted(
            self._attempts.get(run_id, []), key=lambda a: (a.iteration, a.attempt),
        )

    # -- facts and artifacts ------------------------------------------------
    def put_fact(self, fact: RepairFact) -> RepairFact:
        with self._lock:
            for stored in self._facts.get(fact.run_id, []):
                if (
                    stored.schema_id == fact.schema_id
                    and stored.fact_key == fact.fact_key
                    and stored.value_hash == fact.value_hash
                ):
                    return stored
            self._facts.setdefault(fact.run_id, []).append(fact)
            return fact

    def facts(self, run_id: str, *, now: datetime | None = None) -> list[RepairFact]:
        moment = now or utcnow()
        return [
            fact
            for fact in self._facts.get(run_id, [])
            if fact.expires_at is None or fact.expires_at > moment
        ]

    def add_artifact(self, artifact: RepairArtifact) -> None:
        with self._lock:
            self._artifacts.setdefault(artifact.run_id, []).append(artifact)

    def artifacts(self, run_id: str) -> list[RepairArtifact]:
        return list(self._artifacts.get(run_id, []))

    # -- recovery -----------------------------------------------------------
    def resumable_runs(self, *, now: datetime | None = None) -> list[RepairRun]:
        moment = now or utcnow()
        return sorted(
            (
                run
                for run in self._runs.values()
                if run.status not in TERMINAL_STATES
                and (run.lease_expires_at is None or run.lease_expires_at < moment)
            ),
            key=lambda run: run.created_at,
        )
