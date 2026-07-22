"""Commit 5: resuming repair runs after a restart.

Every scenario simulates the restart honestly: state is written through one
store instance, the "process" dies, and the sweep runs against a *new* store
instance over the same SQLite file — exactly what a rebooted worker sees.
"""

from __future__ import annotations

import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.models import stable_hash
from koru.repair_runs.resume import (
    COMPLETED_PROMOTION,
    NEXT_ITERATION,
    PARKED,
    RESUME_STAGING,
    RESUME_VERIFY,
    RETRY_MODEL,
    sweep_resumable,
)
from koru.repair_runs.sqlite_store import SqliteRepairRunStore

_NOW = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)
_AFTER_LEASE = _NOW + timedelta(seconds=999)


class TestResumeAfterRestart(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self._path = Path(self._tmp.name) / "repair-runs.sqlite3"
        self.store = SqliteRepairRunStore(self._path)
        self.addCleanup(self.store.close)

    def _restarted_store(self) -> SqliteRepairRunStore:
        """The process died; a new worker opens the same file."""
        self.store.close()
        reopened = SqliteRepairRunStore(self._path)
        self.addCleanup(reopened.close)
        self.store = reopened
        return reopened

    def _run_at(self, *statuses: str, ticket="T-1"):
        run = self.store.create_run(
            ticket_id=ticket, project_root="/w", max_iterations=5, now=_NOW,
        )
        self.store.claim(run.id, "worker-a", lease_s=60, now=_NOW)
        run = self.store.get_run(run.id)
        for status in statuses:
            run = self.store.transition(
                run.id, status, expected_version=run.version, now=_NOW,
            )
        return run

    def test_an_interrupted_model_attempt_is_closed_and_routed_to_the_next_model(self) -> None:
        """The plan's row: model_attempt_started without an end."""
        run = self._run_at(lc.CONTEXT_READY, lc.MODEL_RUNNING)
        self.store.start_attempt(
            run.id, iteration=1, attempt=1, provider="openrouter",
            model="anthropic/claude", input_hash=stable_hash("x"), now=_NOW,
        )

        store = self._restarted_store()
        [action] = sweep_resumable(store, now=_AFTER_LEASE)

        self.assertEqual(action.kind, RETRY_MODEL)
        self.assertEqual(action.status, lc.MODEL_BLOCKED)
        self.assertEqual(action.interrupted_attempts, 1)
        [attempt] = store.attempts(run.id)
        self.assertEqual(attempt.status, "interrupted")
        self.assertEqual(attempt.failure_code, "worker_died")

    def test_a_staged_patch_is_never_reapplied(self) -> None:
        run = self._run_at(
            lc.CONTEXT_READY, lc.MODEL_RUNNING, lc.ACTION_PROPOSED,
            lc.ACTION_VALIDATED, lc.STAGING,
        )

        [action] = sweep_resumable(self._restarted_store(), now=_AFTER_LEASE)

        self.assertEqual(action.run_id, run.id)
        self.assertEqual(action.kind, RESUME_STAGING)
        self.assertEqual(action.status, lc.STAGING, "classification only — no mutation")

    def test_a_verified_wait_resumes_at_verify(self) -> None:
        self._run_at(
            lc.CONTEXT_READY, lc.MODEL_RUNNING, lc.ACTION_PROPOSED,
            lc.ACTION_VALIDATED, lc.STAGING, lc.VERIFYING,
        )

        [action] = sweep_resumable(self._restarted_store(), now=_AFTER_LEASE)

        self.assertEqual(action.kind, RESUME_VERIFY)

    def test_a_promoted_run_is_completed_not_promoted_again(self) -> None:
        run = self._run_at(
            lc.CONTEXT_READY, lc.MODEL_RUNNING, lc.ACTION_PROPOSED,
            lc.ACTION_VALIDATED, lc.STAGING, lc.VERIFYING, lc.PROMOTED,
        )

        store = self._restarted_store()
        [action] = sweep_resumable(store, now=_AFTER_LEASE)

        self.assertEqual(action.kind, COMPLETED_PROMOTION)
        self.assertEqual(store.get_run(run.id).status, lc.COMPLETED)
        # And the next sweep has nothing to say about it.
        self.assertEqual(sweep_resumable(store, now=_AFTER_LEASE), [])

    def test_exhausted_models_park_the_run_safe_blocked(self) -> None:
        run = self._run_at(
            lc.CONTEXT_READY, lc.MODEL_RUNNING, lc.MODEL_BLOCKED, lc.MODEL_EXHAUSTED,
        )

        store = self._restarted_store()
        [action] = sweep_resumable(store, now=_AFTER_LEASE)

        self.assertEqual(action.kind, PARKED)
        self.assertEqual(store.get_run(run.id).status, lc.SAFE_BLOCKED)

    def test_verify_failure_and_drift_call_for_a_fresh_iteration(self) -> None:
        self._run_at(
            lc.CONTEXT_READY, lc.MODEL_RUNNING, lc.ACTION_PROPOSED,
            lc.ACTION_VALIDATED, lc.STAGING, lc.VERIFYING, lc.VERIFICATION_FAILED,
        )

        [action] = sweep_resumable(self._restarted_store(), now=_AFTER_LEASE)

        self.assertEqual(action.kind, NEXT_ITERATION)

    def test_a_live_lease_is_left_alone(self) -> None:
        """A run whose worker is alive is not this sweep's business."""
        self._run_at(lc.CONTEXT_READY, lc.MODEL_RUNNING)

        actions = sweep_resumable(self._restarted_store(), now=_NOW)  # lease still live

        self.assertEqual(actions, [])

    def test_the_sweep_is_idempotent(self) -> None:
        self._run_at(lc.CONTEXT_READY, lc.MODEL_RUNNING)
        store = self._restarted_store()

        first = sweep_resumable(store, now=_AFTER_LEASE)
        second = sweep_resumable(store, now=_AFTER_LEASE)

        self.assertEqual(first[0].status, lc.MODEL_BLOCKED)
        # Second sweep sees model_blocked, classifies it, heals nothing new.
        self.assertEqual(second[0].kind, RETRY_MODEL)
        self.assertEqual(second[0].status, lc.MODEL_BLOCKED)
        self.assertEqual(second[0].interrupted_attempts, 0)


if __name__ == "__main__":
    unittest.main()
