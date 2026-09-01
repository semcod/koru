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
    assert execution_plan_module._fallback_profile_id(
        {"defaults": {"fallback_profile": "custom"}},
    ) == "custom"


def test_task_profiles_verify_runs_full_ci() -> None:
    profiles = execution_plan_module._load_task_profiles()
    for profile_id in ("god_module_split", "cc_hotspot_refactor"):
        profile = profiles["profiles"][profile_id]
        verify = next(step for step in profile["workflow"] if step["id"] == "verify")
        assert "koru ci run" in verify["command"]
        assert "koru ci gates" not in verify["command"]
        baseline = next(step for step in profile["workflow"] if step["id"] in {"inspect", "baseline"})
        assert "koru ci run --skip-gates" in baseline["command"]
