"""The Context Broker: typed facts in, one small snapshot out (commit 7).

The broker is the only path between the world and the model's context, and it
moves *facts*, never logs. A fact is a typed observation in the ``koru.fact/v1``
envelope — schema, key, structured value, the capability that observed it,
freshness and a hash. Terminal output has no way in: there is no API here that
accepts free text, which is the point.

The loop, per the plan: read the run's live facts, drop the expired (the store
already filters them — stale evidence is worse than none), run registered
probes for what is missing, build a small deterministic ``context_snapshot``,
record its hash durably (an idempotent ``context_snapshot_created`` event and
the run's ``context_hash``), and hand the snapshot to the caller. Probes are
*registered capabilities* — a fact schema maps to one deterministic callable;
neither a ticket nor a model can register one, so requesting a fact can never
become running a command.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime

from koru.repair_runs.models import RepairFact, RepairRun, stable_hash, utcnow
from koru.repair_runs.store import RepairRunStore

ENVELOPE_SCHEMA = "koru.fact/v1"

#: A probe observes one fact: (run_id, key) → RepairFact. Deterministic
#: capability, registered in code — never configured by a ticket or a model.
Probe = Callable[[str, str], RepairFact]


@dataclass(frozen=True)
class FactRequest:
    """What a repair iteration needs to know before a model runs."""

    fact_schema: str
    key: str


@dataclass(frozen=True)
class ContextSnapshot:
    """The small, hashed view of the world a model is allowed to see."""

    run_id: str
    facts: tuple[dict, ...]
    hash: str
    built_at: datetime

    def render(self) -> dict:
        """The exact payload handed to the model — envelopes, nothing else."""
        return {
            "schema": "koru.context-snapshot/v1",
            "run_id": self.run_id,
            "context_hash": self.hash,
            "facts": list(self.facts),
        }


@dataclass(frozen=True)
class MissingFacts:
    """Requests nothing could answer. The caller escalates; nothing is invented."""

    requests: tuple[FactRequest, ...]

    @property
    def reason(self) -> str:
        wanted = ", ".join(f"{r.fact_schema}[{r.key}]" for r in self.requests)
        return f"required facts have no live value and no registered probe: {wanted}"


def fact_envelope(fact: RepairFact, *, confidence: float = 1.0) -> dict:
    """One fact in the shared koru.fact/v1 envelope."""
    return {
        "schema": ENVELOPE_SCHEMA,
        "fact_schema": fact.schema_id,
        "key": fact.fact_key,
        "value": fact.value,
        "source": {"capability": fact.source, "authority": "observed"},
        "observed_at": fact.observed_at.isoformat(),
        "expires_at": fact.expires_at.isoformat() if fact.expires_at else None,
        "confidence": confidence,
        "hash": fact.value_hash,
    }


class ContextBroker:
    """Delivers facts to repair iterations; refuses to deliver anything else."""

    def __init__(
        self,
        store: RepairRunStore,
        probes: dict[str, Probe] | None = None,
    ) -> None:
        self._store = store
        self._probes = dict(probes or {})

    def ensure(
        self,
        run: RepairRun,
        required: list[FactRequest],
        *,
        now: datetime | None = None,
    ) -> ContextSnapshot | MissingFacts:
        """Make every required fact live, then freeze the snapshot.

        Probing writes through the store, so a fact observed for this
        iteration is durable before the model ever sees it — a crash between
        probe and model loses nothing. Unanswerable requests come back as
        ``MissingFacts``; the broker never guesses and never widens a probe's
        scope to cover a neighbour's request.
        """
        moment = now or utcnow()
        live = {
            (fact.schema_id, fact.fact_key): fact
            for fact in self._store.facts(run.id, now=moment)
        }

        unanswered: list[FactRequest] = []
        for request in required:
            if (request.fact_schema, request.key) in live:
                continue
            probe = self._probes.get(request.fact_schema)
            if probe is None:
                unanswered.append(request)
                continue
            observed = probe(run.id, request.key)
            stored = self._store.put_fact(observed)
            live[(stored.schema_id, stored.fact_key)] = stored
        if unanswered:
            return MissingFacts(tuple(unanswered))

        envelopes = tuple(
            fact_envelope(live[key])
            for key in sorted(live)  # deterministic order → deterministic hash
        )
        snapshot_hash = stable_hash([e["hash"] for e in envelopes])
        snapshot = ContextSnapshot(
            run_id=run.id, facts=envelopes, hash=snapshot_hash, built_at=moment,
        )
        # Durable before delivery: the hash names exactly what the model saw,
        # and replaying the same snapshot returns the same recorded event.
        self._store.append_event(
            run.id,
            "context_snapshot_created",
            {"context_hash": snapshot_hash, "fact_count": len(envelopes)},
            idempotency_key=f"ctx:{run.id}:{snapshot_hash}",
            now=moment,
        )
        return snapshot
