"""Durable repair-run state: SQLite-backed, lease-guarded, replay-safe.

The store knows nothing about models, prompts or workspaces — it records what
a repair run *is* (identity, status, lease), what happened to it (events with
idempotency keys), what was tried (model attempts) and what was learned
(typed facts). Everything that talks to an LLM or mutates a checkout lives
elsewhere and leaves its trace here.
"""

from __future__ import annotations

from koru.repair_runs.lifecycle import (
    RESUMABLE_STATES,
    TERMINAL_STATES,
    RepairLifecycleViolation,
    is_valid_transition,
    validate_transition,
)
from koru.repair_runs.models import (
    ModelAttempt,
    RepairArtifact,
    RepairEvent,
    RepairFact,
    RepairRun,
    new_id,
    stable_hash,
    utcnow,
)

__all__ = [
    "RESUMABLE_STATES",
    "TERMINAL_STATES",
    "ModelAttempt",
    "RepairArtifact",
    "RepairEvent",
    "RepairFact",
    "RepairLifecycleViolation",
    "RepairRun",
    "is_valid_transition",
    "new_id",
    "stable_hash",
    "utcnow",
    "validate_transition",
]
