"""The repair-run store contract: what any backend must promise.

The store knows no models and no prompts. Its promises are structural:

- one live repair per (ticket, project root) — creation is first-writer-wins;
- status changes validate the lifecycle graph *and* an optimistic version, so
  two workers racing an update cannot both win;
- events append with a monotonic per-run sequence and a unique idempotency
  key — replaying a step returns the recorded event instead of a duplicate;
- a run is worked on only under a lease, claimed atomically, reclaimable only
  after expiry;
- model attempts are unique per (run, iteration, attempt) — the record of a
  blocked provider cannot be overwritten by the retry that followed it.

``memory_store`` exists so these promises are testable as a contract; SQLite
is the production backend.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import datetime

from koru.repair_runs.models import (
    ModelAttempt,
    RepairArtifact,
    RepairEvent,
    RepairFact,
    RepairRun,
    UsedGrant,
)


class RunAlreadyExists(Exception):
    """A live repair for this (ticket, project root) already exists."""


class UnknownRun(Exception):
    """No repair run with that id."""


class StaleVersion(Exception):
    """Someone else updated the run since it was read; re-read and retry."""


class GrantAlreadyUsed(Exception):
    """This apply-grant (by jti) was already consumed — a replay attempt."""


class RepairRunStore(ABC):
    """The contract. Every method is safe to call from a freshly restarted worker."""

    # -- runs ---------------------------------------------------------------
    @abstractmethod
    def create_run(
        self,
        *,
        ticket_id: str,
        project_root: str,
        max_iterations: int,
        now: datetime | None = None,
    ) -> RepairRun: ...

    @abstractmethod
    def get_run(self, run_id: str) -> RepairRun | None: ...

    @abstractmethod
    def find_run(self, ticket_id: str, project_root: str) -> RepairRun | None: ...

    @abstractmethod
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
    ) -> RepairRun: ...

    # -- leasing ------------------------------------------------------------
    @abstractmethod
    def claim(
        self,
        run_id: str,
        owner: str,
        *,
        lease_s: int,
        now: datetime | None = None,
    ) -> RepairRun | None:
        """Atomically take (or renew) the lease; ``None`` means someone else owns it."""

    @abstractmethod
    def release(self, run_id: str, owner: str) -> None: ...

    # -- events -------------------------------------------------------------
    @abstractmethod
    def append_event(
        self,
        run_id: str,
        event_type: str,
        payload: dict,
        *,
        idempotency_key: str,
        now: datetime | None = None,
    ) -> RepairEvent:
        """Append, or return the already-recorded event for this key."""

    @abstractmethod
    def events(self, run_id: str) -> list[RepairEvent]: ...

    # -- model attempts -----------------------------------------------------
    @abstractmethod
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
    ) -> ModelAttempt: ...

    @abstractmethod
    def finish_attempt(
        self,
        attempt_id: str,
        *,
        status: str,
        failure_code: str | None = None,
        output_hash: str | None = None,
        now: datetime | None = None,
    ) -> None: ...

    @abstractmethod
    def attempts(self, run_id: str) -> list[ModelAttempt]: ...

    # -- facts and artifacts ------------------------------------------------
    @abstractmethod
    def put_fact(self, fact: RepairFact) -> RepairFact:
        """Store, or return the identical already-stored fact (same value hash)."""

    @abstractmethod
    def facts(self, run_id: str, *, now: datetime | None = None) -> list[RepairFact]:
        """Live (unexpired) facts only — stale evidence is worse than none."""

    @abstractmethod
    def add_artifact(self, artifact: RepairArtifact) -> None: ...

    @abstractmethod
    def artifacts(self, run_id: str) -> list[RepairArtifact]: ...

    # -- grant replay protection --------------------------------------------
    @abstractmethod
    def record_grant_use(self, grant: UsedGrant) -> None:
        """Record that a grant (by jti) was consumed. Raises GrantAlreadyUsed
        on replay — the check and the record are one atomic step."""

    @abstractmethod
    def is_grant_used(self, grant_jti: str) -> bool: ...

    @abstractmethod
    def used_grants(self, run_id: str) -> list[UsedGrant]: ...

    # -- recovery -----------------------------------------------------------
    @abstractmethod
    def resumable_runs(self, *, now: datetime | None = None) -> list[RepairRun]:
        """Non-terminal runs whose lease is absent or expired — restart work."""
