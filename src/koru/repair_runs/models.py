"""Typed rows of the repair-run store.

These are records, not behaviour: the store persists them, the lifecycle
constrains them, and nothing here knows a model, a prompt or a workspace.
That ignorance is load-bearing — the store must survive any change of
provider, router or context strategy without a schema migration.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from uuid import uuid4


def utcnow() -> datetime:
    return datetime.now(UTC)


def new_id(prefix: str) -> str:
    return f"{prefix}_{uuid4().hex[:16]}"


def stable_hash(value: object) -> str:
    """Canonical sha256 of a JSON-serialisable value."""
    payload = json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class RepairRun:
    """The durable identity of one repair: everything else hangs off it."""

    id: str
    ticket_id: str
    project_root: str
    status: str
    max_iterations: int
    current_iteration: int = 0
    base_head: str | None = None
    manifest_hash: str | None = None
    context_hash: str | None = None
    lease_owner: str | None = None
    lease_expires_at: datetime | None = None
    version: int = 1
    created_at: datetime = field(default_factory=utcnow)
    updated_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class RepairEvent:
    """One appended fact about a run. Sequence and idempotency key are law."""

    run_id: str
    sequence: int
    event_type: str
    payload: dict
    idempotency_key: str
    created_at: datetime = field(default_factory=utcnow)
    id: int | None = None


@dataclass(frozen=True)
class ModelAttempt:
    """One model invocation. A blocked provider is a failed attempt, not a failed run."""

    id: str
    run_id: str
    iteration: int
    attempt: int
    provider: str
    model: str
    status: str  # running | succeeded | failed | interrupted
    input_hash: str
    failure_code: str | None = None
    output_hash: str | None = None
    started_at: datetime = field(default_factory=utcnow)
    completed_at: datetime | None = None


@dataclass(frozen=True)
class RepairFact:
    """A typed observation the Context Broker collected — never a raw log."""

    id: str
    run_id: str
    schema_id: str
    fact_key: str
    value: dict
    source: str
    value_hash: str
    observed_at: datetime = field(default_factory=utcnow)
    expires_at: datetime | None = None
    #: How much the observing capability vouches for the value. Deliberately
    #: outside ``value`` (and its hash): same value, different confidence,
    #: same identity.
    confidence: float = 1.0

    @classmethod
    def observed(
        cls,
        run_id: str,
        *,
        schema_id: str,
        fact_key: str,
        value: dict,
        source: str,
        expires_at: datetime | None = None,
        confidence: float = 1.0,
    ) -> RepairFact:
        return cls(
            id=new_id("fact"),
            run_id=run_id,
            schema_id=schema_id,
            fact_key=fact_key,
            value=value,
            source=source,
            value_hash=stable_hash(value),
            expires_at=expires_at,
            confidence=confidence,
        )


@dataclass(frozen=True)
class RepairArtifact:
    """A pointer to a large by-product (patch, verify output), hashed for evidence."""

    id: str
    run_id: str
    kind: str
    artifact_ref: str
    sha256: str
    created_at: datetime = field(default_factory=utcnow)


@dataclass(frozen=True)
class UsedGrant:
    """A signed apply-grant consumed by a run. UNIQUE(grant_jti) makes replay
    a database impossibility, surviving restarts that in-memory state would lose."""

    id: str
    run_id: str
    grant_jti: str
    grant_hash: str
    used_at: datetime = field(default_factory=utcnow)

    @classmethod
    def consumed(cls, run_id: str, *, grant_jti: str, grant_body: object) -> UsedGrant:
        return cls(
            id=new_id("grant"),
            run_id=run_id,
            grant_jti=grant_jti,
            grant_hash=stable_hash(grant_body),
        )
