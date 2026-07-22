"""Contract tests for the repair-run store, run against both backends.

Every test in the contract mixin runs unchanged on SQLite and in memory: if a
promise holds in one and not the other, the contract is ambiguous, and the
ambiguity — not the backend — is the bug. The scenarios come straight from
the plan's acceptance list: two workers, expired leases, replayed events,
restart visibility.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.memory_store import MemoryRepairRunStore
from koru.repair_runs.models import RepairArtifact, RepairFact, new_id
from koru.repair_runs.sqlite_store import SqliteRepairRunStore
from koru.repair_runs.store import RunAlreadyExists, StaleVersion

_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)


class _StoreContract:
    """The promises. Subclasses provide ``self.store``."""

    def _run(self, ticket="T-1", root="/w/a"):
        return self.store.create_run(
            ticket_id=ticket, project_root=root, max_iterations=3, now=_NOW,
        )

    # -- identity -----------------------------------------------------------
    def test_one_live_repair_per_ticket_and_root(self) -> None:
        self._run()

        with self.assertRaises(RunAlreadyExists):
            self._run()
        # A different checkout of the same ticket is a different repair.
        self.store.create_run(
            ticket_id="T-1", project_root="/w/b", max_iterations=3, now=_NOW,
        )

    # -- status -------------------------------------------------------------
    def test_transitions_validate_the_lifecycle(self) -> None:
        run = self._run()

        from koru.repair_runs import RepairLifecycleViolation

        with self.assertRaises(RepairLifecycleViolation):
            self.store.transition(
                run.id, lc.PROMOTED, expected_version=run.version, now=_NOW,
            )

    def test_optimistic_version_stops_the_second_writer(self) -> None:
        run = self._run()

        self.store.transition(
            run.id, lc.CONTEXT_REQUIRED, expected_version=run.version, now=_NOW,
        )

        with self.assertRaises(StaleVersion):
            self.store.transition(
                run.id, lc.CONTEXT_READY, expected_version=run.version, now=_NOW,
            )

    def test_transition_can_carry_run_facts(self) -> None:
        run = self._run()

        updated = self.store.transition(
            run.id, lc.CONTEXT_REQUIRED, expected_version=run.version,
            manifest_hash="mh-1", current_iteration=1, now=_NOW,
        )

        self.assertEqual(updated.manifest_hash, "mh-1")
        self.assertEqual(updated.current_iteration, 1)
        self.assertEqual(updated.version, run.version + 1)

    # -- leasing ------------------------------------------------------------
    def test_only_one_worker_holds_the_lease(self) -> None:
        run = self._run()

        first = self.store.claim(run.id, "worker-a", lease_s=60, now=_NOW)
        second = self.store.claim(run.id, "worker-b", lease_s=60, now=_NOW)

        self.assertIsNotNone(first)
        self.assertIsNone(second, "two owners would mean two promoted patches")

    def test_the_owner_may_renew_its_own_lease(self) -> None:
        run = self._run()
        self.store.claim(run.id, "worker-a", lease_s=60, now=_NOW)

        renewed = self.store.claim(
            run.id, "worker-a", lease_s=60, now=_NOW + timedelta(seconds=30),
        )

        self.assertIsNotNone(renewed)

    def test_an_expired_lease_is_reclaimable_by_another_worker(self) -> None:
        run = self._run()
        self.store.claim(run.id, "worker-a", lease_s=60, now=_NOW)

        taken = self.store.claim(
            run.id, "worker-b", lease_s=60, now=_NOW + timedelta(seconds=61),
        )

        self.assertIsNotNone(taken)
        self.assertEqual(taken.lease_owner, "worker-b")

    def test_release_frees_the_run_only_for_its_owner(self) -> None:
        run = self._run()
        self.store.claim(run.id, "worker-a", lease_s=60, now=_NOW)

        self.store.release(run.id, "worker-b")  # not the owner — no-op
        self.assertIsNone(self.store.claim(run.id, "worker-b", lease_s=60, now=_NOW))

        self.store.release(run.id, "worker-a")
        self.assertIsNotNone(
            self.store.claim(run.id, "worker-b", lease_s=60, now=_NOW),
        )

    # -- events -------------------------------------------------------------
    def test_events_get_a_monotonic_per_run_sequence(self) -> None:
        run = self._run()

        for n in range(3):
            self.store.append_event(
                run.id, "step", {"n": n}, idempotency_key=f"k-{n}", now=_NOW,
            )

        self.assertEqual([e.sequence for e in self.store.events(run.id)], [1, 2, 3])

    def test_a_replayed_event_returns_the_original_instead_of_a_duplicate(self) -> None:
        run = self._run()
        first = self.store.append_event(
            run.id, "patch_staged", {"sha": "abc"}, idempotency_key="stage-1", now=_NOW,
        )

        replayed = self.store.append_event(
            run.id, "patch_staged", {"sha": "abc"}, idempotency_key="stage-1", now=_NOW,
        )

        self.assertEqual(replayed.sequence, first.sequence)
        self.assertEqual(len(self.store.events(run.id)), 1)

    # -- model attempts -----------------------------------------------------
    def test_a_blocked_attempt_survives_the_retry_that_followed_it(self) -> None:
        """The plan's core acceptance: one run, two attempts, both on record."""
        run = self._run()

        blocked = self.store.start_attempt(
            run.id, iteration=1, attempt=1, provider="openrouter",
            model="anthropic/claude", input_hash="in-1", now=_NOW,
        )
        self.store.finish_attempt(
            blocked.id, status="failed", failure_code="provider_policy_block", now=_NOW,
        )
        succeeded = self.store.start_attempt(
            run.id, iteration=1, attempt=2, provider="openrouter",
            model="openai/gpt", input_hash="in-1", now=_NOW,
        )
        self.store.finish_attempt(
            succeeded.id, status="succeeded", output_hash="out-1", now=_NOW,
        )

        records = self.store.attempts(run.id)
        self.assertEqual(len(records), 2)
        self.assertEqual(records[0].failure_code, "provider_policy_block")
        self.assertEqual(records[1].status, "succeeded")

    def test_the_same_attempt_slot_cannot_be_recorded_twice(self) -> None:
        run = self._run()
        self.store.start_attempt(
            run.id, iteration=1, attempt=1, provider="p", model="m",
            input_hash="in", now=_NOW,
        )

        with self.assertRaises(Exception):  # noqa: B017 — backend-specific error type
            self.store.start_attempt(
                run.id, iteration=1, attempt=1, provider="p", model="m2",
                input_hash="in", now=_NOW,
            )

    # -- facts --------------------------------------------------------------
    def test_facts_expire_and_identical_facts_deduplicate(self) -> None:
        run = self._run()
        live = RepairFact.observed(
            run.id, schema_id="s/v1", fact_key="k", value={"v": 1}, source="probe",
            expires_at=_NOW + timedelta(minutes=5),
        )
        stale = RepairFact.observed(
            run.id, schema_id="s/v1", fact_key="old", value={"v": 0}, source="probe",
            expires_at=_NOW - timedelta(minutes=5),
        )
        self.store.put_fact(live)
        self.store.put_fact(stale)
        self.store.put_fact(live)  # replay

        facts = self.store.facts(run.id, now=_NOW)

        self.assertEqual([f.fact_key for f in facts], ["k"])

    # -- artifacts ----------------------------------------------------------
    def test_artifacts_are_recorded(self) -> None:
        run = self._run()
        self.store.add_artifact(
            RepairArtifact(
                id=new_id("art"), run_id=run.id, kind="patch",
                artifact_ref=".koru/runs/x/patch.diff", sha256="deadbeef",
            ),
        )

        [artifact] = self.store.artifacts(run.id)
        self.assertEqual(artifact.kind, "patch")

    # -- grant replay protection --------------------------------------------
    def test_a_grant_jti_is_consumable_exactly_once(self) -> None:
        """The check and the record are one atomic step — replay is impossible."""
        from koru.repair_runs.models import UsedGrant
        from koru.repair_runs.store import GrantAlreadyUsed

        run = self._run()
        grant = UsedGrant.consumed(run.id, grant_jti="jti-1", grant_body={"m": "h"})

        self.store.record_grant_use(grant)

        self.assertTrue(self.store.is_grant_used("jti-1"))
        with self.assertRaises(GrantAlreadyUsed):
            self.store.record_grant_use(
                UsedGrant.consumed(run.id, grant_jti="jti-1", grant_body={"m": "h2"}),
            )
        [used] = self.store.used_grants(run.id)
        self.assertEqual(used.grant_jti, "jti-1")

    def test_an_unused_jti_reads_unused(self) -> None:
        self.assertFalse(self.store.is_grant_used("never-seen"))

    # -- recovery -----------------------------------------------------------
    def test_resumable_runs_are_nonterminal_with_dead_leases(self) -> None:
        active = self._run()
        self.store.claim(active.id, "worker-a", lease_s=60, now=_NOW)

        expired = self.store.create_run(
            ticket_id="T-2", project_root="/w/a", max_iterations=3, now=_NOW,
        )
        self.store.claim(expired.id, "worker-b", lease_s=10, now=_NOW)

        done = self.store.create_run(
            ticket_id="T-3", project_root="/w/a", max_iterations=3, now=_NOW,
        )
        done = self.store.transition(
            done.id, lc.CONTEXT_READY, expected_version=done.version, now=_NOW,
        )
        self.store.transition(
            done.id, lc.FAILED, expected_version=done.version, now=_NOW,
        )

        later = _NOW + timedelta(seconds=30)
        resumable = self.store.resumable_runs(now=later)

        self.assertEqual([run.ticket_id for run in resumable], ["T-2"])


