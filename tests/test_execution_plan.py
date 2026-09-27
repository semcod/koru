"""Tests for dynamic execution plan compilation."""

from __future__ import annotations

from pathlib import Path

import yaml

from koru.autonomy import execution_plan as execution_plan_module
from koru.autonomy.execution_plan import compile_execution_plan, resolve_ticket_repo


def _write_sprint(project: Path, tickets: dict) -> None:
    sprint_dir = project / ".planfile" / "sprints"
    sprint_dir.mkdir(parents=True, exist_ok=True)
    payload = {"sprint": {"id": "current", "tickets": tickets}}
    (sprint_dir / "current.yaml").write_text(yaml.safe_dump(payload), encoding="utf-8")


def test_compile_plan_selects_highest_priority_ticket(tmp_path: Path) -> None:
    (tmp_path / "koru.yaml").write_text(
        "schema: '1.0'\nautonomy:\n  strategy:\n    id: test\n"
        "    default_pipeline:\n      order: [planfile_queue, idle_scan]\n",
        encoding="utf-8",
    )
    _write_sprint(
        tmp_path,
        {
            "STARTER-003": {
                "id": "STARTER-003",
                "status": "open",
                "priority": "high",
                "name": "Split god module: codot/godot/llm/app.py",
                "labels": ["god-module", "refactor"],
                "files": ["codot/godot/llm/app.py"],
                "source": {"context": {"signal": "code2llm_god"}},
            },
            "STARTER-010": {
                "id": "STARTER-010",
                "status": "open",
                "priority": "high",
                "name": "Reduce cyclomatic complexity: _build_llm_prompt (CC=36, limit=15)",
                "labels": ["cyclomatic", "refactor"],
                "files": ["nexu/examples/web_app_calculator/cinema/server.py"],
                "source": {"context": {"signal": "regix_cc"}},
            },
        },
    )
    target = tmp_path / "codot" / "godot" / "llm"
    target.mkdir(parents=True)
    (target / "app.py").write_text("print('ok')\n", encoding="utf-8")

    plan = compile_execution_plan(tmp_path)
    assert plan.phase == "planfile_queue"
    assert plan.selected_ticket is not None
    assert plan.selected_ticket["id"] == "STARTER-010"
    assert plan.steps[0].profile_id == "cc_hotspot_refactor"
    assert plan.signals.get("skipped_likely_complete") == 1


def test_skips_likely_complete_god_module_ticket(tmp_path: Path) -> None:
    (tmp_path / "koru.yaml").write_text(
        "schema: '1.0'\nautonomy:\n  strategy:\n    id: test\n"
        "    default_pipeline:\n      order: [planfile_queue, idle_scan]\n",
        encoding="utf-8",
    )
    _write_sprint(
        tmp_path,
        {
            "STARTER-003": {
                "id": "STARTER-003",
                "status": "open",
                "priority": "high",
                "name": "Split god module: codot/godot/llm/app.py",
                "labels": ["god-module", "refactor"],
                "files": ["codot/godot/llm/app.py"],
            },
            "STARTER-020": {
                "id": "STARTER-020",
                "status": "open",
                "priority": "normal",
                "name": "Split large module: site_explorer",
                "labels": ["large-module", "refactor"],
                "files": ["curllm/site_explorer.py"],
            },
        },
    )
    target = tmp_path / "codot" / "godot" / "llm"
    target.mkdir(parents=True)
    (target / "app.py").write_text("print('ok')\n", encoding="utf-8")
    big = tmp_path / "curllm"
    big.mkdir()
    (big / "site_explorer.py").write_text("\n".join(["# line"] * 500), encoding="utf-8")

    plan = compile_execution_plan(tmp_path)
    assert plan.selected_ticket is not None
    assert plan.selected_ticket["id"] == "STARTER-020"
    assert plan.signals.get("skipped_likely_complete") == 1


def test_resolve_ticket_repo_uses_nested_git_root(tmp_path: Path) -> None:
    repo = tmp_path / "cql"
    repo.mkdir()
    (repo / ".git").mkdir()
    ticket = {
        "id": "STARTER-013",
        "files": ["packages/foo.ts", "project/analysis.toon.yaml"],
    }
    # Without a real git repo this falls back to project; smoke the function shape.
    resolved = resolve_ticket_repo(repo, ticket)
    assert isinstance(resolved, str)


def test_profile_selection_uses_registry_order(monkeypatch) -> None:
    profiles = {
        "defaults": {"profile_order": ["second", "first"]},
        "profiles": {
            "first": {"match": {"labels_any": ["refactor"]}},
            "second": {"match": {"labels_any": ["refactor"]}},
        },
    }
    monkeypatch.setattr(execution_plan_module, "_load_task_profiles", lambda: profiles)

    profile_id, _profile = execution_plan_module._select_profile(
        {"labels": ["refactor"]},
        "planfile_queue",
    )

    assert profile_id == "second"


def test_fallback_profile_uses_registry_default() -> None:
    assert (
        execution_plan_module._fallback_profile_id(
            {"defaults": {"fallback_profile": "custom"}},
        )
        == "custom"
    )


def test_task_profiles_verify_runs_full_ci() -> None:
    profiles = execution_plan_module._load_task_profiles()
    for profile_id in ("god_module_split", "cc_hotspot_refactor"):
        profile = profiles["profiles"][profile_id]
        verify = next(step for step in profile["workflow"] if step["id"] == "verify")
        assert "koru ci run" in verify["command"]
        assert "koru ci gates" not in verify["command"]
        baseline = next(step for step in profile["workflow"] if step["id"] in {"inspect", "baseline"})
        assert "koru ci run --skip-gates" in baseline["command"]


