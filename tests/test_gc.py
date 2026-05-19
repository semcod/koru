"""Tests for koru.gc – planfile queue garbage collection."""

from __future__ import annotations

import json
import tempfile
import unittest
from datetime import UTC, datetime, timedelta
from pathlib import Path

import yaml

from koru.gc import (
    GcResult,
    collect_gc_candidates,
    run_gc,
)


def _write_sprint(project: Path, tickets: dict, sprint: str = "current") -> None:
    """Write a minimal sprint YAML for testing."""
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    data = {
        "sprint": {
            "id": sprint,
            "name": "test",
            "status": "active",
            "tickets": tickets,
        },
    }
    (sprint_dir / f"{sprint}.yaml").write_text(
        yaml.safe_dump(data, sort_keys=False),
        encoding="utf-8",
    )


def _ts(days_ago: float) -> str:
    """ISO timestamp N days in the past."""
    dt = datetime.now(UTC) - timedelta(days=days_ago)
    return dt.isoformat()


def _ticket(
    name: str,
    status: str = "done",
    exec_state: str = "done",
    days_ago: float = 60,
) -> dict:
    return {
        "name": name,
        "status": status,
        "execution": {
            "state": exec_state,
            "finished_at": _ts(days_ago),
        },
    }


class TestCollectGcCandidates(unittest.TestCase):
    def test_finds_old_done_tickets(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-001": _ticket("Old task", days_ago=60),
                    "T-002": _ticket("Recent task", days_ago=1),
                    "T-003": _ticket("Open task", status="open", exec_state="ready", days_ago=90),
                },
            )
            candidates = collect_gc_candidates(project, max_age_days=30)
            ids = [c.ticket_id for c in candidates]
            self.assertIn("T-001", ids)
            self.assertNotIn("T-002", ids)  # too recent
            self.assertNotIn("T-003", ids)  # status=open not in GC_STATUSES

    def test_includes_failed_and_blocked(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-010": _ticket(
                        "Failed old", status="failed", exec_state="failed", days_ago=45
                    ),
                    "T-011": _ticket(
                        "Blocked old", status="blocked", exec_state="pending", days_ago=45
                    ),
                },
            )
            candidates = collect_gc_candidates(project, max_age_days=30)
            ids = [c.ticket_id for c in candidates]
            self.assertIn("T-010", ids)
            self.assertIn("T-011", ids)

    def test_no_candidates_when_all_recent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-020": _ticket("Fresh done", days_ago=2),
                },
            )
            candidates = collect_gc_candidates(project, max_age_days=30)
            self.assertEqual(candidates, [])

    def test_missing_timestamp_treated_as_old(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-030": {
                        "name": "No timestamp",
                        "status": "done",
                        "execution": {"state": "done"},
                    },
                },
            )
            candidates = collect_gc_candidates(project, max_age_days=30)
            self.assertEqual(len(candidates), 1)
            self.assertEqual(candidates[0].age_days, float("inf"))

    def test_empty_sprint(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(project, {})
            candidates = collect_gc_candidates(project, max_age_days=1)
            self.assertEqual(candidates, [])

    def test_custom_statuses(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-040": _ticket("Done old", status="done", days_ago=60),
                    "T-041": _ticket("Failed old", status="failed", days_ago=60),
                },
            )
            # Only clean "failed"
            candidates = collect_gc_candidates(
                project,
                statuses=frozenset({"failed"}),
                max_age_days=30,
            )
            ids = [c.ticket_id for c in candidates]
            self.assertNotIn("T-040", ids)
            self.assertIn("T-041", ids)


class TestRunGc(unittest.TestCase):
    def test_dry_run_does_not_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-100": _ticket("Old done", days_ago=60),
                    "T-101": _ticket("Recent done", days_ago=5),
                },
            )
            result = run_gc(project, apply=False, max_age_days=30)
            self.assertTrue(result.dry_run)
            self.assertEqual(result.removed, ["T-100"])
            self.assertEqual(result.kept, [])
            # Sprint file untouched
            data = yaml.safe_load(
                (project / ".planfile/sprints/current.yaml").read_text(),
            )
            self.assertIn("T-100", data["sprint"]["tickets"])

    def test_keep_last_protects_recent(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-200": _ticket("Oldest", days_ago=90),
                    "T-201": _ticket("Middle", days_ago=60),
                    "T-202": _ticket("Newest old", days_ago=35),
                },
            )
            result = run_gc(project, apply=False, max_age_days=30, keep_last=1)
            self.assertIn("T-200", result.removed)
            self.assertIn("T-201", result.removed)
            # T-202 protected by keep_last=1
            self.assertIn("T-202", result.kept)

    def test_keep_last_larger_than_candidates_keeps_all(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-300": _ticket("Only old", days_ago=60),
                },
            )
            result = run_gc(project, apply=False, max_age_days=30, keep_last=5)
            self.assertEqual(result.removed, [])
            self.assertEqual(result.kept, ["T-300"])

    def test_apply_calls_planfile_delete(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-400": _ticket("Old done", days_ago=60),
                },
            )
            delete_calls: list[list[str]] = []

            def fake_runner(command: list[str], _project: Path):
                delete_calls.append(list(command))
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            result = run_gc(
                project,
                apply=True,
                max_age_days=30,
                planfile_runner=fake_runner,
            )
            self.assertFalse(result.dry_run)
            self.assertEqual(result.removed, ["T-400"])
            # Verify planfile delete was called
            self.assertTrue(any("delete" in str(c) for c in delete_calls))

    def test_apply_creates_archive(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-500": _ticket("Archived ticket", days_ago=60),
                },
            )

            def fake_runner(command: list[str], _project: Path):
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            result = run_gc(
                project,
                apply=True,
                max_age_days=30,
                archive=True,
                planfile_runner=fake_runner,
            )
            self.assertIsNotNone(result.archived_to)
            self.assertTrue(result.archived_to.exists())
            lines = result.archived_to.read_text().strip().split("\n")
            self.assertEqual(len(lines), 1)
            data = json.loads(lines[0])
            self.assertEqual(data["id"], "T-500")

    def test_no_archive_flag(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-600": _ticket("No archive", days_ago=60),
                },
            )

            def fake_runner(command: list[str], _project: Path):
                return type("R", (), {"returncode": 0, "stdout": "", "stderr": ""})()

            result = run_gc(
                project,
                apply=True,
                max_age_days=30,
                archive=False,
                planfile_runner=fake_runner,
            )
            self.assertIsNone(result.archived_to)

    def test_no_candidates_returns_empty_result(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-700": _ticket("Recent", days_ago=5),
                },
            )
            result = run_gc(project, apply=False, max_age_days=30)
            self.assertEqual(result.candidates, [])
            self.assertEqual(result.removed, [])

    def test_delete_failure_records_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            _write_sprint(
                project,
                {
                    "T-800": _ticket("Fail to delete", days_ago=60),
                },
            )

            def failing_runner(command: list[str], _project: Path):
                return type(
                    "R", (), {"returncode": 1, "stdout": "", "stderr": "permission denied"}
                )()

            result = run_gc(
                project,
                apply=True,
                max_age_days=30,
                planfile_runner=failing_runner,
            )
            self.assertEqual(len(result.errors), 1)
            self.assertIn("T-800", result.errors[0])

    def test_summary_string(self) -> None:
        r = GcResult(removed=["A", "B"], kept=["C"], dry_run=True)
        s = r.summary()
        self.assertIn("removed=2", s)
        self.assertIn("kept=1", s)
        self.assertIn("dry_run=true", s)
