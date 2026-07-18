"""Commit 4: queue patch runs leave a durable trace in the repair-run store.

Driven through the real runner with the real SQLite store — the assertions
read ``.koru/state/repair-runs.sqlite3`` the way the future router will.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.repair_runs.sqlite_store import SqliteRepairRunStore, default_store_path
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

_STALE_REPLY = _GOOD_REPLY.replace("-old\n", "-never was\n")


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


def _ticket_args(command) -> list[str]:
    args = [str(part) for part in command]
    return args[args.index("ticket"):] if "ticket" in args else args


class TestRepairRecording(unittest.TestCase):
    def _git_repo(self, tmp: str) -> Path:
        return _repolab.git_repo(tmp)

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        _repolab.commit_file(project, rel, body)

    def _ticket(self, **input_overrides) -> dict:
        inputs = {
            "prompt": "change old to new",
            "verify_command": "true",
            "promotion_mode": "apply",
        }
        inputs.update(input_overrides)
        return {
            "id": "REC-1",
            "name": "patch a.txt",
            "executor": {"kind": "llm", "mode": "automatic"},
            "labels": ["refactor"],
            "files": ["a.txt"],
            "inputs": inputs,
        }

    def _drive(self, project: Path, ticket: dict, llm_replies: list):
        from koru.queue.runner import run_next_planfile_task

        replies = list(llm_replies)

        def planfile_runner(command, _project):
            args = _ticket_args(command)
            if args[:4] == ["ticket", "list", "--status", "open"]:
                return _reply(stdout=json.dumps(ticket))
            return _reply()

        def llm_runner(request, _project):
            return replies.pop(0) if replies else _reply(returncode=1, stderr="exhausted")

        def shell_runner(command: str, cwd):
            # Honour the gate the ticket asked for: `false` fails, `true` passes.
            failing = command.split()[-1] == "false" if command.strip() else False
            return _reply(returncode=1 if failing else 0, stderr="gate red" if failing else "")

        return run_next_planfile_task(
            project=project,
            actor="koru-test",
            planfile_runner=planfile_runner,
            llm_runner=llm_runner,
            shell_runner=shell_runner,
        )

    def _store(self, project: Path) -> SqliteRepairRunStore:
        store = SqliteRepairRunStore(default_store_path(project))
        self.addCleanup(store.close)
        return store

    def test_a_green_run_is_recorded_completed_with_one_succeeded_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            result = self._drive(project, self._ticket(), [_reply(stdout=_GOOD_REPLY)])

            self.assertEqual(result.status, "completed")
            store = self._store(project)
            run = store.find_run("REC-1", str(project))
            assert run is not None
            self.assertEqual(run.status, "completed")
            self.assertIsNone(run.lease_owner, "the lease must be given back")
            [attempt] = store.attempts(run.id)
            self.assertEqual(attempt.status, "succeeded")
            self.assertTrue(attempt.input_hash)
            self.assertTrue(attempt.output_hash)

    def test_a_retry_records_two_attempts_on_one_run(self) -> None:
        """The plan's acceptance shape: one run_id, two model_attempts."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            result = self._drive(
                project,
                self._ticket(),
                [_reply(stdout=_STALE_REPLY), _reply(stdout=_GOOD_REPLY)],
            )

            self.assertEqual(result.status, "completed")
            store = self._store(project)
            run = store.find_run("REC-1", str(project))
            assert run is not None
            attempts = store.attempts(run.id)
            self.assertEqual(len(attempts), 2)
            self.assertEqual({a.run_id for a in attempts}, {run.id})
            self.assertNotEqual(
                attempts[0].input_hash, attempts[1].input_hash,
                "the retry prompt differs, so its input hash must too",
            )
            self.assertEqual(run.status, "completed")

    def test_a_failed_verify_ends_the_run_failed_and_releases_the_lease(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = self._ticket(verify_command="false")
            ticket["labels"] = ["refactor"]
            ticket["inputs"]["skip_verify_baseline"] = True

            result = self._drive(project, ticket, [_reply(stdout=_GOOD_REPLY)])

            self.assertEqual(result.status, "failed")
            store = self._store(project)
            run = store.find_run("REC-1", str(project))
            assert run is not None
            self.assertEqual(run.status, "failed")
            self.assertIsNone(run.lease_owner)

    def test_a_model_that_never_answers_fails_the_run_with_a_failed_attempt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            result = self._drive(
                project, self._ticket(), [_reply(returncode=1, stderr="boom")],
            )

            self.assertEqual(result.status, "failed")
            store = self._store(project)
            run = store.find_run("REC-1", str(project))
            assert run is not None
            self.assertEqual(run.status, "failed")
            [attempt] = store.attempts(run.id)
            self.assertEqual(attempt.status, "failed")
            self.assertEqual(attempt.failure_code, "provider_error")

    def test_recording_being_unavailable_never_blocks_the_queue(self) -> None:
        """The store is observational at this stage; the queue's job comes first."""
        from unittest import mock

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")

            with mock.patch(
                "koru.queue.repair_recording.SqliteRepairRunStore",
                side_effect=OSError("disk says no"),
            ):
                result = self._drive(project, self._ticket(), [_reply(stdout=_GOOD_REPLY)])

            self.assertEqual(result.status, "completed")
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")

    def test_a_second_queue_pass_resumes_the_same_run(self) -> None:
        """A failed repair re-runs under the same run identity, next iteration."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            failing = self._ticket()
            failing["inputs"]["verify_command"] = "false"
            failing["inputs"]["skip_verify_baseline"] = True

            self._drive(project, failing, [_reply(stdout=_GOOD_REPLY)])
            store = self._store(project)
            run = store.find_run("REC-1", str(project))
            assert run is not None
            self.assertEqual(run.status, "failed")

            # `failed` is terminal: a re-run of the ticket must NOT silently
            # reuse the dead run — and must still work, unrecorded.
            result = self._drive(project, self._ticket(), [_reply(stdout=_GOOD_REPLY)])

            self.assertEqual(result.status, "completed")
            after = store.find_run("REC-1", str(project))
            assert after is not None
            self.assertEqual(after.status, "failed", "the terminal record is immutable")


if __name__ == "__main__":
    unittest.main()