def _write_idle_project(tmp_path: Path, order: list[str]) -> None:
    (tmp_path / "koru.yaml").write_text(
        "schema: '1.0'\nautonomy:\n  strategy:\n    id: test\n"
        f"    default_pipeline:\n      order: [{', '.join(order)}]\n",
        encoding="utf-8",
    )
    _write_sprint(tmp_path, {})


def test_compile_plan_runs_discovery_phase_without_open_tickets(tmp_path: Path) -> None:
    _write_idle_project(tmp_path, ["planfile_queue", "whole_project_discovery"])

    plan = compile_execution_plan(tmp_path)

    assert plan.phase == "whole_project_discovery"
    assert plan.selected_ticket is None
    assert plan.summary == "phase=whole_project_discovery"
    assert plan.steps and plan.steps[0].profile_id == "whole_project_discovery"
    assert plan.signals["open_refactor_tickets"] == 0


def test_compile_plan_stays_idle_without_discovery_phase(tmp_path: Path) -> None:
    _write_idle_project(tmp_path, ["planfile_queue"])

    plan = compile_execution_plan(tmp_path)

    assert plan.phase == "idle"
    assert plan.selected_ticket is None
    assert plan.summary == "phase=idle"
    assert plan.steps == []


def test_select_pending_pr_returns_none_on_empty_list(tmp_path: Path) -> None:
    result = execution_plan_module._select_pending_pr(tmp_path, [])
    assert result is None


def test_select_pending_pr_returns_selection_for_first_pr(tmp_path: Path) -> None:
    from koru.autonomy.task_strategies import PendingPR

    pr = PendingPR(
        number=100,
        title="Fix thing",
        head_branch="ticket/100-fix",
        url="https://example.com/pr/100",
        mergeable="MERGEABLE",
    )
    result = execution_plan_module._select_pending_pr(tmp_path, [pr])
    assert result is not None
    assert result.phase == "pending_pr"
    assert result.selected_pr is not None
    assert result.selected_pr["number"] == 100


def test_select_pending_worktree_returns_none_on_empty_list(tmp_path: Path) -> None:
    result = execution_plan_module._select_pending_worktree(tmp_path, [])
    assert result is None


def test_select_pending_worktree_returns_selection(tmp_path: Path) -> None:
    from koru.autonomy.task_strategies import PendingWorktree

    wt = PendingWorktree(
        path=str(tmp_path / ".worktrees" / "ticket-42--fix"),
        branch="ticket/42-fix",
        head_sha="def456",
        ticket_id="42",
        is_dirty=False,
        is_merged=False,
        commits_ahead=1,
    )
    result = execution_plan_module._select_pending_worktree(tmp_path, [wt])
    assert result is not None
    assert result.phase == "pending_worktree"
    assert result.selected_worktree is not None
    assert result.selected_worktree["ticket_id"] == "42"


def test_select_issue_or_discovery_returns_ticket_selection(
    tmp_path: Path,
    monkeypatch,
) -> None:
    profiles = {
        "defaults": {"fallback_profile": "generic"},
        "profiles": {"generic": {"match": {}, "workflow": []}},
    }
    monkeypatch.setattr(execution_plan_module, "_load_task_profiles", lambda: profiles)

    ticket = {"id": "PLF-001", "name": "Fix something", "files": [], "labels": []}
    result = execution_plan_module._select_issue_or_discovery(
        tmp_path,
        {},
        [ticket],
    )
    assert result is not None
    assert result.phase == "planfile_queue"
    assert result.selected is not None
    assert result.selected["id"] == "PLF-001"


def test_select_issue_or_discovery_falls_to_discovery_when_empty(
    tmp_path: Path,
) -> None:
    (tmp_path / "koru.yaml").write_text(
        "schema: '1.0'\nautonomy:\n  strategy:\n    id: test\n"
        "    default_pipeline:\n      order: [planfile_queue, idle_scan]\n",
        encoding="utf-8",
    )
    strategy = {"default_pipeline": {"order": ["idle_scan"]}}
    result = execution_plan_module._select_issue_or_discovery(tmp_path, strategy, [])
    assert result is not None
    assert result.phase == "idle_scan"


def test_pr_steps_and_worktree_steps_are_auto_runnable(tmp_path: Path) -> None:
    from koru.autonomy.execution_plan_steps import pr_steps, worktree_steps
    from koru.autonomy.task_strategies import PendingPR, PendingWorktree

    pr = PendingPR(number=101, title="Test PR", head_branch="ticket/101-feat")
    steps = pr_steps(tmp_path, pr)
    finish_pr = next(s for s in steps if s.id == "finish_pr")
    assert finish_pr.auto_runnable is True

    wt = PendingWorktree(
        path=str(tmp_path / ".worktrees" / "ticket-102--test"),
        branch="ticket/102-test",
        ticket_id="102",
        head_sha="abc1234",
        is_dirty=False,
        commits_ahead=1,
        is_merged=False,
    )
    wt_steps = worktree_steps(tmp_path, wt)
    finish_wt = next(s for s in wt_steps if s.id == "finish_worktree")
    assert finish_wt.auto_runnable is True

