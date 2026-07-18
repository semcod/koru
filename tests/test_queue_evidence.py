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
