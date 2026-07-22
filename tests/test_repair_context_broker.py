"""Commit 7: the Context Broker — facts in envelopes, never logs.

The properties under test: the snapshot is deterministic and hashed, probing
is durable before delivery, unanswerable requests escalate instead of being
guessed, and a ticket that declared facts mandatory never reaches a model
without them.
"""

from __future__ import annotations

import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.context_broker import (
    ContextBroker,
    ContextSnapshot,
    FactRequest,
    MissingFacts,
    fact_envelope,
)
from koru.repair_runs.memory_store import MemoryRepairRunStore
from koru.repair_runs.models import RepairFact

_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)

_DOCROOT = "plesk.docroot.decision/v1"


def _fact(run_id: str, key="docs.subactor.com", value=None, expires=None, confidence=1.0):
    return RepairFact.observed(
        run_id,
        schema_id=_DOCROOT,
        fact_key=key,
        value=value or {"decision": "refuse", "expected_remote_path": f"/{key}"},
        source="plesk.site.query.docroot",
        expires_at=expires,
        confidence=confidence,
    )


class TestEnvelope(unittest.TestCase):
    def test_the_envelope_matches_the_plan_shape(self) -> None:
        fact = _fact("run_1", expires=_NOW + timedelta(minutes=5), confidence=0.9)

        envelope = fact_envelope(fact, confidence=fact.confidence)

        self.assertEqual(envelope["schema"], "koru.fact/v1")
        self.assertEqual(envelope["fact_schema"], _DOCROOT)
        self.assertEqual(envelope["key"], "docs.subactor.com")
        self.assertEqual(envelope["value"]["decision"], "refuse")
        self.assertEqual(
            envelope["source"],
            {"capability": "plesk.site.query.docroot", "authority": "observed"},
        )
        self.assertEqual(envelope["confidence"], 0.9)
        self.assertEqual(envelope["hash"], fact.value_hash)
        self.assertTrue(envelope["observed_at"])
        self.assertTrue(envelope["expires_at"])


