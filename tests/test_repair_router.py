"""Commit 6: the model router — a blocked provider routes, it never closes.

The acceptance scenarios come verbatim from the plan: model A policy-blocked →
model B answers → one run_id, two attempts, completed; a restart between the
block and the retry; every model burned → safe_blocked, never "do anything
that closes the ticket".
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from koru.repair_runs import lifecycle as lc
from koru.repair_runs.models import ModelAttempt, stable_hash
from koru.repair_runs.resume import sweep_resumable
from koru.repair_runs.router import (
    CONTEXT_LENGTH_EXCEEDED,
    PROVIDER_ERROR,
    PROVIDER_POLICY_BLOCK,
    PROVIDER_TIMEOUT,
    RUNTIME_POLICY_DENIED,
    ModelSpec,
    choose_model,
    classify_invocation,
)
from koru.repair_runs.sqlite_store import SqliteRepairRunStore, default_store_path

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

_REGISTRY_YAML = (
    "queue:\n"
    "  repair_models:\n"
    "    - id: primary\n"
    "      model: anthropic/claude\n"
    "      capabilities: [code, reasoning]\n"
    "    - id: fallback-policy\n"
    "      model: openai/gpt\n"
    "      capabilities: [code, strict-json]\n"
)


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0, status_code=None):
    return SimpleNamespace(
        returncode=returncode, stdout=stdout, stderr=stderr, status_code=status_code,
    )


class TestClassification(unittest.TestCase):
    def test_success_is_none(self) -> None:
        self.assertIsNone(classify_invocation(_reply(stdout="ok")))

    def test_the_table_rows(self) -> None:
        cases = {
            PROVIDER_POLICY_BLOCK: _reply(returncode=1, status_code=403),
            PROVIDER_TIMEOUT: _reply(returncode=1, stderr="request timed out"),
            CONTEXT_LENGTH_EXCEEDED: _reply(returncode=1, stderr="context length exceeded"),
            RUNTIME_POLICY_DENIED: _reply(returncode=1, stderr="runtime_policy_denied"),
            PROVIDER_ERROR: _reply(returncode=1, stderr="something else broke"),
        }
        for expected, result in cases.items():
            with self.subTest(code=expected):
                self.assertEqual(classify_invocation(result), expected)


class TestChooseModel(unittest.TestCase):
    _A = ModelSpec(id="a", model="anthropic/claude")
    _B = ModelSpec(id="b", model="openai/gpt")
    _C = ModelSpec(id="c", model="google/gemini", capabilities=("long-context",))

    def _attempt(self, model: str, failure: str | None, status="failed") -> ModelAttempt:
        return ModelAttempt(
            id="att", run_id="r", iteration=1, attempt=1, provider="openrouter",
            model=model, status=status, failure_code=failure, input_hash="h",
        )

    def test_a_sticky_failure_burns_the_model_for_the_run(self) -> None:
        chosen = choose_model(
            (self._A, self._B),
            [self._attempt("anthropic/claude", PROVIDER_POLICY_BLOCK)],
        )
        assert chosen is not None
        self.assertEqual(chosen.id, "b")

    def test_a_timeout_does_not_burn_the_model(self) -> None:
        """Transient failure: the same model may answer the retry."""
        chosen = choose_model(
            (self._A, self._B), [self._attempt("anthropic/claude", PROVIDER_TIMEOUT)],
        )
        assert chosen is not None
        self.assertEqual(chosen.id, "a")

    def test_an_interrupted_attempt_burns_the_model(self) -> None:
        chosen = choose_model(
            (self._A, self._B),
            [self._attempt("anthropic/claude", "worker_died", status="interrupted")],
        )
        assert chosen is not None
        self.assertEqual(chosen.id, "b")

    def test_context_length_prefers_a_long_context_model(self) -> None:
        chosen = choose_model(
            (self._A, self._B, self._C),
            [self._attempt("anthropic/claude", CONTEXT_LENGTH_EXCEEDED)],
            last_failure=CONTEXT_LENGTH_EXCEEDED,
        )
        assert chosen is not None
        self.assertEqual(chosen.id, "c")

    def test_a_burned_roster_returns_none_not_a_hail_mary(self) -> None:
        chosen = choose_model(
            (self._A, self._B),
            [
                self._attempt("anthropic/claude", PROVIDER_POLICY_BLOCK),
                self._attempt("openai/gpt", PROVIDER_POLICY_BLOCK),
            ],
        )
        self.assertIsNone(chosen)


class _QueueLab(unittest.TestCase):
    def _git_repo(self, tmp: str) -> Path:
        project = Path(tmp)
        for args in (
            ["init", "-q"],
            ["config", "user.email", "koru@test"],
            ["config", "user.name", "koru"],
        ):
            subprocess.run(["git", *args], cwd=project, check=True, capture_output=True)
        return project

    def _commit_file(self, project: Path, rel: str, body: str) -> None:
        (project / rel).write_text(body, encoding="utf-8")
        subprocess.run(["git", "add", "-A"], cwd=project, check=True, capture_output=True)
        subprocess.run(
            ["git", "commit", "-qm", "baseline"], cwd=project, check=True, capture_output=True,
        )

    def _ticket(self) -> dict:
        return {
            "id": "RT-1",
            "name": "patch a.txt",
            "executor": {"kind": "llm", "mode": "automatic"},
            "labels": ["refactor"],
            "files": ["a.txt"],
            "inputs": {
                "prompt": "change old to new",
                "verify_command": "true",
                "promotion_mode": "apply",
            },
        }

    def _drive(self, project: Path, llm_by_model: dict):
        from koru.queue.runner import run_next_planfile_task

        ticket = self._ticket()
        lifecycle: list[str] = []

        def planfile_runner(command, _project):
            args = [str(part) for part in command]
            args = args[args.index("ticket"):] if "ticket" in args else args
            if args[:4] == ["ticket", "list", "--status", "open"]:
                return _reply(stdout=json.dumps(ticket))
            if len(args) > 1 and args[1] in {"done", "block"}:
                lifecycle.append(args[1])
            return _reply()

        def llm_runner(request, _project):
            return llm_by_model[str(request.get("model"))]

        result = run_next_planfile_task(
            project=project,
            actor="koru-test",
            planfile_runner=planfile_runner,
            llm_runner=llm_runner,
            shell_runner=lambda command, cwd: _reply(),
        )
        return result, lifecycle

    def _store(self, project: Path) -> SqliteRepairRunStore:
        store = SqliteRepairRunStore(default_store_path(project))
        self.addCleanup(store.close)
        return store


class TestPolicyBlockResilience(_QueueLab):
    """The milestone: pierwszy model zablokowany → drugi kończy run."""

    def test_model_a_blocked_model_b_completes_one_run_two_attempts(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "koru.yaml").write_text(_REGISTRY_YAML, encoding="utf-8")

            result, lifecycle = self._drive(
                project,
                {
                    "anthropic/claude": _reply(returncode=1, status_code=403),
                    "openai/gpt": _reply(stdout=_GOOD_REPLY),
                },
            )

            self.assertEqual(result.status, "completed")
            self.assertEqual(lifecycle, ["done"], "the ticket closed exactly once")
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")
            store = self._store(project)
            run = store.find_run("RT-1", str(project))
            assert run is not None
            self.assertEqual(run.status, "completed")
            attempts = store.attempts(run.id)
            self.assertEqual(len(attempts), 2)
            self.assertEqual({a.run_id for a in attempts}, {run.id}, "one run_id")
            self.assertEqual(attempts[0].model, "anthropic/claude")
            self.assertEqual(attempts[0].failure_code, PROVIDER_POLICY_BLOCK)
            self.assertEqual(attempts[1].model, "openai/gpt")
            self.assertEqual(attempts[1].status, "succeeded")

    def test_every_model_blocked_parks_safe_blocked_and_never_completes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "koru.yaml").write_text(_REGISTRY_YAML, encoding="utf-8")

            result, lifecycle = self._drive(
                project,
                {
                    "anthropic/claude": _reply(returncode=1, status_code=403),
                    "openai/gpt": _reply(returncode=1, status_code=403),
                },
            )

            self.assertEqual(result.status, "failed")
            self.assertEqual(lifecycle, ["block"], "blocked for a human, not closed")
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            store = self._store(project)
            run = store.find_run("RT-1", str(project))
            assert run is not None
            self.assertEqual(run.status, lc.SAFE_BLOCKED)
            self.assertEqual(
                [a.failure_code for a in store.attempts(run.id)],
                [PROVIDER_POLICY_BLOCK, PROVIDER_POLICY_BLOCK],
            )

    def test_the_run_survives_a_restart_between_block_and_retry(self) -> None:
        """Plan's restart acceptance: model A blocked → proces ginie → restart →
        model B przejmuje ten sam run → completed."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            (project / "koru.yaml").write_text(_REGISTRY_YAML, encoding="utf-8")

            # Process 1: claims the run, starts model A, dies mid-call.
            now = datetime(2026, 7, 18, 12, 0, 0, tzinfo=UTC)
            store = self._store(project)
            run = store.create_run(
                ticket_id="RT-1", project_root=str(project), max_iterations=5, now=now,
            )
            store.claim(run.id, "worker-dead", lease_s=60, now=now)
            run = store.get_run(run.id)
            for status in (lc.CONTEXT_READY, lc.MODEL_RUNNING):
                run = store.transition(run.id, status, expected_version=run.version, now=now)
            store.start_attempt(
                run.id, iteration=1, attempt=1, provider="openrouter",
                model="anthropic/claude", input_hash=stable_hash("x"), now=now,
            )

            # Restart: the sweep closes the dangling attempt and unblocks routing.
            later = now + timedelta(seconds=120)
            [action] = sweep_resumable(store, now=later)
            self.assertEqual(action.status, lc.MODEL_BLOCKED)

            # Process 2: the queue picks the ticket up again; the router must
            # skip burned model A and let B finish the same run.
            result, lifecycle = self._drive(
                project,
                {
                    "anthropic/claude": _reply(returncode=1, status_code=403),
                    "openai/gpt": _reply(stdout=_GOOD_REPLY),
                },
            )

            self.assertEqual(result.status, "completed")
            after = store.find_run("RT-1", str(project))
            assert after is not None
            self.assertEqual(after.id, run.id, "the same run survived the restart")
            self.assertEqual(after.status, "completed")
            attempts = store.attempts(run.id)
            self.assertEqual(
                [(a.model, a.status) for a in attempts],
                [("anthropic/claude", "interrupted"), ("openai/gpt", "succeeded")],
            )


if __name__ == "__main__":
    unittest.main()
