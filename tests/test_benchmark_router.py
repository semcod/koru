"""Unit tests for task classification, candidate ranking, and benchmark routing."""
from __future__ import annotations

from pathlib import Path

from koru.queue.benchmark_router import resolve_task_route
from koru.queue.routing.classifier import classify_task
from koru.queue.routing.contracts import (
    Candidate,
    ProbeResult,
    Task,
    TaskClass,
    ToolClass,
)
from koru.queue.routing.ranking import rank_candidates


def test_classify_task_missing_metadata() -> None:
    task = classify_task(None)
    assert task.difficulty == TaskClass.OTHER
    assert task.kind == "unknown"
    assert task.reason == "missing_metadata"

    task2 = classify_task({})
    assert task2.difficulty == TaskClass.OTHER
    assert task2.reason == "unclassified_metadata"


def test_classify_task_complex_on_large_scope() -> None:
    # Multiple files -> complex
    task = classify_task({"files": ["a.py", "b.py", "c.py"]})
    assert task.difficulty == TaskClass.COMPLEX
    assert task.kind == "coding"

    # Governance / security label -> complex
    task2 = classify_task({"labels": ["security"], "files": ["auth.py"]})
    assert task2.difficulty == TaskClass.COMPLEX


def test_classify_task_bounded_safe_ruff() -> None:
    task = classify_task({
        "inputs": {"task_kind": "lint_fix", "ruff_codes": ["F401", "I001"]},
        "files": ["src/module.py"],
    })
    assert task.difficulty == TaskClass.SIMPLE
    assert task.kind == "ruff"
    assert task.reason == "bounded_safe_ruff"


def test_classify_task_docs() -> None:
    task = classify_task({"inputs": {"task_kind": "docs"}})
    assert task.difficulty == TaskClass.OTHER
    assert task.kind == "docs"


def test_rank_candidates_explicit_override_wins() -> None:
    c1 = Candidate(
        id="cand-1",
        tool_class=ToolClass.CLI,
        client="aider",
        transport="subprocess",
        fingerprint="v1",
        capabilities=frozenset({"simple:coding"}),
        model="gpt-4o",
    )
    c2 = Candidate(
        id="cand-2",
        tool_class=ToolClass.API,
        client="subllm",
        transport="api",
        fingerprint="v2",
        capabilities=frozenset({"simple:coding"}),
        model="gemini",
    )

    task = Task(TaskClass.SIMPLE, "coding", "test")
    # Even if c2 has verified passing probe evidence, explicit choice of c1 wins
    evidence = {
        "cand-2": ProbeResult(status="ok", duration_ms=120),
        "cand-1": ProbeResult(status="failed", duration_ms=500),
    }

    decision = rank_candidates(
        task=task,
        candidates=[c1, c2],
        evidence=evidence,
        explicit_choice="aider",
    )
    assert decision.candidate == c1
    assert "explicit_selection(aider)" in decision.reason
    assert not decision.low_confidence


def test_rank_candidates_capability_filter() -> None:
    c1 = Candidate(
        id="cand-1",
        tool_class=ToolClass.DETERMINISTIC,
        client="ruff",
        transport="local",
        fingerprint="v1",
        capabilities=frozenset({"simple:ruff"}),
    )
    c2 = Candidate(
        id="cand-2",
        tool_class=ToolClass.API,
        client="subllm",
        transport="api",
        fingerprint="v2",
        capabilities=frozenset({"complex:coding"}),
    )

    task = Task(TaskClass.COMPLEX, "coding", "complex logic")
    decision = rank_candidates(task=task, candidates=[c1, c2])
    assert decision.candidate == c2
    assert "unsupported_capability: requires complex:coding" in decision.rejected["cand-1"]


def test_rank_candidates_prefers_verified_probe_over_failed() -> None:
    c1 = Candidate(
        id="cand-1",
        tool_class=ToolClass.CLI,
        client="opencode",
        transport="subprocess",
        fingerprint="v1",
        capabilities=frozenset({"simple:coding"}),
    )
    c2 = Candidate(
        id="cand-2",
        tool_class=ToolClass.API,
        client="subllm",
        transport="api",
        fingerprint="v2",
        capabilities=frozenset({"simple:coding"}),
    )

    task = Task(TaskClass.SIMPLE, "coding", "test")
    evidence = {
        "cand-1": ProbeResult(status="failed", duration_ms=300, detail="rate limit 429"),
        "cand-2": ProbeResult(status="ok", duration_ms=150, detail="success"),
    }

    decision = rank_candidates(task=task, candidates=[c1, c2], evidence=evidence)
    assert decision.candidate == c2
    assert "verified_probe" in decision.reason
    assert not decision.low_confidence


def test_resolve_task_route_with_custom_candidates(tmp_path: Path) -> None:
    c1 = Candidate(
        id="cand-det",
        tool_class=ToolClass.DETERMINISTIC,
        client="ruff",
        transport="local",
        fingerprint="v1",
        capabilities=frozenset({"simple:ruff"}),
    )
    task_dict = {
        "inputs": {"task_kind": "lint_fix", "ruff_codes": ["F401"]},
        "files": ["test.py"],
    }
    decision = resolve_task_route(task_dict, project_root=tmp_path, candidates=[c1])
    assert decision.candidate == c1
    assert decision.task.key == "simple:ruff"