class TestBroker(unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryRepairRunStore()
        self.run = self.store.create_run(
            ticket_id="T-1", project_root="/w", max_iterations=5, now=_NOW,
        )

    def _request(self, key="docs.subactor.com") -> FactRequest:
        return FactRequest(fact_schema=_DOCROOT, key=key)

    def test_live_facts_produce_a_deterministic_hashed_snapshot(self) -> None:
        self.store.put_fact(_fact(self.run.id, key="a.example"))
        self.store.put_fact(_fact(self.run.id, key="b.example"))
        broker = ContextBroker(self.store)

        first = broker.ensure(
            self.run, [self._request("a.example"), self._request("b.example")], now=_NOW,
        )
        second = broker.ensure(
            self.run, [self._request("b.example"), self._request("a.example")], now=_NOW,
        )

        assert isinstance(first, ContextSnapshot)
        assert isinstance(second, ContextSnapshot)
        self.assertEqual(first.hash, second.hash, "order must not change identity")
        self.assertEqual([f["key"] for f in first.facts], ["a.example", "b.example"])

    def test_the_snapshot_event_is_recorded_once_per_identity(self) -> None:
        self.store.put_fact(_fact(self.run.id))
        broker = ContextBroker(self.store)

        broker.ensure(self.run, [self._request()], now=_NOW)
        broker.ensure(self.run, [self._request()], now=_NOW)  # replay

        events = [
            e for e in self.store.events(self.run.id)
            if e.event_type == "context_snapshot_created"
        ]
        self.assertEqual(len(events), 1, "same snapshot, same recorded event")

    def test_an_expired_fact_triggers_the_probe_and_the_result_is_durable(self) -> None:
        """Durable before delivery: a crash between probe and model loses nothing."""
        self.store.put_fact(
            _fact(self.run.id, expires=_NOW - timedelta(minutes=1)),  # stale
        )
        probed: list[str] = []

        def docroot_probe(run_id: str, key: str) -> RepairFact:
            probed.append(key)
            return _fact(run_id, key=key, value={"decision": "allow"})

        broker = ContextBroker(self.store, {_DOCROOT: docroot_probe})

        snapshot = broker.ensure(self.run, [self._request()], now=_NOW)

        assert isinstance(snapshot, ContextSnapshot)
        self.assertEqual(probed, ["docs.subactor.com"])
        [fact] = self.store.facts(self.run.id, now=_NOW)
        self.assertEqual(fact.value["decision"], "allow", "probe result persisted")
        [rendered] = [
            f for f in snapshot.facts if f["value"]["decision"] == "allow"
        ]
        self.assertEqual(rendered["key"], "docs.subactor.com")

    def test_an_unanswerable_request_escalates_instead_of_guessing(self) -> None:
        broker = ContextBroker(self.store)  # no probes registered

        outcome = broker.ensure(self.run, [self._request()], now=_NOW)

        assert isinstance(outcome, MissingFacts)
        self.assertIn("plesk.docroot.decision/v1[docs.subactor.com]", outcome.reason)
        self.assertEqual(self.store.facts(self.run.id, now=_NOW), [], "nothing invented")

    def test_the_snapshot_render_is_envelopes_and_nothing_else(self) -> None:
        """No API here accepts free text — logs cannot reach the model."""
        self.store.put_fact(_fact(self.run.id))
        broker = ContextBroker(self.store)

        snapshot = broker.ensure(self.run, [self._request()], now=_NOW)

        assert isinstance(snapshot, ContextSnapshot)
        rendered = snapshot.render()
        self.assertEqual(rendered["schema"], "koru.context-snapshot/v1")
        self.assertEqual(rendered["context_hash"], snapshot.hash)
        for fact in rendered["facts"]:
            self.assertEqual(fact["schema"], "koru.fact/v1")
            self.assertIsInstance(fact["value"], dict)


class TestSessionIntegration(unittest.TestCase):
    """A ticket that declares facts mandatory never reaches a model without them."""

    def _ticket(self) -> dict:
        return {
            "id": "CB-1",
            "inputs": {
                "prompt": "fix the docroot",
                "required_facts": [{"schema": _DOCROOT, "key": "docs.subactor.com"}],
            },
        }

    def test_missing_facts_park_the_run_and_refuse_the_session(self) -> None:
        from koru.queue.repair_recording import RepairRecordingSession

        store = MemoryRepairRunStore()

        session = RepairRecordingSession.begin(
            Path("/tmp/none"), self._ticket(), "worker-a", store=store,
        )

        self.assertIsNone(session, "no session — the model must not run blind")
        run = store.find_run("CB-1", "/tmp/none")
        assert run is not None
        self.assertEqual(run.status, lc.PROBE_REQUIRED)
        self.assertIsNone(run.lease_owner, "the lease was given back")

    def test_delivered_facts_pin_the_hash_and_reach_every_model_call(self) -> None:
        from koru.queue.repair_recording import RepairRecordingSession

        store = MemoryRepairRunStore()
        probes = {
            _DOCROOT: lambda run_id, key: _fact(run_id, key=key),
        }

        session = RepairRecordingSession.begin(
            Path("/tmp/none"), self._ticket(), "worker-a", store=store, probes=probes,
        )

        assert session is not None
        run = store.get_run(session.run_id)
        assert run is not None
        self.assertEqual(run.status, lc.MODEL_RUNNING)
        self.assertTrue(run.context_hash, "snapshot hash pinned on the run")

        seen: list[dict] = []

        def llm(action, project):
            seen.append(action)
            from types import SimpleNamespace

            return SimpleNamespace(returncode=0, stdout="ok", stderr="", status_code=None)

        session.wrap_llm(llm)({"prompt": "fix the docroot"}, Path("/tmp/none"))

        [action] = seen
        self.assertEqual(
            action["context_facts"]["context_hash"], run.context_hash,
            "the model saw exactly the snapshot the run recorded",
        )
        [attempt] = store.attempts(run.id)
        self.assertTrue(attempt.input_hash, "context identity folded into the attempt")


if __name__ == "__main__":
    unittest.main()