class TestMemoryStore(_StoreContract, unittest.TestCase):
    def setUp(self) -> None:
        self.store = MemoryRepairRunStore()


class TestSqliteStore(_StoreContract, unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.store = SqliteRepairRunStore(Path(self._tmp.name) / "repair-runs.sqlite3")
        self.addCleanup(self.store.close)

    def test_state_survives_a_process_restart(self) -> None:
        """SQLite only: a new store instance over the same file sees everything."""
        path = Path(self._tmp.name) / "repair-runs.sqlite3"
        run = self._run()
        self.store.append_event(
            run.id, "patch_staged", {"sha": "abc"}, idempotency_key="k1", now=_NOW,
        )
        self.store.close()

        reopened = SqliteRepairRunStore(path)
        self.addCleanup(reopened.close)
        self.store = reopened

        survived = reopened.get_run(run.id)
        assert survived is not None
        self.assertEqual(survived.ticket_id, "T-1")
        self.assertEqual(len(reopened.events(run.id)), 1)
        # And the idempotency key still guards against replay after restart.
        replay = reopened.append_event(
            run.id, "patch_staged", {"sha": "abc"}, idempotency_key="k1", now=_NOW,
        )
        self.assertEqual(replay.sequence, 1)

    def test_a_consumed_grant_stays_consumed_across_a_restart(self) -> None:
        """SQLite only: the whole point of persisting used_grants — a grant used
        before a crash cannot be replayed by the worker that resumes the run."""
        from koru.repair_runs.models import UsedGrant
        from koru.repair_runs.store import GrantAlreadyUsed

        path = Path(self._tmp.name) / "repair-runs.sqlite3"
        run = self._run()
        self.store.record_grant_use(
            UsedGrant.consumed(run.id, grant_jti="apply-jti-9", grant_body={"n": 1}),
        )
        self.store.close()

        reopened = SqliteRepairRunStore(path)
        self.addCleanup(reopened.close)
        self.store = reopened

        self.assertTrue(reopened.is_grant_used("apply-jti-9"))
        with self.assertRaises(GrantAlreadyUsed):
            reopened.record_grant_use(
                UsedGrant.consumed(run.id, grant_jti="apply-jti-9", grant_body={"n": 2}),
            )


if __name__ == "__main__":
    unittest.main()
