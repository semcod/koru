"""Tests for fast-path living status updates and waves CLI routing."""

from __future__ import annotations

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from koru.cli_ticket import ticket_main
from koru.queue.living_status import update_living_status
from koru.queue.runners import run_process


def test_cli_ticket_waves_routed_to_queue_main() -> None:
    with patch("koru.cli_ticket_queue.ticket_main", return_value=0) as mock_queue_main:
        ret = ticket_main(["waves", "--format", "json"])
        assert ret == 0
        mock_queue_main.assert_called_once_with(["waves", "--format", "json"])


def test_update_living_status_fastpath_success(tmp_path: Path) -> None:
    mock_pf = MagicMock()
    ticket = {"id": "T-001", "description": "Existing task description"}

    with patch("planfile.Planfile.auto_discover", return_value=mock_pf) as mock_discover, \
         patch("koru.queue.planfile_sync.sync_after_ticket_update") as mock_sync:
        result = update_living_status(
            project=tmp_path,
            ticket=ticket,
            state="in_progress",
            actor="koru-worker-1",
            runner=run_process,
        )

        assert result.returncode == 0
        mock_discover.assert_called_once_with(str(tmp_path))
        mock_pf.update_ticket.assert_called_once()
        args, kwargs = mock_pf.update_ticket.call_args
        assert args[0] == "T-001"
        assert "<!-- koru:living-status:start -->" in kwargs["description"]
        assert "in_progress" in kwargs["description"]
        mock_sync.assert_called_once_with(tmp_path, "T-001")


def test_update_living_status_fallback_on_custom_runner(tmp_path: Path) -> None:
    dummy_proc = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    custom_runner = MagicMock(return_value=dummy_proc)
    ticket = {"id": "T-002", "description": "Another task"}

    with patch(
        "koru.queue.planfile_sdk.planfile_lifecycle_command",
        return_value=dummy_proc,
    ) as mock_lifecycle:
        result = update_living_status(
            project=tmp_path,
            ticket=ticket,
            state="done",
            actor="koru-worker-2",
            runner=custom_runner,
        )

        assert result.returncode == 0
        mock_lifecycle.assert_called_once()
        call_args = mock_lifecycle.call_args[0]
        assert call_args[0] == tmp_path
        assert call_args[1][0] == "ticket"
        assert call_args[1][1] == "update"
        assert call_args[1][2] == "T-002"
