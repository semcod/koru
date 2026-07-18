"""Repair-run models and lifecycle: the law before the machinery.

Commit 1 of the repair-run store: no store, no LLM — just the shapes and the
transition graph the rest will be held to.
"""

from __future__ import annotations

import unittest

from koru.repair_runs import (
    TERMINAL_STATES,
    RepairFact,
    RepairLifecycleViolation,
    is_valid_transition,
    stable_hash,
    validate_transition,
)
from koru.repair_runs import lifecycle as lc


class TestLifecycle(unittest.TestCase):
    def test_the_happy_path_is_legal_end_to_end(self) -> None:
        path = (
            lc.CREATED, lc.CONTEXT_REQUIRED, lc.CONTEXT_READY, lc.MODEL_RUNNING,
            lc.ACTION_PROPOSED, lc.ACTION_VALIDATED, lc.STAGING, lc.VERIFYING,
            lc.PROMOTED, lc.COMPLETED,
        )
        for current, requested in zip(path, path[1:], strict=False):
            with self.subTest(step=f"{current}->{requested}"):
                validate_transition(current, requested)

    def test_a_provider_block_routes_to_the_next_model_not_to_failed(self) -> None:
        """`provider_policy_block` is an operational event, not a verdict."""
        self.assertTrue(is_valid_transition(lc.MODEL_RUNNING, lc.MODEL_BLOCKED))
        self.assertTrue(is_valid_transition(lc.MODEL_BLOCKED, lc.MODEL_RUNNING))
        self.assertFalse(is_valid_transition(lc.MODEL_BLOCKED, lc.FAILED))
        self.assertFalse(is_valid_transition(lc.MODEL_BLOCKED, lc.COMPLETED))

    def test_exhausting_every_model_ends_safe_blocked_never_completed(self) -> None:
        """The alternative — do anything that closes the ticket — is the bug."""
        self.assertTrue(is_valid_transition(lc.MODEL_EXHAUSTED, lc.SAFE_BLOCKED))
        self.assertEqual(
            lc.TRANSITIONS[lc.MODEL_EXHAUSTED], frozenset({lc.SAFE_BLOCKED}),
        )

    def test_request_fact_loops_back_through_context(self) -> None:
        self.assertTrue(is_valid_transition(lc.ACTION_VALIDATED, lc.CONTEXT_REQUIRED))

    def test_a_failed_verify_opens_a_new_iteration_not_a_model_retry(self) -> None:
        self.assertTrue(is_valid_transition(lc.VERIFICATION_FAILED, lc.CONTEXT_REQUIRED))
        self.assertFalse(is_valid_transition(lc.VERIFICATION_FAILED, lc.MODEL_RUNNING))

    def test_terminal_states_go_nowhere(self) -> None:
        for state in TERMINAL_STATES:
            with self.subTest(state=state):
                self.assertEqual(lc.TRANSITIONS[state], frozenset())

    def test_an_illegal_jump_raises(self) -> None:
        with self.assertRaises(RepairLifecycleViolation):
            validate_transition(lc.CREATED, lc.PROMOTED)

    def test_every_declared_state_has_a_transition_entry(self) -> None:
        """A state outside the graph would dodge validation entirely."""
        declared = {
            getattr(lc, name)
            for name in dir(lc)
            if name.isupper() and isinstance(getattr(lc, name), str)
        }
        self.assertEqual(declared - set(lc.TRANSITIONS), set())


class TestFacts(unittest.TestCase):
    def test_observed_fact_hashes_its_value(self) -> None:
        fact = RepairFact.observed(
            "run_1",
            schema_id="plesk.docroot.decision/v1",
            fact_key="docs.subactor.com",
            value={"decision": "refuse"},
            source="plesk.site.query.docroot",
        )

        self.assertEqual(fact.value_hash, stable_hash({"decision": "refuse"}))
        self.assertTrue(fact.id.startswith("fact_"))

    def test_stable_hash_is_order_independent(self) -> None:
        self.assertEqual(
            stable_hash({"a": 1, "b": 2}), stable_hash({"b": 2, "a": 1}),
        )


if __name__ == "__main__":
    unittest.main()
