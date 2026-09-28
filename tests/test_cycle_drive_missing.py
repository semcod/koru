"""Tests for resilient waiting ticket missing check in cycle drive retry."""

from __future__ import annotations

import subprocess
import unittest
from pathlib import Path
from unittest.mock import patch

from koru.autonomy.cycle.cycle_drive_retry import _waiting_ticket_is_missing


class WaitingTicketMissingTests(unittest.TestCase):
    def test_empty_ticket_id_returns_false(self) -> None:
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), ""))
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), "   "))

    @patch("koru.autonomy.cycle.cycle_drive_retry._run_process")
    def test_existing_ticket_returns_false(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[], returncode=0, stdout='{"id": "STARTER-003"}', stderr=""
        )
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), "STARTER-003"))

    @patch("koru.autonomy.cycle.cycle_drive_retry._run_process")
    def test_module_not_found_error_fails_closed(self, mock_run) -> None:
        # If planfile crashes with ModuleNotFoundError (e.g. missing procache),
        # it must NOT drop the ticket as a ghost id.
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="",
            stderr="Traceback (most recent call last):\nModuleNotFoundError: No module named 'procache'",
        )
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), "STARTER-003"))

    @patch("koru.autonomy.cycle.cycle_drive_retry._run_process")
    def test_command_not_found_fails_closed(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=127,
            stdout="",
            stderr="/bin/sh: line 1: planfile: command not found",
        )
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), "STARTER-003"))

    @patch("koru.autonomy.cycle.cycle_drive_retry._run_process")
    def test_explicit_ticket_not_found_returns_true(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="✗ Ticket STARTER-003 not found.",
            stderr="",
        )
        self.assertTrue(_waiting_ticket_is_missing(Path("/tmp"), "STARTER-003"))

    @patch("koru.autonomy.cycle.cycle_drive_retry._run_process")
    def test_different_ticket_not_found_returns_false(self, mock_run) -> None:
        mock_run.return_value = subprocess.CompletedProcess(
            args=[],
            returncode=1,
            stdout="✗ Ticket OTHER-999 not found.",
            stderr="",
        )
        self.assertFalse(_waiting_ticket_is_missing(Path("/tmp"), "STARTER-003"))


if __name__ == "__main__":
    unittest.main()
