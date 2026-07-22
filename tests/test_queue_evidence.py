"""The evidence bundle: one JSON artifact that proves what a patch run did.

The contract under test, from the autonomy plan: every run leaves a bundle,
retries never erase their predecessors' patch hashes, secrets never reach the
record, and a landed patch that cannot prove itself may not close its ticket.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from koru.queue.evidence import (
    VERDICT_REFUSED,
    VERDICT_VERIFIED,
    completion_gap,
    load_evidence,
)
from koru.queue.patch_retry import apply_patch_with_retry
from tests import _repolab

_GOOD_REPLY = (
    "```diff\n"
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1 +1 @@\n"
    "-old\n"
    "+new\n"
    "```\n"
)

#: Written against contents the file does not have, so `git apply` rejects it —
#: the mechanical, retryable failure the retry loop exists for.
_STALE_REPLY = (
    "```diff\n"
    "diff --git a/a.txt b/a.txt\n"
    "--- a/a.txt\n"
    "+++ b/a.txt\n"
    "@@ -1 +1 @@\n"
    "-something that was never there\n"
    "+new\n"
    "```\n"
)


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _ticket_args(command) -> list[str]:
    """Strip the interpreter prefix planfile_command puts before ``ticket``."""
    args = [str(part) for part in command]
    return args[args.index("ticket"):] if "ticket" in args else args


class _RepoCase(unittest.TestCase):
    def _git_repo(self, tmp: str) -> Path:
        return _repolab.git_repo(tmp)

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        _repolab.commit_file(project, rel, body)

    def _gate_ok(self, command: str, cwd: Path):
        return _reply()

    def _run(self, project: Path, agent_reply, ticket: dict, gate, llm=None):
        return apply_patch_with_retry(
            project,
            agent_reply,
            ticket,
            {"prompt": "x"},
            llm or (lambda action, p: _reply(returncode=1)),
            gate,
        )


class TestBundleContents(_RepoCase):
    def test_a_landed_patch_leaves_a_verified_bundle_beside_its_manifest(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-1", "inputs": {"verify_command": "true"}}

            _result, outcome, bundle = self._run(
                project, _reply(stdout=_GOOD_REPLY), ticket, self._gate_ok,
            )

            self.assertIsNone(outcome, outcome)
            assert bundle is not None
            self.assertEqual(bundle["verdict"], VERDICT_VERIFIED)
            self.assertEqual(bundle["ticket_id"], "EV-1")
            run_dir = project / ".koru" / "runs" / bundle["run_id"]
            manifest = json.loads((run_dir / "manifest.json").read_text(encoding="utf-8"))
            persisted = json.loads((run_dir / "evidence.json").read_text(encoding="utf-8"))
            # The bundle and the manifest vouch for each other.
            self.assertEqual(persisted["manifest_hash"], manifest["manifest_hash"])
            self.assertEqual(persisted["base_head"], manifest["base_head"])
            self.assertEqual(
                persisted["workspace_snapshot"], manifest["workspace_snapshot_sha256"],
            )
            [attempt] = persisted["patch_attempts"]
            self.assertEqual(attempt["outcome"], "landed")
            self.assertEqual(attempt["patch_sha256"], manifest["patch_sha256"])
            self.assertEqual(persisted["verify"]["command"], "true")
            self.assertEqual(persisted["verify"]["source"], "legacy")

    def test_a_retry_keeps_both_patch_shas_in_one_run(self) -> None:
        """The record of a failed attempt must survive the attempt that fixed it."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-2", "inputs": {"verify_command": "true"}}

            def corrected_agent(action, p):
                return _reply(stdout=_GOOD_REPLY)

            _result, outcome, bundle = self._run(
                project, _reply(stdout=_STALE_REPLY), ticket, self._gate_ok, llm=corrected_agent,
            )

            self.assertIsNone(outcome, outcome)
            assert bundle is not None
            first, second = bundle["patch_attempts"]
            self.assertEqual(first["outcome"], "patch_does_not_apply")
            self.assertTrue(first["retryable"])
            self.assertEqual(second["outcome"], "landed")
            self.assertIsNotNone(first["patch_sha256"])
            self.assertIsNotNone(second["patch_sha256"])
            self.assertNotEqual(first["patch_sha256"], second["patch_sha256"])
            # One logical run — one directory holding manifest and evidence both.
            self.assertEqual(bundle["verdict"], VERDICT_VERIFIED)
            run_dir = project / ".koru" / "runs" / bundle["run_id"]
            self.assertTrue((run_dir / "manifest.json").is_file())
            self.assertTrue((run_dir / "evidence.json").is_file())

    def test_a_refused_run_documents_its_refusal(self) -> None:
        """Every status has evidence — failure is a first-class outcome."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-3", "inputs": {"verify_command": "false"}}

            def failing_gate(command: str, cwd: Path):
                return _reply(returncode=1, stderr="assertion blew up")

            _result, outcome, bundle = self._run(
                project, _reply(stdout=_GOOD_REPLY), ticket, failing_gate,
            )

            self.assertIsNotNone(outcome)
            assert bundle is not None
            self.assertEqual(bundle["verdict"], VERDICT_REFUSED)
            [attempt] = bundle["patch_attempts"]
            self.assertEqual(attempt["outcome"], "verify_baseline_failed")
            self.assertIn("assertion blew up", attempt["message"])

    def test_secrets_in_gate_output_never_reach_the_evidence(self) -> None:
        """Evidence outlives the run on disk; a leaked key there costs the most."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {
                "id": "EV-4",
                "labels": ["type:development-defect"],  # skip baseline: judge the patch
                "inputs": {"verify_command": "false"},
            }
            secret = "sk-live-abcdef1234567890"

            def leaky_gate(command: str, cwd: Path):
                return _reply(returncode=1, stderr=f"OPENAI_API_KEY={secret} rejected")

            _result, _outcome, bundle = self._run(
                project, _reply(stdout=_GOOD_REPLY), ticket, leaky_gate,
            )

            assert bundle is not None
            serialized = json.dumps(bundle)
            self.assertNotIn(secret, serialized)
            self.assertIn("[redacted]", serialized)
            persisted = load_evidence(project, bundle["run_id"])
            assert persisted is not None
            self.assertNotIn(secret, json.dumps(persisted))


