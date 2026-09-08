"""Queue compiler boundaries independent of live daemon or LLM services."""

from __future__ import annotations

import pytest

from koru.autonomy import execution_plan as execution
from koru.work import llm_provenance


@pytest.fixture
def queued(monkeypatch, tmp_path):
    ticket = {"id": "TASK-1", "name": " Work ", "files": ["src/a.py"]}
    monkeypatch.setattr(execution, "load_autonomy_strategy", lambda p: {"id": "test"})
    monkeypatch.setattr(execution, "build_strategy_heuristics", lambda p: {})
    monkeypatch.setattr(execution, "_open_refactor_tickets", lambda p: [ticket, {"id": "TASK-2"}])
    monkeypatch.setattr(execution, "_count_skipped_complete", lambda p: 0)
    monkeypatch.setattr(execution, "sprint_ticket_status_summary", lambda p: {})
    monkeypatch.setattr(execution, "resolve_ticket_repo", lambda p, t: str(tmp_path / "repo"))

    def unavailable(*args):
        raise RuntimeError("no live provenance in characterization")

    monkeypatch.setattr(llm_provenance, "resolve_work_llm_context", unavailable)
    return ticket


@pytest.mark.parametrize(("profile_id", "expected_id"), [("chosen", "chosen"), (None, "generic")])
def test_matched_profile_uses_first_ticket_and_resolved_repo(queued, monkeypatch, tmp_path, profile_id, expected_id):
    profile = {"workflow": []}
    monkeypatch.setattr(execution, "_select_profile", lambda t, p: (profile_id, profile))
    calls = []

    def workflow(selected, **kwargs):
        calls.append((selected, kwargs))
        return [execution.ExecutionStep("step", "test", "test", profile_id=kwargs["profile_id"])]

    monkeypatch.setattr(execution, "_workflow_steps", workflow)
    plan = execution.compile_execution_plan(tmp_path)
    assert plan.selected_ticket is queued
    assert plan.phase == "planfile_queue"
    assert plan.summary == f"phase=planfile_queue ticket=TASK-1 profile={expected_id}"
    assert calls == [
        (
            profile,
            {
                "project": tmp_path,
                "repo": tmp_path / "repo",
                "ticket": queued,
                "profile_id": expected_id,
                "phase": "planfile_queue",
            },
        )
    ]


def test_fallback_profile_is_used_only_for_missing_match(queued, monkeypatch, tmp_path):
    fallback = {"workflow": []}
    monkeypatch.setattr(execution, "_select_profile", lambda t, p: (None, None))
    monkeypatch.setattr(
        execution,
        "_load_task_profiles",
        lambda: {
            "defaults": {"fallback_profile": "fallback"},
            "profiles": {"fallback": fallback},
        },
    )
    calls = []
    monkeypatch.setattr(
        execution, "_workflow_steps", lambda profile, **kwargs: calls.append((profile, kwargs["profile_id"])) or []
    )
    plan = execution.compile_execution_plan(tmp_path)
    assert calls == [(fallback, "fallback")]
    assert plan.steps == []
    assert plan.summary == "phase=planfile_queue ticket=TASK-1 profile=n/a"


@pytest.mark.parametrize("fallback", [None, "invalid"])
def test_missing_usable_profile_builds_manual_ticket_step(queued, monkeypatch, tmp_path, fallback):
    monkeypatch.setattr(execution, "_select_profile", lambda t, p: (None, None))
    monkeypatch.setattr(
        execution,
        "_load_task_profiles",
        lambda: {
            "profiles": {"god_module_split": fallback},
        },
    )
    plan = execution.compile_execution_plan(tmp_path)
    assert plan.steps == [
        execution.ExecutionStep(
            id="work_ticket",
            kind="ide_work",
            reason="Runnable planfile ticket without a matching profile.",
            ticket_id="TASK-1",
            repo=str(tmp_path / "repo"),
            hint="Work",
        )
    ]
    assert plan.summary == "phase=planfile_queue ticket=TASK-1 profile=None"
