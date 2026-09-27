"""Tests for koru work cli finish arguments and ticket inference."""

from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from koru.cli_work import _action_finish, build_parser
from koru.work.lifecycle import _infer_ticket_id, finish_work


class TestCliWorkFinish(unittest.TestCase):
    def test_finish_parser_ticket_is_optional(self) -> None:
        args = build_parser().parse_args(["finish", "--pr", "42", "--merge"])
        self.assertIs(args.func, _action_finish)
        self.assertIsNone(args.ticket)
        self.assertEqual(args.pr, 42)
        self.assertTrue(args.merge)

    def test_infer_ticket_id_from_branch(self) -> None:
        tid = _infer_ticket_id(Path("/tmp/repo"), "ticket/287-auto-merge")
        self.assertEqual(tid, "ticket-287")

    def test_infer_ticket_id_from_worktree_path(self) -> None:
        tid = _infer_ticket_id(Path("/tmp/repo/.worktrees/ticket-288--fix"), "main")
        self.assertEqual(tid, "ticket-288")

    def test_finish_work_infers_ticket_id_when_omitted(self) -> None:
        with (
            patch("koru.work.lifecycle._ensure_repo"),
            patch("koru.work.lifecycle._current_branch", return_value="ticket/289-feature"),
            patch(
                "koru.work.lifecycle.run_local_ci",
                return_value={"overall_status": "passed", "stages": []},
            ),
            patch(
                "koru.work.lifecycle.dispatch_validator_merge",
                return_value={"status": "published"},
            ) as mock_dispatch,
        ):
            res = finish_work(Path("/tmp/repo"), pr_number=10, publish=True)
            self.assertEqual(res["status"], "finished")
            self.assertEqual(res["ticket_id"], "ticket-289")
            mock_dispatch.assert_called_once_with(
                Path("/tmp/repo").resolve(),
                ticket_id="ticket-289",
                pr_number=10,
                dry_run=False,
                merge=True,
            )
