"""Tests for the JSONL run-log writer.

Contract:
- ``open_run_log`` does NOT touch disk until something is written.
- Each ``write_*`` appends one JSON object per line, ``sort_keys=True``.
- IO errors do not raise — the queue runner must keep going.
- File path lives strictly under ``<project>/.planfile/.koru/runs/``.
"""

from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest import mock

from koru.run_log import open_run_log, open_run_log_eagerly
from koru.runtime import runs_dir, runtime_dir


def _result(**kw) -> SimpleNamespace:
    base = dict(
        ticket_id="PLF-1",
        executor_kind="shell",
        status="completed",
        exit_code=0,
        message="echo ok",
        stderr="",
    )
    base.update(kw)
    return SimpleNamespace(**base)


class TestOpenRunLog(unittest.TestCase):
    def test_constructor_does_not_create_file(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log(project)
            self.assertFalse(writer.path.exists())
            # Project root remains empty.
            self.assertEqual(list(project.iterdir()), [])

    def test_eager_creates_runs_dir_only(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log_eagerly(project)
            self.assertTrue(runs_dir(project).is_dir())
            self.assertTrue((runtime_dir(project) / "README.md").is_file())
            # The log file itself is still not on disk.
            self.assertFalse(writer.path.exists())

    def test_path_is_under_planfile_dot_koru_runs(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log(project)
            relative = writer.path.relative_to(runs_dir(project))
            self.assertEqual(relative.parent, Path("."))
            self.assertTrue(writer.path.name.endswith(".jsonl"))


class TestWriteEvents(unittest.TestCase):
    def test_header_iteration_footer_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log(project)
            writer.write_header(project=project, mode="loop", actor="koru-test")
            writer.write_iteration(iteration=1, result=_result())
            writer.write_iteration(
                iteration=2,
                result=_result(status="failed", exit_code=2),
            )
            writer.write_footer(
                summary=SimpleNamespace(
                    iterations=2,
                    completed=["PLF-1"],
                    failed=["PLF-2"],
                    waiting=[],
                    last_status="failed",
                )
            )

            self.assertTrue(writer.path.is_file())
            lines = writer.path.read_text(encoding="utf-8").strip().split("\n")
            self.assertEqual(len(lines), 4)

            events = [json.loads(line) for line in lines]
            self.assertEqual(events[0]["type"], "run.start")
            self.assertEqual(events[0]["mode"], "loop")
            self.assertEqual(events[1]["type"], "iteration")
            self.assertEqual(events[1]["status"], "completed")
            self.assertEqual(events[2]["type"], "iteration")
            self.assertEqual(events[2]["exit_code"], 2)
            self.assertEqual(events[3]["type"], "run.end")
            self.assertEqual(events[3]["completed"], ["PLF-1"])

    def test_each_line_is_json(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log(project)
            writer.write_header(project=project, mode="single")
            writer.write_iteration(iteration=1, result=_result())

            for line in writer.path.read_text(encoding="utf-8").splitlines():
                # Each line is independently parseable — JSONL.
                json.loads(line)

    def test_keys_are_sorted_in_output(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            project = Path(tmp)
            writer = open_run_log(project)
            writer.write_iteration(iteration=1, result=_result())
            line = writer.path.read_text(encoding="utf-8").splitlines()[0]
            obj = json.loads(line)
            # If sort_keys=True was honoured, the dict iteration order
            # of the loaded line matches sorted key order.
            self.assertEqual(list(obj.keys()), sorted(obj.keys()))

    def test_message_truncation_500_chars(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            writer = open_run_log(Path(tmp))
            big = "x" * 5000
            writer.write_iteration(iteration=1, result=_result(message=big))
            obj = json.loads(writer.path.read_text(encoding="utf-8").splitlines()[0])
            self.assertEqual(len(obj["message"]), 500)


class TestErrorTolerance(unittest.TestCase):
    def test_io_error_does_not_propagate(self) -> None:
        """A failing write must not crash the queue runner."""
        with tempfile.TemporaryDirectory() as tmp:
            writer = open_run_log(Path(tmp))
            with mock.patch(
                "koru.run_log.open",
                side_effect=PermissionError("nope"),
            ):
                # Must not raise.
                writer.write_iteration(iteration=1, result=_result())


if __name__ == "__main__":
    unittest.main()
