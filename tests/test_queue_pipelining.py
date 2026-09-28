"""Tests for dynamic queue pipelining and continuous work-stealing."""

from __future__ import annotations

import time
from pathlib import Path
from unittest.mock import MagicMock, patch

from koru.queue.loop import run_planfile_queue_loop
from koru.queue.runner import _next_tickets_or_result
from koru.queue.runners import run_process
from koru.queue.types import QueueRunResult


def test_dynamic_pipelining_continuous_scheduling(tmp_path: Path) -> None:
    """Verify that when worker finishes early, next disjoint ticket is dispatched immediately."""
    tickets_state = [
        {"id": "PIPE-1", "status": "open", "priority": "high", "files": ["file_a.py"]},
        {"id": "PIPE-2", "status": "open", "priority": "high", "files": ["file_b.py"]},
        {"id": "PIPE-3", "status": "open", "priority": "normal", "files": ["file_a.py"]},
    ]

    active_tickets: set[str] = set()
    completed_order: list[str] = []

    def fake_next_tickets(
        project,
        runner,
        count=1,
        queue_name=None,
        target_ticket_id=None,
        *,
        disjoint_files=True,
        interactive=False,
        locked_files=None,
        exclude_ids=None,
    ):
        locked = set(locked_files or [])
        excluded = set(exclude_ids or []) | active_tickets

        selected = []
        for t in tickets_state:
            if t.get("status") != "open" or t["id"] in excluded:
                continue
            t_files = set(t.get("files", []))
            if disjoint_files and (t_files & locked):
                continue
            selected.append(t)
            locked.update(t_files)
            if len(selected) >= count:
                break
        return selected, None

    def fake_run_task(*args, **kwargs):
        target_id = kwargs.get("target_ticket_id") or "unknown"
        active_tickets.add(target_id)
        try:
            if target_id == "PIPE-1":
                time.sleep(0.05)
            elif target_id == "PIPE-2":
                time.sleep(0.15)
            elif target_id == "PIPE-3":
                time.sleep(0.02)
            completed_order.append(target_id)
            for t in tickets_state:
                if t["id"] == target_id:
                    t["status"] = "completed"
            return QueueRunResult(status="completed", ticket_id=target_id, executor_kind="shell")
        finally:
            active_tickets.discard(target_id)

    with patch("koru.queue.runner._next_tickets_or_result", side_effect=fake_next_tickets):
        with patch("koru.queue.loop.run_next_planfile_task", side_effect=fake_run_task):
            res = run_planfile_queue_loop(
                project=tmp_path,
                concurrency=2,
                max_iterations=10,
                planfile_runner=MagicMock(),
                shell_runner=MagicMock(),
                api_runner=MagicMock(),
                llm_runner=MagicMock(),
                prompt_runner=MagicMock(),
            )

            assert res.iterations == 3
            assert set(res.completed) == {"PIPE-1", "PIPE-2", "PIPE-3"}
            # PIPE-1 finishes first, allowing PIPE-3 to start and finish before PIPE-2 finishes!
            assert completed_order[0] == "PIPE-1"
            assert completed_order[1] == "PIPE-3"
            assert completed_order[2] == "PIPE-2"


def test_queue_loop_concurrency_dry_run(tmp_path: Path) -> None:
    """Verify that dry_run flag is propagated to workers during concurrent loop."""
    tickets = [
        {"id": "DRY-1", "status": "open", "files": ["x.py"]},
        {"id": "DRY-2", "status": "open", "files": ["y.py"]},
    ]

    dry_run_calls = []

    def fake_next_tickets(*args, **kwargs):
        nonlocal tickets
        res = list(tickets)
        tickets = []
        return res, None

    def fake_run_task(*args, **kwargs):
        dry = kwargs.get("dry_run", False)
        dry_run_calls.append(dry)
        target_id = kwargs.get("target_ticket_id")
        return QueueRunResult(status="dry_run", ticket_id=target_id, executor_kind="shell")

    with patch("koru.queue.runner._next_tickets_or_result", side_effect=fake_next_tickets):
        with patch("koru.queue.loop.run_next_planfile_task", side_effect=fake_run_task):
            res = run_planfile_queue_loop(
                project=tmp_path,
                concurrency=2,
                dry_run=True,
                max_iterations=5,
                planfile_runner=MagicMock(),
                shell_runner=MagicMock(),
                api_runner=MagicMock(),
                llm_runner=MagicMock(),
                prompt_runner=MagicMock(),
            )

            assert all(dry_run_calls)
            assert res.last_status == "dry_run"


def test_empty_queue_fast_path(tmp_path: Path) -> None:
    """Verify empty queue returns immediately in-process without CLI subprocess fallback."""
    mock_pf = MagicMock()
    mock_pf.next_tickets.return_value = []
    mock_pf.list_tickets.return_value = []

    with patch("planfile.Planfile.auto_discover", return_value=mock_pf):
        tickets, err = _next_tickets_or_result(tmp_path, run_process, count=2)
        assert tickets == []
        assert err is None
