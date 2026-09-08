"""Plan ordering and creation budgets at the discovery boundary."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import koru.tasks
from koru.autonomy import todo2code_discovery as discovery


def _plan(name, priority="P2", path=None):
    path = path or f"src/{name}.py"
    return {
        "id": name,
        "title": name,
        "priority": priority,
        "target": {"paths": [path]},
        "changes": [{"path": path, "action": "create"}],
    }


def _apply(project, plans, limit=10):
    return discovery._apply_plan_tickets(
        project,
        {"plans": plans},
        plans_path=project / "plans.json",
        source=discovery.DEFAULT_SOURCE,
        limit=limit,
    )


@pytest.fixture
def created(monkeypatch):
    calls = []

    def create(project, text, **kwargs):
        calls.append(kwargs["scaffold"]["title"])
        return SimpleNamespace(reused=False)

    monkeypatch.setattr(koru.tasks, "create_nl_task", create)
    return calls


def test_ranking_precedes_limit_and_preserves_equal_score_order(tmp_path, created):
    result = _apply(tmp_path, [_plan("low", "P3"), _plan("first", "P1"), _plan("second", "P1")], limit=2)
    assert created == ["[todo2code] first", "[todo2code] second"]
    assert result == (created, [], 3, 0)


def test_filtered_counts_exclude_non_mapping_input(tmp_path, created):
    result = _apply(tmp_path, [None, "bad", {}, _plan("asset", path="image.png"), _plan("valid")])
    assert result == (["[todo2code] valid"], [], 1, 2)
    assert created == ["[todo2code] valid"]


@pytest.mark.parametrize("limit", [0, -1])
def test_non_positive_limit_preserves_counts_without_creation(tmp_path, created, limit):
    assert _apply(tmp_path, [_plan("valid")], limit) == ([], [], 1, 0)
    assert created == []


def test_duplicate_does_not_consume_successful_creation_limit(tmp_path, created):
    plan = _plan("first")
    result = _apply(tmp_path, [plan, dict(plan), _plan("second")], limit=2)
    assert result == (["[todo2code] first", "[todo2code] second"], ["[todo2code] first"], 3, 0)
    assert len(created) == 2


@pytest.mark.parametrize("outcome", ["reused", "failed"])
def test_unsuccessful_creation_does_not_consume_limit(tmp_path, monkeypatch, outcome):
    calls = []

    def create(project, text, **kwargs):
        calls.append(kwargs["scaffold"]["title"])
        if len(calls) == 1 and outcome == "failed":
            raise ValueError("unavailable")
        return SimpleNamespace(reused=len(calls) == 1)

    monkeypatch.setattr(koru.tasks, "create_nl_task", create)
    result = _apply(tmp_path, [_plan("first"), _plan("second")], limit=1)
    skipped = "[todo2code] first" + (": unavailable" if outcome == "failed" else "")
    assert result == (["[todo2code] second"], [skipped], 2, 0)
    assert calls == ["[todo2code] first", "[todo2code] second"]
