"""Tests for task execution strategies and prioritization in Koru."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

import pytest
import yaml

from koru.autonomy.execution_plan import compile_execution_plan
from koru.autonomy.task_strategies import (
    DEFAULT_TASK_STRATEGY,
    STRATEGY_ORDER,
    PendingPR,
    PendingWorktree,
    find_pending_prs,
    find_pending_worktrees,
    resolve_task_strategy,
)
from koru.cli_decide import decide_main
from koru.cli_work import work_main


def _write_sprint(project: Path, tickets: dict) -> None:
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    payload = {"sprint": {"id": "current", "tickets": tickets}}
    (sprint_dir / "current.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_default_strategy_is_in_flight_first(tmp_path: Path) -> None:
    assert DEFAULT_TASK_STRATEGY == "in_flight_first"
    assert resolve_task_strategy(tmp_path) == "in_flight_first"
    assert STRATEGY_ORDER["in_flight_first"] == ("pending_prs", "pending_worktrees", "issues")


def test_resolve_task_strategy_precedence(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    # 1. Default
    assert resolve_task_strategy(tmp_path) == "in_flight_first"

    # 2. From koru.yaml strategy
    (tmp_path / "koru.yaml").write_text(
        "schema: '1.0'\nautonomy:\n  strategy:\n    id: accordion_detail_to_general\n",
        encoding="utf-8",
    )
    assert resolve_task_strategy(tmp_path) == "accordion_detail_to_general"

    # 3. From environment variable
    monkeypatch.setenv("KORU_TASK_STRATEGY", "worktree_first")
    assert resolve_task_strategy(tmp_path) == "worktree_first"

    # 4. Explicit override beats env and config
    assert resolve_task_strategy(tmp_path, explicit_strategy="issues_first") == "issues_first"


def test_in_flight_first_prioritizes_pending_prs(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    mock_pr = PendingPR(
        number=450,
        title="Fix core pipeline bug",
        head_branch="ticket/450-fix-core",
        url="https://github.com/semcod/koru/pull/450",
        mergeable="MERGEABLE",
    )
    mock_wt = PendingWorktree(
        path="/path/to/.worktrees/ticket-449",
        branch="ticket/449-old-work",
        ticket_id="ticket-449",
        head_sha="abcdef123",
        is_dirty=True,
        commits_ahead=1,
        is_merged=False,
    )

    # In in_flight_first, pending PR must be chosen first, even with worktrees and issues present!
    plan = compile_execution_plan(
        tmp_path,
        pending_prs=[mock_pr],
        pending_worktrees=[mock_wt],
    )
    assert plan.phase == "pending_pr"
    assert plan.selected_pr is not None
    assert plan.selected_pr["number"] == 450
    assert any("gh pr view 450" in cmd for s in plan.steps for cmd in s.commands)
    assert any("--pr 450" in cmd for s in plan.steps for cmd in s.commands)


def test_in_flight_first_prioritizes_pending_worktrees_when_no_prs(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    mock_wt = PendingWorktree(
        path="/path/to/.worktrees/ticket-449",
        branch="ticket/449-old-work",
        ticket_id="ticket-449",
        head_sha="abcdef123",
        is_dirty=True,
        commits_ahead=1,
        is_merged=False,
    )

    # When no open PRs exist, pending local worktree must be chosen ahead of open planfile tickets!
    plan = compile_execution_plan(
        tmp_path,
        pending_prs=[],
        pending_worktrees=[mock_wt],
    )
    assert plan.phase == "pending_worktree"
    assert plan.selected_worktree is not None
    assert plan.selected_worktree["ticket_id"] == "ticket-449"
    assert any("git -C /path/to/.worktrees/ticket-449 status" in cmd for s in plan.steps for cmd in s.commands)
    assert any("koru work finish --ticket ticket-449" in cmd for s in plan.steps for cmd in s.commands)


def test_in_flight_first_falls_back_to_issues_when_no_prs_or_worktrees(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    plan = compile_execution_plan(
        tmp_path,
        pending_prs=[],
        pending_worktrees=[],
    )
    assert plan.phase == "planfile_queue"
    assert plan.selected_ticket is not None
    assert plan.selected_ticket["id"] == "T-1"


def test_accordion_strategy_prioritizes_issues_first(tmp_path: Path) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    mock_pr = PendingPR(
        number=450,
        title="Fix core pipeline bug",
        head_branch="ticket/450-fix-core",
    )

    # When strategy is accordion_detail_to_general, issues are processed first
    plan = compile_execution_plan(
        tmp_path,
        strategy_override="accordion_detail_to_general",
        pending_prs=[mock_pr],
    )
    assert plan.phase == "planfile_queue"
    assert plan.selected_ticket is not None
    assert plan.selected_ticket["id"] == "T-1"


def test_worktree_first_strategy_prioritizes_worktrees_over_prs(tmp_path: Path) -> None:
    mock_pr = PendingPR(
        number=450,
        title="Fix core pipeline bug",
        head_branch="ticket/450-fix-core",
    )
    mock_wt = PendingWorktree(
        path="/path/to/.worktrees/ticket-449",
        branch="ticket/449-old-work",
        ticket_id="ticket-449",
        head_sha="abcdef123",
        is_dirty=True,
        commits_ahead=1,
        is_merged=False,
    )

    plan = compile_execution_plan(
        tmp_path,
        strategy_override="worktree_first",
        pending_prs=[mock_pr],
        pending_worktrees=[mock_wt],
    )
    assert plan.phase == "pending_worktree"
    assert plan.selected_worktree is not None
    assert plan.selected_worktree["ticket_id"] == "ticket-449"


def test_find_pending_prs_parsing(tmp_path: Path) -> None:
    gh_output = json.dumps(
        [
            {
                "number": 448,
                "title": "Consolidate autoloop env overrides",
                "headRefName": "ticket/238-env",
                "url": "https://github.com/semcod/koru/pull/448",
                "mergeable": "MERGEABLE",
                "reviewDecision": "APPROVED",
                "statusCheckRollup": [{"state": "SUCCESS"}],
            }
        ]
    )

    def mock_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        assert cmd[:4] == ["gh", "pr", "list", "--state"]
        return subprocess.CompletedProcess(cmd, 0, stdout=gh_output, stderr="")

    prs = find_pending_prs(tmp_path, runner=mock_runner)
    assert len(prs) == 1
    assert prs[0].number == 448
    assert prs[0].title == "Consolidate autoloop env overrides"
    assert prs[0].head_branch == "ticket/238-env"
    assert prs[0].mergeable == "MERGEABLE"
    assert prs[0].review_decision == "APPROVED"
    assert prs[0].checks_status == "SUCCESS"


def test_find_pending_prs_failure_handling(tmp_path: Path) -> None:
    def failing_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="gh: not found")

    prs = find_pending_prs(tmp_path, runner=failing_runner)
    assert prs == []


def test_find_pending_worktrees_detects_dirty_and_unmerged(tmp_path: Path) -> None:
    worktree_list_output = (
        f"worktree {tmp_path}\n"
        "HEAD 3645d892\n"
        "branch refs/heads/main\n\n"
        f"worktree {tmp_path / '.worktrees' / 'ticket-240'}\n"
        "HEAD abcdef12\n"
        "branch refs/heads/ticket/240-feature\n\n"
        f"worktree {tmp_path / '.worktrees' / 'ticket-239'}\n"
        "HEAD 12345678\n"
        "branch refs/heads/ticket/239-consolidate\n\n"
    )

    def mock_runner(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
        if cmd == ["worktree", "list", "--porcelain"]:
            return subprocess.CompletedProcess(cmd, 0, stdout=worktree_list_output, stderr="")
        if cmd == ["status", "--short"]:
            # Make ticket-240 dirty, ticket-239 clean
            if "ticket-240" in str(cwd):
                return subprocess.CompletedProcess(cmd, 0, stdout=" M src/file.py\n", stderr="")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
        if cmd[:2] == ["merge-base", "--is-ancestor"]:
            # ticket-240 is not merged, ticket-239 is merged
            branch = cmd[2]
            returncode = 1 if "240" in branch else 0
            return subprocess.CompletedProcess(cmd, returncode, stdout="", stderr="")
        if cmd[:2] == ["rev-list", "--count"]:
            branch = cmd[2].split("..")[-1]
            ahead = "2" if "240" in branch else "0"
            return subprocess.CompletedProcess(cmd, 0, stdout=ahead, stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    wts = find_pending_worktrees(tmp_path, runner=mock_runner)
    assert len(wts) == 1
    assert wts[0].ticket_id == "ticket-240"
    assert wts[0].is_dirty is True
    assert wts[0].is_merged is False
    assert wts[0].commits_ahead == 2


def test_cli_decide_json_format(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    code = decide_main(["--project", str(tmp_path), "--format", "json"])
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["strategy_id"] == "in_flight_first"
    assert payload["phase"] == "planfile_queue"


def test_cli_work_next_supports_strategy_flag(tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
    _write_sprint(
        tmp_path,
        {
            "T-1": {
                "id": "T-1",
                "status": "open",
                "priority": "high",
                "name": "Refactor smell",
                "labels": ["refactor"],
            }
        },
    )

    cmd = [
        "--project",
        str(tmp_path),
        "--format",
        "json",
        "next",
        "--strategy",
        "accordion_detail_to_general",
    ]
    code = work_main(cmd)
    assert code == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["plan"]["strategy_id"] == "accordion_detail_to_general"
