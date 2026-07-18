"""Crash recovery: what a restart may do with a half-finished run.

Failure injection works at the durable-state level: a real run produces the
real journal, manifest and refs, then the test reproduces a crash by cutting
those artifacts to the exact prefix a dying process would have left. The
invariants under test come straight from the autonomy plan: no second apply,
no second commit, no false completed, no destroying another session's work.
Recovery cannot apply a patch even in principle — the module has no import
path to ``apply_unified_diff`` — so the tests focus on what it *does* close.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.queue.evidence import completion_gap, load_evidence
from koru.queue.journal import PHASE_STAGING, last_phase, read_events
from koru.queue.patch_retry import apply_patch_with_retry
from koru.queue.recovery import (
    FINISH_PROMOTION,
    NEEDS_HUMAN,
    NOTHING_TO_DO,
    REPLAY_SAFE,
    assess_run,
    recover_run,
    scan_incomplete_runs,
    sweep,
)

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


def _reply(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(returncode=returncode, stdout=stdout, stderr=stderr)


class _CrashLab(unittest.TestCase):
    """Drives real runs, then damages their durable state like a crash would."""

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

    def _run(self, project: Path, ticket: dict, gate=None):
        return apply_patch_with_retry(
            project,
            _reply(stdout=_GOOD_REPLY),
            ticket,
            {"prompt": "x"},
            lambda action, p: _reply(returncode=1),
            gate or (lambda command, cwd: _reply()),
        )

    def _the_run_id(self, project: Path) -> str:
        [journal] = (project / ".koru" / "runs").glob("*/events.jsonl")
        return journal.parent.name

    def _crash_after(self, project: Path, run_id: str, phase: str) -> None:
        """Rewind durable state to the moment just after *phase* was journaled."""
        run_dir = project / ".koru" / "runs" / run_id
        lines = (run_dir / "events.jsonl").read_text(encoding="utf-8").splitlines()
        kept: list[str] = []
        for line in lines:
            kept.append(line)
            if json.loads(line)["phase"] == phase:
                break
        (run_dir / "events.jsonl").write_text("\n".join(kept) + "\n", encoding="utf-8")
        evidence = run_dir / "evidence.json"
        if evidence.exists():
            evidence.unlink()


class TestReplaySafe(_CrashLab):
    def test_a_crash_before_any_workspace_write_retires_the_run(self) -> None:
        """Killed mid-staging: the worktree is disposable, the workspace never
        moved, so the run closes as interrupted and the ticket may simply re-run."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            _r, outcome, _b = self._run(
                project,
                {"id": "R-1", "labels": ["type:development-defect"],
                 "inputs": {"verify_command": "false"}},
                gate=lambda command, cwd: _reply(returncode=1, stderr="red"),
            )
            self.assertIsNotNone(outcome)
            run_id = self._the_run_id(project)
            self._crash_after(project, run_id, PHASE_STAGING)

            assessment = recover_run(project, run_id)

            self.assertEqual(assessment.recommendation, REPLAY_SAFE)
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "old\n")
            events = read_events(project, run_id)
            self.assertEqual(last_phase(events), "refused")
            evidence = load_evidence(project, run_id)
            assert evidence is not None
            self.assertEqual(evidence["verdict"], "refused")
            self.assertEqual(evidence["actor"], "koru-recovery")

    def test_recovery_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            self._run(
                project,
                {"id": "R-2", "labels": ["type:development-defect"],
                 "inputs": {"verify_command": "false"}},
                gate=lambda command, cwd: _reply(returncode=1, stderr="red"),
            )
            run_id = self._the_run_id(project)
            self._crash_after(project, run_id, PHASE_STAGING)

            first = recover_run(project, run_id)
            events_after_first = read_events(project, run_id)
            second = recover_run(project, run_id)

            self.assertEqual(first.recommendation, REPLAY_SAFE)
            self.assertEqual(second.recommendation, NOTHING_TO_DO)
            self.assertEqual(read_events(project, run_id), events_after_first)


class TestFinishPromotion(_CrashLab):
    def test_an_existing_run_ref_finishes_the_promotion_instead_of_retiring_it(self) -> None:
        """Killed after commit_worktree but before the bookkeeping: the verified
        commit exists on koru/run-<id>, and closing the run as interrupted would
        throw away finished work. Recovery completes the records instead."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            _r, outcome, _b = self._run(
                project,
                {"id": "R-3", "inputs": {"verify_command": "true",
                                         "promotion_mode": "branch"}},
            )
            self.assertIsNone(outcome, outcome)
            run_id = self._the_run_id(project)
            self._crash_after(project, run_id, PHASE_STAGING)

            assessment = recover_run(project, run_id)

            self.assertEqual(assessment.recommendation, FINISH_PROMOTION)
            evidence = load_evidence(project, run_id)
            assert evidence is not None
            self.assertEqual(evidence["verdict"], "verified")
            self.assertTrue(evidence["promotion"]["commit_sha"])
            self.assertIsNone(completion_gap(project, evidence))
            # No second commit: the ref still points at the one verified commit.
            commits = subprocess.run(
                ["git", "rev-list", "--count", f"koru/run-{run_id}"],
                cwd=project, capture_output=True, text=True, check=True,
            ).stdout.strip()
            self.assertEqual(commits, "2")  # baseline + the one promotion
            self.assertEqual(last_phase(read_events(project, run_id)), "completed")


class TestNeedsHuman(_CrashLab):
    def test_a_workspace_that_moved_after_applying_goes_to_a_human_untouched(self) -> None:
        """An open `applying` with a drifted workspace is unprovable either way:
        recovery must change nothing and say exactly why."""
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            _r, outcome, _b = self._run(
                project, {"id": "R-4", "inputs": {"verify_command": "true"}},
            )
            self.assertIsNone(outcome, outcome)  # a.txt is now "new"
            run_id = self._the_run_id(project)
            self._crash_after(project, run_id, "applying")

            events_before = read_events(project, run_id)
            assessment = recover_run(project, run_id)

            self.assertEqual(assessment.recommendation, NEEDS_HUMAN)
            self.assertIn("cannot distinguish", assessment.reason)
            # Nothing was touched: no events appended, no evidence invented,
            # the (possibly half-applied) workspace left exactly as found.
            self.assertEqual(read_events(project, run_id), events_before)
            self.assertIsNone(load_evidence(project, run_id))
            self.assertEqual((project / "a.txt").read_text(encoding="utf-8"), "new\n")


class TestSweep(_CrashLab):
    def test_terminal_runs_are_invisible_and_interrupted_ones_are_triaged(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            _r, outcome, _b = self._run(
                project, {"id": "R-5", "inputs": {"verify_command": "true"}},
            )
            self.assertIsNone(outcome, outcome)

            self.assertEqual(scan_incomplete_runs(project), [])
            self.assertEqual(sweep(project), [])

            run_id = self._the_run_id(project)
            self.assertEqual(
                assess_run(project, run_id).recommendation, NOTHING_TO_DO,
            )


if __name__ == "__main__":
    unittest.main()
