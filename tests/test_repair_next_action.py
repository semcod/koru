"""The koru.repair.next-action/v1 contract: the type is the permission.

Parser tests prove the closed set holds under hostile input; the session
tests prove the plan's loops end to end — request_fact → probe → fresh
snapshot → patch from the same model, and garbage → invalid_structured_output
→ the router's next model, all on one run and one ledger.
"""

from __future__ import annotations

import json
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.memory_store import MemoryRepairRunStore
from koru.repair_runs.models import RepairFact
from koru.repair_runs.next_action import (
    NEXT_ACTION_SCHEMA,
    NextAction,
    NextActionError,
    parse_next_action,
)

_PATCH = (
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
)


def _payload(**overrides) -> str:
    body = {
        "schema": NEXT_ACTION_SCHEMA,
        "action": "propose_patch",
        "reason_code": "implementation_ready",
        "required_facts": [],
        "patch": _PATCH,
        "confidence": 0.91,
    }
    body.update(overrides)
    return json.dumps(body)


class TestParser(unittest.TestCase):
    def test_a_valid_propose_patch_parses(self) -> None:
        parsed = parse_next_action(_payload())

        assert isinstance(parsed, NextAction)
        self.assertEqual(parsed.action, "propose_patch")
        self.assertEqual(parsed.patch, _PATCH)
        self.assertEqual(parsed.confidence, 0.91)

    def test_fenced_json_is_unwrapped(self) -> None:
        parsed = parse_next_action(f"```json\n{_payload()}\n```")

        assert isinstance(parsed, NextAction)

    def test_actions_outside_the_closed_set_die_at_the_boundary(self) -> None:
        """`run_shell` is not refused by policy — it is unrepresentable."""
        for action in ("run_shell", "git_commit", "change_policy", "widen_scope"):
            with self.subTest(action=action):
                parsed = parse_next_action(_payload(action=action, patch=None))
                assert isinstance(parsed, NextActionError)
                self.assertEqual(parsed.failure_code, "invalid_structured_output")

    def test_smuggled_keys_are_dropped_into_a_void(self) -> None:
        raw = json.loads(_payload())
        raw["command"] = "rm -rf /"
        raw["promotion_mode"] = "commit"

        parsed = parse_next_action(json.dumps(raw))

        assert isinstance(parsed, NextAction)
        self.assertFalse(hasattr(parsed, "command"))
        self.assertEqual(
            set(parsed.__dataclass_fields__),
            {"action", "reason_code", "required_facts", "patch", "confidence"},
        )

    def test_prose_is_invalid_structured_output_never_parsed(self) -> None:
        parsed = parse_next_action("Sure! Here's my patch:\n" + _PATCH)

        assert isinstance(parsed, NextActionError)

    def test_propose_patch_without_a_diff_is_refused(self) -> None:
        parsed = parse_next_action(_payload(patch="just some prose"))

        assert isinstance(parsed, NextActionError)

    def test_a_patch_on_a_non_patch_action_is_refused(self) -> None:
        """declare_no_patch carrying a patch is a contradiction, not a bonus."""
        parsed = parse_next_action(_payload(action="declare_no_patch"))

        assert isinstance(parsed, NextActionError)

    def test_request_fact_requires_facts_and_confidence_is_clamped(self) -> None:
        refused = parse_next_action(
            _payload(action="request_fact", patch=None, required_facts=[]),
        )
        assert isinstance(refused, NextActionError)

        ok = parse_next_action(
            _payload(
                action="request_fact",
                patch=None,
                required_facts=[{"schema": "s/v1", "key": "k"}],
                confidence=7,
            ),
        )
        assert isinstance(ok, NextAction)
        self.assertEqual(ok.confidence, 1.0)


class _SessionLab(unittest.TestCase):
    _DOCROOT = "plesk.docroot.decision/v1"

    def _ticket(self, **inputs) -> dict:
        base = {"prompt": "fix it", "structured_output": True}
        base.update(inputs)
        return {"id": "NA-1", "inputs": base}

    def _begin(self, ticket, probes=None):
        from koru.queue.repair_recording import RepairRecordingSession

        self.store = MemoryRepairRunStore()
        session = RepairRecordingSession.begin(
            Path("/tmp/none"), ticket, "worker-a", store=self.store, probes=probes,
        )
        assert session is not None
        return session

    @staticmethod
    def _reply(stdout: str):
        return SimpleNamespace(returncode=0, stdout=stdout, stderr="", status_code=None)


