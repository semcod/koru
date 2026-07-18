"""The run journal: append-only, monotonic, and honest about crashes.

The property under test is the recovery contract: after any interruption the
journal must say which mutation — if any — was underway, and reading it must
never manufacture order out of a torn file.
"""

from __future__ import annotations

import json
import subprocess
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from koru.queue.journal import (
    PHASE_APPLIED,
    PHASE_APPLYING,
    PHASE_COMPLETED,
    PHASE_FROZEN,
    PHASE_PROMOTED,
    PHASE_PROMOTING,
    PHASE_REFUSED,
    PHASE_RESOLVED,
    PHASE_STAGED,
    PHASE_STAGING,
    PHASE_VERIFIED,
    RunJournal,
    interrupted_mutation,
    last_phase,
    read_events,
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


class TestJournalMechanics(unittest.TestCase):
    def test_seq_is_monotonic_and_events_carry_the_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")

            journal.append(PHASE_RESOLVED, data={"mode": "apply"})
            journal.append(PHASE_FROZEN, manifest_hash="abc")

            events = read_events(project, "run1")
            self.assertEqual([e["seq"] for e in events], [1, 2])
            self.assertEqual({e["run_id"] for e in events}, {"run1"})
            self.assertEqual(events[1]["manifest_hash"], "abc")
            self.assertTrue(all(e["at"] for e in events))

    def test_seq_continues_across_process_restarts(self) -> None:
        """A new instance is a restart in miniature — numbering must not reset."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            RunJournal(project, "run1").append(PHASE_RESOLVED)

            RunJournal(project, "run1").append(PHASE_FROZEN)

            self.assertEqual([e["seq"] for e in read_events(project, "run1")], [1, 2])

    def test_a_torn_final_line_is_dropped_not_parsed(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")
            journal.append(PHASE_RESOLVED)
            with journal.path.open("a", encoding="utf-8") as handle:
                handle.write('{"seq": 2, "phase": "fro')  # process died mid-write

            events = read_events(project, "run1")

            self.assertEqual(len(events), 1)
            self.assertEqual(last_phase(events), PHASE_RESOLVED)

    def test_appending_after_a_torn_line_heals_onto_a_fresh_line(self) -> None:
        """The next event must not concatenate into the torn bytes."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")
            journal.append(PHASE_RESOLVED)
            with journal.path.open("a", encoding="utf-8") as handle:
                handle.write('{"torn')

            RunJournal(project, "run1").append(PHASE_FROZEN)

            # The torn bytes stop the reader, so only seq 1 is trusted — but the
            # new event exists intact on its own line for forensics.
            self.assertEqual(len(read_events(project, "run1")), 1)
            raw = journal.path.read_text(encoding="utf-8").splitlines()
            self.assertTrue(raw[-1].startswith('{"'))
            self.assertEqual(json.loads(raw[-1])["phase"], PHASE_FROZEN)

    def test_a_broken_seq_chain_stops_the_reader(self) -> None:
        """Events after a gap cannot be ordered against what was lost."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")
            journal.append(PHASE_RESOLVED)
            with journal.path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps({"seq": 5, "phase": PHASE_PROMOTED}) + "\n")

            events = read_events(project, "run1")

            self.assertEqual([e["seq"] for e in events], [1])

    def test_replay_is_idempotent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")
            for phase in (PHASE_RESOLVED, PHASE_FROZEN, PHASE_APPLYING, PHASE_APPLIED):
                journal.append(phase)

            self.assertEqual(read_events(project, "run1"), read_events(project, "run1"))


class TestLifecycleEnforcement(unittest.TestCase):
    def test_an_impossible_history_is_rejected_at_write_time(self) -> None:
        """`promoted` out of nowhere must fail loudly, not be archived."""
        from koru.queue.lifecycle import LifecycleViolation

        with tempfile.TemporaryDirectory() as tmp:
            journal = RunJournal(Path(tmp), "run1")
            journal.append(PHASE_RESOLVED)

            with self.assertRaises(LifecycleViolation):
                journal.append(PHASE_PROMOTED)

    def test_an_exact_duplicate_event_is_idempotent(self) -> None:
        """Replayed bookkeeping must not inflate the record."""
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            journal = RunJournal(project, "run1")
            journal.append(PHASE_RESOLVED, data={"mode": "apply"})

            first = journal.append(PHASE_FROZEN, manifest_hash="abc")
            second = journal.append(PHASE_FROZEN, manifest_hash="abc")

            self.assertEqual(first["seq"], second["seq"])
            self.assertEqual(len(read_events(project, "run1")), 2)

    def test_a_changed_payload_is_not_a_duplicate(self) -> None:
        """Same phase, different manifest — that is a new fact, not a replay."""
        from koru.queue.lifecycle import LifecycleViolation

        with tempfile.TemporaryDirectory() as tmp:
            journal = RunJournal(Path(tmp), "run1")
            journal.append(PHASE_RESOLVED)
            journal.append(PHASE_FROZEN, manifest_hash="abc")

            with self.assertRaises(LifecycleViolation):
                journal.append(PHASE_FROZEN, manifest_hash="DIFFERENT")

    def test_events_carry_the_schema_version(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            RunJournal(project, "run1").append(PHASE_RESOLVED)

            [event] = read_events(project, "run1")
            self.assertEqual(event["schema_version"], 1)

    def test_a_retry_may_reopen_after_a_refusal(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            journal = RunJournal(Path(tmp), "run1")
            journal.append(PHASE_RESOLVED)
            journal.append(PHASE_REFUSED)

            event = journal.append(PHASE_RESOLVED)

            self.assertEqual(event["seq"], 3)


class TestInterruptedMutation(unittest.TestCase):
    def _events(self, *phases: str) -> list[dict]:
        return [{"seq": i + 1, "phase": phase} for i, phase in enumerate(phases)]

    def test_a_clean_run_reports_nothing(self) -> None:
        events = self._events(
            PHASE_RESOLVED, PHASE_FROZEN, PHASE_STAGING, PHASE_STAGED,
            PHASE_APPLYING, PHASE_APPLIED, PHASE_COMPLETED,
        )
        self.assertIsNone(interrupted_mutation(events))

    def test_an_open_apply_is_flagged(self) -> None:
        """Intent without completion is exactly "a crash may have half-written"."""
        events = self._events(PHASE_RESOLVED, PHASE_FROZEN, PHASE_APPLYING)
        self.assertEqual(interrupted_mutation(events), PHASE_APPLYING)

    def test_an_open_promotion_is_flagged_even_after_a_clean_apply(self) -> None:
        events = self._events(
            PHASE_RESOLVED, PHASE_APPLYING, PHASE_APPLIED, PHASE_VERIFIED, PHASE_PROMOTING,
        )
        self.assertEqual(interrupted_mutation(events), PHASE_PROMOTING)

    def test_a_refusal_closes_the_open_intent(self) -> None:
        events = self._events(PHASE_RESOLVED, PHASE_STAGING, PHASE_REFUSED)
        self.assertIsNone(interrupted_mutation(events))


class TestTransactionJournaling(unittest.TestCase):
    """The transaction writes the journal as it works, in recovery-usable order."""

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

    def _phases(self, project: Path) -> list[str]:
        runs = sorted((project / ".koru" / "runs").glob("*/events.jsonl"))
        self.assertEqual(len(runs), 1, runs)
        run_id = runs[0].parent.name
        return [e["phase"] for e in read_events(project, run_id)]

    def test_a_green_isolated_run_journals_every_step_through_completed(self) -> None:
        from koru.queue.patch_retry import apply_patch_with_retry

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "J-1", "inputs": {"verify_command": "true"}}

            _result, outcome, _bundle = apply_patch_with_retry(
                project,
                _reply(stdout=_GOOD_REPLY),
                ticket,
                {"prompt": "x"},
                lambda action, p: _reply(returncode=1),
                lambda command, cwd: _reply(),
            )

            self.assertIsNone(outcome, outcome)
            phases = self._phases(project)
            self.assertEqual(
                phases,
                [
                    PHASE_RESOLVED,
                    PHASE_FROZEN,
                    PHASE_STAGING,
                    PHASE_STAGED,
                    PHASE_APPLYING,
                    PHASE_APPLIED,
                    PHASE_COMPLETED,
                ],
            )
            self.assertIsNone(interrupted_mutation(read_events(project, self._run_id(project))))

    def test_a_commit_mode_run_journals_the_promotion_pair(self) -> None:
        from koru.queue.patch_retry import apply_patch_with_retry

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {
                "id": "J-2",
                "inputs": {"verify_command": "true", "promotion_mode": "commit"},
            }

            _result, outcome, _bundle = apply_patch_with_retry(
                project,
                _reply(stdout=_GOOD_REPLY),
                ticket,
                {"prompt": "x"},
                lambda action, p: _reply(returncode=1),
                lambda command, cwd: _reply(),
            )

            self.assertIsNone(outcome, outcome)
            phases = self._phases(project)
            self.assertIn(PHASE_PROMOTING, phases)
            self.assertIn(PHASE_PROMOTED, phases)
            self.assertLess(phases.index(PHASE_PROMOTING), phases.index(PHASE_PROMOTED))

    def test_a_refused_run_ends_at_refused(self) -> None:
        from koru.queue.patch_retry import apply_patch_with_retry

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {
                "id": "J-3",
                "labels": ["type:development-defect"],
                "inputs": {"verify_command": "false"},
            }

            _result, outcome, _bundle = apply_patch_with_retry(
                project,
                _reply(stdout=_GOOD_REPLY),
                ticket,
                {"prompt": "x"},
                lambda action, p: _reply(returncode=1),
                lambda command, cwd: _reply(returncode=1, stderr="red"),
            )

            self.assertIsNotNone(outcome)
            phases = self._phases(project)
            self.assertEqual(phases[-1], PHASE_REFUSED)
            self.assertNotIn(PHASE_COMPLETED, phases)

    def test_both_retry_attempts_share_one_journal(self) -> None:
        from koru.queue.patch_retry import apply_patch_with_retry

        stale = _GOOD_REPLY.replace("-old\n", "-never was\n")

        with tempfile.TemporaryDirectory() as tmp:
            project = self._git_repo(tmp)
            self._commit_file(project, "a.txt", "old\n")
            ticket = {"id": "J-4", "inputs": {"verify_command": "true"}}

            _result, outcome, _bundle = apply_patch_with_retry(
                project,
                _reply(stdout=stale),
                ticket,
                {"prompt": "x"},
                lambda action, p: _reply(stdout=_GOOD_REPLY),
                lambda command, cwd: _reply(),
            )

            self.assertIsNone(outcome, outcome)
            phases = self._phases(project)
            # One file, two attempts: two `resolved`, a refusal in between, and
            # the second attempt runs through to completed.
            self.assertEqual(phases.count(PHASE_RESOLVED), 2)
            self.assertIn(PHASE_REFUSED, phases)
            self.assertEqual(phases[-1], PHASE_COMPLETED)

    def _run_id(self, project: Path) -> str:
        [run] = (project / ".koru" / "runs").glob("*/events.jsonl")
        return run.parent.name


if __name__ == "__main__":
    unittest.main()
