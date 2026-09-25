"""Tests for koru work lifecycle."""

from __future__ import annotations

import contextlib
import io
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.cli_work import _action_finish, _action_next, _action_start, build_parser, work_main
from koru.task_models import CreatedTask
from koru.work.lifecycle import finish_work, start_work


class TestWorkStart(unittest.TestCase):
    def test_start_work_creates_ticket_and_branch(self) -> None:
        created = CreatedTask(ticket_id="ticket-099", sprint="current", path=Path("/tmp/x"), name="Demo")
        with (
            patch("koru.work.lifecycle._ensure_repo"),
            patch("koru.work.lifecycle.create_nl_task", return_value=created),
            patch("koru.work.lifecycle._current_branch", return_value="main"),
            patch("koru.work.lifecycle._ensure_branch"),
            patch("koru.work.lifecycle._commit_planfile_sync", return_value="abc"),
            patch("koru.work.lifecycle._push_branch"),
        ):
            result = start_work(Path("/tmp/project"), title="Demo task")
        self.assertEqual(result["ticket_id"], "ticket-099")
        self.assertEqual(result["branch"], "ticket-099-demo-task")
        self.assertTrue(result["pushed"])


class TestWorkFinish(unittest.TestCase):
    def test_finish_blocked_on_ci(self) -> None:
        with (
            patch("koru.work.lifecycle._ensure_repo"),
            patch("koru.work.lifecycle._current_branch", return_value="ticket-099-demo"),
            patch(
                "koru.work.lifecycle.run_local_ci",
                return_value={"overall_status": "failed", "stages": []},
            ),
        ):
            result = finish_work(Path("/tmp/project"), ticket_id="ticket-099", publish=False)
        self.assertEqual(result["status"], "blocked")
        self.assertEqual(result["reason"], "ci_failed")


class TestWorkCli(unittest.TestCase):
    def test_work_start_cli(self) -> None:
        with patch(
            "koru.cli_work.start_work",
            return_value={"status": "started", "ticket_id": "t1", "branch": "b1", "next": []},
        ):
            code = work_main(["--project", "/tmp", "start", "--title", "x"])
        self.assertEqual(code, 0)


class TestWorkParser(unittest.TestCase):
    """Table-driven build_parser keeps flags, defaults and dispatch identical."""

    def test_start_flags_and_dispatch(self) -> None:
        args = build_parser().parse_args(["start", "--title", "demo"])
        self.assertIs(args.func, _action_start)
        self.assertEqual(args.base, "main")
        self.assertFalse(args.no_push)
        self.assertEqual(args.remote, "origin")

    def test_finish_flags_and_dispatch(self) -> None:
        args = build_parser().parse_args(["finish", "--ticket", "t1", "--pr", "7", "--merge", "--dry-run"])
        self.assertIs(args.func, _action_finish)
        self.assertEqual(args.pr, 7)
        self.assertTrue(args.merge)
        self.assertTrue(args.dry_run)
        self.assertFalse(args.skip_ci)

    def test_next_flags_and_dispatch(self) -> None:
        args = build_parser().parse_args(["next", "--run-gates"])
        self.assertIs(args.func, _action_next)
        self.assertTrue(args.run_gates)
        self.assertFalse(args.start_branch)

    def test_global_defaults(self) -> None:
        args = build_parser().parse_args(["next"])
        self.assertEqual(args.format, "text")
        self.assertEqual(args.project, Path.cwd())

    def test_title_required(self) -> None:
        with self.assertRaises(SystemExit):
            build_parser().parse_args(["start"])

    def test_subcommand_help_texts_preserved(self) -> None:
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer), self.assertRaises(SystemExit):
            build_parser().parse_args(["-h"])
        rendered = " ".join(buffer.getvalue().split())
        for text in (
            "Create ticket, branch, commit planfile, push.",
            "Run CI and dispatch validator-agent.",
            "Decide the next refactor ticket and optionally start a work branch.",
        ):
            self.assertIn(text, rendered)


if __name__ == "__main__":
    unittest.main()
