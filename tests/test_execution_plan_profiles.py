"""Tests for extracted execution plan profiles and step generators."""

from __future__ import annotations

from pathlib import Path

from koru.autonomy.execution_plan_profiles import (
    fallback_profile_id,
    load_task_profiles,
    profile_labels_match,
    profile_order,
    select_profile,
    ticket_labels,
    ticket_likely_complete,
    ticket_name,
    ticket_signal,
)
from koru.autonomy.execution_plan_steps import (
    pr_steps,
    worktree_steps,
)
from koru.autonomy.task_strategies import PendingPR, PendingWorktree


def test_load_task_profiles() -> None:
    data = load_task_profiles()
    assert isinstance(data, dict)
    assert "profiles" in data
    assert "defaults" in data


def test_profile_helpers() -> None:
    data = load_task_profiles()
    order = profile_order(data)
    assert isinstance(order, tuple)
    assert len(order) > 0

    fallback = fallback_profile_id(data)
    assert fallback in data["profiles"]


def test_ticket_metadata_extraction() -> None:
    ticket = {
        "id": "T-1",
        "name": "Refactor module",
        "labels": ["God-Module", "Refactor"],
        "source": {"context": {"signal": "god_module"}},
    }
    assert ticket_name(ticket) == "Refactor module"
    assert ticket_labels(ticket) == {"god-module", "refactor"}
    assert ticket_signal(ticket) == "god_module"
    assert profile_labels_match(ticket_labels(ticket), ["god-module"])


def test_select_profile() -> None:
    ticket = {
        "id": "T-2",
        "name": "Split god module foo",
        "labels": ["god-module"],
        "source": {"context": {"signal": "god_module"}},
    }
    pid, profile = select_profile(ticket, "planfile_queue")
    assert pid is not None
    assert isinstance(profile, dict)


def test_ticket_likely_complete(tmp_path: Path) -> None:
    src_file = tmp_path / "small.py"
    src_file.write_text("x = 1\n", encoding="utf-8")

    ticket = {
        "id": "T-3",
        "files": ["small.py"],
        "labels": ["god-module"],
    }
    # < 250 lines -> likely complete
    assert ticket_likely_complete(tmp_path, ticket) is True


def test_step_generation(tmp_path: Path) -> None:
    pr = PendingPR(
        number=999,
        title="fix: test",
        head_branch="ticket/999-fix",
        url="https://github.com/test/999",
    )
    steps = pr_steps(tmp_path, pr)
    assert len(steps) == 2
    assert steps[0].id == "view_pr"
    assert steps[1].id == "finish_pr"

    wt = PendingWorktree(
        path=tmp_path / "wt",
        branch="ticket/999-fix",
        head_sha="abcdef",
        ticket_id="ticket-999",
        is_dirty=False,
        is_merged=False,
        commits_ahead=1,
    )
    wt_steps = worktree_steps(tmp_path, wt)
    assert len(wt_steps) == 3
    assert wt_steps[0].id == "status_worktree"
    assert wt_steps[1].id == "test_worktree"
    assert wt_steps[2].id == "finish_worktree"


def test_select_profile_god_function() -> None:
    ticket = {
        "id": "PLF-033",
        "name": "Address code smell: God Function: main",
        "labels": ["koru", "nl-task", "llm-ready", "code2llm", "code-smell", "god-function"],
        "source": {
            "context": {
                "signal": "code2llm_smell_god_function",
            },
        },
    }
    pid, profile = select_profile(ticket, "planfile_queue")
    assert pid == "god_function_refactor"
    assert isinstance(profile, dict)
    hints = [step.get("hint") for step in profile.get("workflow", []) if "hint" in step]
    assert any("Decompose the oversized function" in h for h in hints)


def test_select_profile_code_smells() -> None:
    for signal, smell_label, name in [
        ("code2llm_smell_shotgun_surgery", "shotgun-surgery", "Address code smell: Shotgun Surgery: found"),
        ("code2llm_smell_data_clump", "data-clump", "Address code smell: Data Clump: client_params"),
        ("code2llm_smell_feature_envy", "feature-envy", "Address code smell: Feature Envy: parse_row"),
    ]:
        ticket = {
            "id": "PLF-041",
            "name": name,
            "labels": ["koru", "code-smell", smell_label],
            "source": {"context": {"signal": signal}},
        }
        pid, profile = select_profile(ticket, "planfile_queue")
        assert pid == "code_smell_refactor", f"Expected code_smell_refactor for {signal}, got {pid}"
        assert isinstance(profile, dict)


def test_select_profile_cc_hotspot_code2llm_cc() -> None:
    ticket = {
        "id": "PLF-050",
        "name": "Reduce cyclomatic complexity: parse_args (CC=14, limit=10)",
        "labels": ["code2llm", "complexity", "refactor", "scan"],
        "source": {"context": {"signal": "code2llm_cc"}},
    }
    pid, profile = select_profile(ticket, "planfile_queue")
    assert pid == "cc_hotspot_refactor"
    assert isinstance(profile, dict)


def test_profile_order_precedence() -> None:
    data = load_task_profiles()
    order = profile_order(data)
    assert "cc_hotspot_refactor" in order
    assert "god_function_refactor" in order
    assert "code_smell_refactor" in order
    assert "god_module_split" in order
    # Verify god_function and code_smell are prioritized before god_module_split
    assert order.index("god_function_refactor") < order.index("god_module_split")
    assert order.index("code_smell_refactor") < order.index("god_module_split")