class TestCompletionGap(_RepoCase):
    def test_no_bundle_at_all_is_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            self.assertIsNotNone(completion_gap(self._git_repo(tmp), None))

    def test_a_bundle_that_never_reached_disk_is_a_gap(self) -> None:
        """The auditor reads disk, so disk is what gates — memory does not count."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-5", "inputs": {"verify_command": "true"}}

            with mock.patch(
                "koru.queue.patch_retry.persist_evidence", side_effect=OSError("read-only"),
            ):
                _result, outcome, bundle = self._run(
                    project, _reply(stdout=_GOOD_REPLY), ticket, self._gate_ok,
                )

            self.assertIsNone(outcome, "the patch itself landed")
            gap = completion_gap(project, bundle)
            assert gap is not None
            self.assertIn("not persisted", gap)

    def test_a_persisted_valid_bundle_passes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-6", "inputs": {"verify_command": "true"}}

            _result, _outcome, bundle = self._run(
                project, _reply(stdout=_GOOD_REPLY), ticket, self._gate_ok,
            )

            self.assertIsNone(completion_gap(project, bundle))

    def test_a_success_verdict_without_a_frozen_manifest_is_a_gap(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "EV-7", "inputs": {"verify_command": "true"}}
            _result, _outcome, bundle = self._run(
                project, _reply(stdout=_GOOD_REPLY), ticket, self._gate_ok,
            )
            assert bundle is not None
            path = project / ".koru" / "runs" / bundle["run_id"] / "evidence.json"
            doctored = json.loads(path.read_text(encoding="utf-8"))
            doctored["manifest_hash"] = None
            path.write_text(json.dumps(doctored), encoding="utf-8")

            gap = completion_gap(project, bundle)

            assert gap is not None
            self.assertIn("no frozen manifest", gap)


class TestRunnerCompletionGate(_RepoCase):
    """`completed` without persisted evidence is impossible, end to end."""

    def _ticket(self) -> dict:
        return {
            "id": "EV-RUN-1",
            "name": "patch a.txt",
            "executor": {"kind": "llm", "mode": "automatic"},
            "labels": ["refactor"],  # expects edits → patch mode
            "files": ["a.txt"],
            "inputs": {"prompt": "change old to new", "verify_command": "true"},
        }

    def _drive(self, project: Path) -> tuple[object, list[list[str]]]:
        from koru.queue.runner import run_next_planfile_task

        ticket = self._ticket()
        calls: list[list[str]] = []

        def planfile_runner(command, _project):
            args = _ticket_args(command)
            calls.append(args)
            if args[:4] == ["ticket", "list", "--status", "open"]:
                return _reply(stdout=json.dumps(ticket))
            return _reply()

        def llm_runner(request, _project):
            return _reply(stdout=_GOOD_REPLY)

        result = run_next_planfile_task(
            project=project,
            actor="koru-test",
            planfile_runner=planfile_runner,
            llm_runner=llm_runner,
            shell_runner=self._gate_ok,
        )
        return result, calls

    def _lifecycle(self, calls: list[list[str]]) -> list[str]:
        return [
            args[1]
            for args in calls
            if len(args) > 1 and args[0] == "ticket" and args[1] in {"done", "block"}
        ]

    def test_a_provable_run_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            result, calls = self._drive(project)

            self.assertEqual(result.status, "completed")
            self.assertEqual(self._lifecycle(calls), ["done"])

    def test_an_unprovable_run_is_blocked_not_completed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            with mock.patch(
                "koru.queue.patch_retry.persist_evidence", side_effect=OSError("read-only"),
            ):
                result, calls = self._drive(project)

            self.assertEqual(result.status, "failed")
            self.assertEqual(self._lifecycle(calls), ["block"])
            block = next(args for args in calls if len(args) > 1 and args[1] == "block")
            self.assertIn("evidence_incomplete", " ".join(str(a) for a in block))


if __name__ == "__main__":
    unittest.main()


class TestProvenance:
    """P0-4: the bundle answers *who proposed* without loop logs."""

    def _reply(self, **raw):
        from types import SimpleNamespace

        return SimpleNamespace(returncode=0, stdout="", stderr="", raw=raw, model="")

    def test_non_llm_result_yields_none(self):
        from types import SimpleNamespace

        from koru.queue.evidence import provenance_from_result

        assert provenance_from_result(SimpleNamespace(returncode=0)) is None
        assert provenance_from_result(self._reply()) is None

    def test_provider_model_and_queue_are_recorded(self):
        from koru.queue.evidence import provenance_from_result

        provenance = provenance_from_result(
            self._reply(provider="z.ai", model="glm-5.2", provider_attempts=["z.ai"])
        )
        assert provenance == {
            "provider": "z.ai",
            "model": "glm-5.2",
            "provider_attempts": ["z.ai"],
        }

    def test_fallback_reason_names_the_skipped_providers(self):
        from koru.queue.evidence import provenance_from_result

        provenance = provenance_from_result(
            self._reply(
                provider="minimax",
                model="MiniMax-M2",
                provider_attempts=["subscription", "z.ai", "minimax"],
            )
        )
        assert provenance["fallback"] == (
            "subscription → z.ai unavailable/exhausted; served by minimax"
        )

    def test_bundle_carries_provenance(self):
        from koru.queue.evidence import build_evidence_bundle, provenance_from_result

        bundle = build_evidence_bundle(
            run_id="run-1",
            ticket={"id": "PLF-1"},
            manifest=None,
            patch_attempts=[{"attempt": 1}],
            verify={},
            promotion={},
            verdict="refused",
            provenance=provenance_from_result(
                self._reply(provider="z.ai", provider_attempts=["z.ai"])
            ),
        )
        assert bundle["provenance"]["provider"] == "z.ai"


class TestBindings:
    """P0-4: the hash ladder starts at the proposal, recorded in the bundle."""

    def test_bundle_carries_envelope_bindings(self):
        from koru.queue.evidence import build_evidence_bundle

        bindings = {
            "intent_pack": {"id": "koru.patch", "version": "1.0"},
            "input_hash": "a" * 64,
            "prompt_schema_hash": "b" * 64,
            "artifact_sha256": "c" * 64,
            "proposal_sha256": "d" * 64,
        }
        bundle = build_evidence_bundle(
            run_id="run-2",
            ticket={"id": "PLF-2"},
            manifest=None,
            patch_attempts=[{"attempt": 1}],
            verify={},
            promotion={},
            verdict="refused",
            bindings=bindings,
        )
        assert bundle["bindings"]["proposal_sha256"] == "d" * 64
        assert bundle["bindings"]["intent_pack"]["id"] == "koru.patch"

    def test_legacy_bare_diff_run_has_null_bindings(self):
        from koru.queue.evidence import build_evidence_bundle

        bundle = build_evidence_bundle(
            run_id="run-3",
            ticket={"id": "PLF-3"},
            manifest=None,
            patch_attempts=[{"attempt": 1}],
            verify={},
            promotion={},
            verdict="refused",
        )
        assert bundle["bindings"] is None


class TestHashLadder:
    """P0-4: the bundle's lower rungs are recomputable by an auditor."""

    def _bundle(self, *, verify=None, verdict="refused", bindings=None):
        from koru.queue.evidence import build_evidence_bundle

        return build_evidence_bundle(
            run_id="run-h",
            ticket={"id": "PLF-9"},
            manifest={"manifest_hash": "m" * 64},
            patch_attempts=[{"attempt": 1}],
            verify=verify or {},
            promotion={"mode": "branch", "isolated": True},
            verdict=verdict,
            bindings=bindings,
        )

    def test_hashes_are_deterministic(self):
        verify = {"command": "pytest -q", "status": "passed"}
        first = self._bundle(verify=verify)
        second = self._bundle(verify=verify)
        assert first["verification_hash"] == second["verification_hash"]
        assert first["execution_binding_hash"] == second["execution_binding_hash"]

    def test_changing_the_gate_changes_both_hashes(self):
        green = self._bundle(verify={"command": "pytest -q", "status": "passed"})
        red = self._bundle(verify={"command": "pytest -q", "status": "failed"})
        assert green["verification_hash"] != red["verification_hash"]
        assert green["execution_binding_hash"] != red["execution_binding_hash"]

    def test_no_gate_means_no_verification_hash_but_binding_still_exists(self):
        bundle = self._bundle(verify=None)
        assert bundle["verification_hash"] is None
        assert isinstance(bundle["execution_binding_hash"], str)

    def test_binding_covers_the_proposal(self):
        with_proposal = self._bundle(
            bindings={"proposal_sha256": "d" * 64}
        )
        without = self._bundle()
        assert (
            with_proposal["execution_binding_hash"]
            != without["execution_binding_hash"]
        )

    def test_versions_recorded(self):
        bundle = self._bundle()
        versions = bundle["versions"]
        assert versions["evidence_schema"] == 1
        assert versions["proposal_schema"] == "1.0"
        assert versions["koru"] and versions["koru"] != "unknown"


class TestAuthorizationInBundle:
    def test_binding_hash_covers_the_grant(self):
        from koru.queue.evidence import build_evidence_bundle

        def bundle(auth):
            return build_evidence_bundle(
                run_id="run-a",
                ticket={"id": "PLF-A"},
                manifest={"manifest_hash": "m" * 64},
                patch_attempts=[{"attempt": 1}],
                verify={},
                promotion={},
                verdict="refused",
                authorization=auth,
            )

        granted = bundle({"jti": "j-1", "capabilities": ["code.patch.stage"]})
        legacy = bundle(None)
        assert granted["authorization"]["jti"] == "j-1"
        assert legacy["authorization"] is None
        assert (
            granted["execution_binding_hash"] != legacy["execution_binding_hash"]
        )