class TestStructuredSession(_SessionLab):
    def test_propose_patch_hands_the_diff_to_the_queue_pipeline(self) -> None:
        session = self._begin(self._ticket())

        result = session.wrap_llm(lambda a, p: self._reply(_payload()))(
            {"prompt": "fix it"}, Path("/tmp/none"),
        )

        self.assertEqual(result.stdout, _PATCH, "stdout is now exactly the patch")
        [attempt] = self.store.attempts(session.run_id)
        self.assertEqual(attempt.status, "succeeded")

    def test_the_prompt_carries_the_contract(self) -> None:
        session = self._begin(self._ticket())
        seen: list[dict] = []

        def llm(action, project):
            seen.append(action)
            return self._reply(_payload())

        session.wrap_llm(llm)({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertIn(NEXT_ACTION_SCHEMA, seen[0]["prompt"])

    def test_request_fact_probes_and_reasks_the_same_model_with_fresh_facts(self) -> None:
        """The plan's loop: LLM → request_fact → probe → fact → new snapshot → LLM."""
        probes = {
            self._DOCROOT: lambda run_id, key: RepairFact.observed(
                run_id, schema_id=self._DOCROOT, fact_key=key,
                value={"decision": "refuse"}, source="plesk.site.query.docroot",
            ),
        }
        session = self._begin(self._ticket(), probes=probes)
        calls: list[dict] = []

        def llm(action, project):
            calls.append(action)
            if len(calls) == 1:
                return self._reply(
                    _payload(
                        action="request_fact",
                        patch=None,
                        required_facts=[
                            {"schema": self._DOCROOT, "key": "docs.subactor.com"},
                        ],
                    ),
                )
            return self._reply(_payload())

        result = session.wrap_llm(llm)({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertEqual(result.stdout, _PATCH)
        self.assertEqual(len(calls), 2)
        self.assertNotIn("context_facts", calls[0], "no facts existed yet")
        self.assertEqual(
            calls[1]["context_facts"]["facts"][0]["key"], "docs.subactor.com",
            "the second ask carried the freshly probed fact",
        )
        attempts = self.store.attempts(session.run_id)
        self.assertEqual([a.status for a in attempts], ["succeeded", "succeeded"])
        self.assertNotEqual(
            attempts[0].input_hash, attempts[1].input_hash,
            "the new snapshot changed the attempt's input identity",
        )

    def test_an_unanswerable_fact_request_ends_as_no_patch(self) -> None:
        session = self._begin(self._ticket())  # no probes registered

        result = session.wrap_llm(
            lambda a, p: self._reply(
                _payload(
                    action="request_fact",
                    patch=None,
                    required_facts=[{"schema": self._DOCROOT, "key": "x"}],
                ),
            ),
        )({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertTrue(result.stdout.startswith("NO-PATCH:"))

    def test_declare_no_patch_is_an_honest_no(self) -> None:
        session = self._begin(self._ticket())

        result = session.wrap_llm(
            lambda a, p: self._reply(
                _payload(action="declare_no_patch", patch=None,
                         reason_code="not_reproducible"),
            ),
        )({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertEqual(result.stdout, "NO-PATCH: not_reproducible")
        [attempt] = self.store.attempts(session.run_id)
        self.assertEqual(attempt.status, "succeeded", "an honest no is not a failure")


class TestStructuredRouting(_SessionLab):
    """Contract failures route like provider failures — same run, next model."""

    def _registry(self):
        from koru.repair_runs.router import ModelSpec

        return (
            ModelSpec(id="a", model="model/a"),
            ModelSpec(id="b", model="model/b"),
        )

    def test_garbage_from_model_a_routes_to_model_b(self) -> None:
        session = self._begin(self._ticket())
        session._registry = self._registry()

        def llm(action, project):
            if action["model"] == "model/a":
                return self._reply("I'd love to help! Here's what I think...")
            return self._reply(_payload())

        result = session.wrap_llm(llm)({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertEqual(result.stdout, _PATCH)
        attempts = self.store.attempts(session.run_id)
        self.assertEqual(
            [(a.model, a.failure_code) for a in attempts],
            [("model/a", "invalid_structured_output"), ("model/b", None)],
        )

    def test_retry_with_model_burns_the_abdicating_model(self) -> None:
        session = self._begin(self._ticket())
        session._registry = self._registry()

        def llm(action, project):
            if action["model"] == "model/a":
                return self._reply(
                    _payload(action="retry_with_model", patch=None,
                             reason_code="outside_my_competence"),
                )
            return self._reply(_payload())

        result = session.wrap_llm(llm)({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertEqual(result.stdout, _PATCH)
        attempts = self.store.attempts(session.run_id)
        self.assertEqual(attempts[0].failure_code, "model_declined")
        self.assertEqual(attempts[1].model, "model/b")

    def test_every_model_emitting_garbage_parks_safe_blocked(self) -> None:
        session = self._begin(self._ticket())
        session._registry = self._registry()

        result = session.wrap_llm(
            lambda a, p: self._reply("prose forever"),
        )({"prompt": "fix it"}, Path("/tmp/none"))

        self.assertEqual(result.returncode, 1)
        run = self.store.get_run(session.run_id)
        assert run is not None
        self.assertEqual(run.status, lc.SAFE_BLOCKED)


if __name__ == "__main__":
    unittest.main()
