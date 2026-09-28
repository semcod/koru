"""Tests for parallel ticket batching, execution waves, and queue concurrency."""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

from koru.cli_ticket_queue import ticket_main
from koru.queue.loop import run_planfile_queue_loop
from koru.queue.runner import _next_tickets_or_result
from koru.queue.ticket import parse_next_tickets, ticket_file_scope
from koru.queue.types import CommandResult, QueueRunResult


def test_ticket_file_scope_extraction() -> None:
    t1 = {"files": ["src/a.py", "src/b.py"]}
    assert ticket_file_scope(t1) == {"src/a.py", "src/b.py"}

    t2 = {"inputs": {"files": ["src/c.py"], "file": "src/d.py"}}
    assert ticket_file_scope(t2) == {"src/c.py", "src/d.py"}

    t3 = {"source": {"context": {"file": "src/e.py"}}}
    assert ticket_file_scope(t3) == {"src/e.py"}

    t4 = {"allowed_paths": ["src/f/**"]}
    assert ticket_file_scope(t4) == {"src/f/**"}

    t5 = {}
    assert ticket_file_scope(t5) == set()


def test_parse_next_tickets_disjoint_filtering() -> None:
    tickets = [
        {
            "id": "T-001",
            "status": "open",
            "priority": "critical",
            "files": ["src/module_a.py"],
            "executor": {"kind": "shell", "handler": "echo 1"},
        },
        {
            "id": "T-002",
            "status": "open",
            "priority": "high",
            "files": ["src/module_a.py", "src/shared.py"],  # overlaps with T-001
            "executor": {"kind": "shell", "handler": "echo 2"},
        },
        {
            "id": "T-003",
            "status": "open",
            "priority": "normal",
            "files": ["src/module_c.py"],
            "executor": {"kind": "shell", "handler": "echo 3"},
        },
        {
            "id": "T-004",
            "status": "open",
            "priority": "low",
            "files": ["src/module_d.py"],
            "executor": {"kind": "shell", "handler": "echo 4"},
        },
    ]

    stdout = json.dumps(tickets)

    # When disjoint_files=True and count=2: T-001 picked, T-002 skipped (conflicts on module_a), T-003 picked
    picked_disjoint = parse_next_tickets(stdout, count=2, disjoint_files=True)
    assert len(picked_disjoint) == 2
    assert [t["id"] for t in picked_disjoint] == ["T-001", "T-003"]

    # When disjoint_files=False and count=2: T-001 and T-002 picked
    picked_all = parse_next_tickets(stdout, count=2, disjoint_files=False)
    assert len(picked_all) == 2
    assert [t["id"] for t in picked_all] == ["T-001", "T-002"]


def test_parse_next_tickets_single_object_payload() -> None:
    single = {
        "id": "T-100",
        "status": "open",
        "priority": "high",
        "executor": {"kind": "shell", "handler": "echo ok"},
    }
    stdout = json.dumps(single)
    picked = parse_next_tickets(stdout, count=3)
    assert len(picked) == 1
    assert picked[0]["id"] == "T-100"


def test_next_tickets_or_result_fallback(tmp_path: Path) -> None:
    tickets = [
        {"id": "T-1", "status": "open", "priority": "high", "files": ["f1.py"]},
        {"id": "T-2", "status": "open", "priority": "normal", "files": ["f2.py"]},
    ]
    runner = MagicMock(return_value=CommandResult(0, json.dumps(tickets), ""))

    with patch("koru.queue.runner.planfile_command", return_value=CommandResult(0, json.dumps(tickets), "")):
        with patch("koru.queue.runner.admitted_payload", return_value=json.dumps(tickets)):
            batch, err = _next_tickets_or_result(tmp_path, runner, count=2, disjoint_files=True)
            assert err is None
            assert len(batch) == 2
            assert [t["id"] for t in batch] == ["T-1", "T-2"]


def test_run_planfile_queue_loop_concurrent(tmp_path: Path) -> None:
    tickets = [
        {"id": "PAR-1", "status": "open", "priority": "high", "files": ["a.py"]},
        {"id": "PAR-2", "status": "open", "priority": "high", "files": ["b.py"]},
    ]

    def fake_next_tickets(*args, **kwargs):
        nonlocal tickets
        if tickets:
            batch = list(tickets)
            tickets = []
            return batch, None
        return [], None

    def fake_run_task(*args, **kwargs):
        target_id = kwargs.get("target_ticket_id") or "unknown"
        return QueueRunResult(
            status="completed",
            ticket_id=target_id,
            executor_kind="shell",
            message=f"done {target_id}",
        )

    with patch("koru.queue.runner._next_tickets_or_result", side_effect=fake_next_tickets):
        with patch("koru.queue.loop.run_next_planfile_task", side_effect=fake_run_task):
            progress_results = []
            loop_res = run_planfile_queue_loop(
                project=tmp_path,
                concurrency=2,
                max_iterations=10,
                progress_callback=lambda res, it: progress_results.append(res.ticket_id),
                planfile_runner=MagicMock(),
                shell_runner=MagicMock(),
                api_runner=MagicMock(),
                llm_runner=MagicMock(),
                prompt_runner=MagicMock(),
            )

            assert set(loop_res.completed) == {"PAR-1", "PAR-2"}
            assert loop_res.iterations == 2
            assert set(progress_results) == {"PAR-1", "PAR-2"}


def test_cli_waves_action(tmp_path: Path, capsys) -> None:
    with patch("subprocess.run") as mock_sub:
        mock_sub.return_value = MagicMock(
            returncode=0,
            stdout=json.dumps([{"id": "T-10"}, {"id": "T-11"}]),
        )
        exit_code = ticket_main(["waves", "--project", str(tmp_path), "--format", "json"])
        assert exit_code == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert len(data) >= 1
