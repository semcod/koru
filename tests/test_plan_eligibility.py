"""Eligibility boundaries must survive changes to plan classification."""

from __future__ import annotations

import pytest

from koru.autonomy import code_change_usefulness as usefulness


def _plan(**updates):
    return {"target": {"paths": ["src/main.py"]}, **updates}


@pytest.mark.parametrize(
    ("action", "exists", "expected"),
    [
        ("create", False, True),
        ("create", True, False),
        ("CREATE", False, True),
        (" create ", False, False),
        ("modify", False, False),
        ("modify", True, True),
        (None, False, False),
        (None, True, True),
        ("delete", False, False),
        ("delete", True, True),
    ],
)
def test_action_requires_matching_filesystem_state(tmp_path, action, exists, expected):
    (tmp_path / "src").mkdir()
    if exists:
        (tmp_path / "src/main.py").write_text("pass\n")
    plan = _plan(changes=[{"path": "./src/main.py", "action": action}])
    assert usefulness.is_useful_plan(plan, project=tmp_path) is expected


@pytest.mark.parametrize("action", ["create", "modify", "delete"])
def test_no_project_does_not_impose_filesystem_preconditions(action):
    assert usefulness.is_useful_plan(_plan(changes=[{"path": "src/main.py", "action": action}]))


@pytest.mark.parametrize(
    "updates",
    [
        {"evidence": {"recordIds": ["INT-CHANGELOG-1"]}},
        {"risk": {"level": " HIGH "}},
    ],
)
def test_review_required_plan_never_reaches_path_or_score_evaluation(monkeypatch, updates):
    def unexpected(*args, **kwargs):
        pytest.fail("review-required plan reached path/score evaluation")

    monkeypatch.setattr(usefulness, "plan_useful_paths", unexpected)
    monkeypatch.setattr(usefulness, "plan_usefulness_score", unexpected)
    assert not usefulness.is_useful_plan(_plan(**updates), min_score=-100)


def test_mixed_evidence_is_not_changelog_only():
    assert usefulness.is_useful_plan(_plan(evidence={"recordIds": ["INT-CHANGELOG-1", "CODE-1"]}))


def test_last_normalized_action_wins_and_invalid_entries_are_ignored(tmp_path):
    plan = _plan(
        changes=[
            None,
            "bad",
            {"path": "src/main.py", "action": "modify"},
            {"path": "./src/main.py", "action": "create"},
        ]
    )
    assert usefulness.is_useful_plan(plan, project=tmp_path)
    plan["changes"].reverse()
    assert not usefulness.is_useful_plan(plan, project=tmp_path)


@pytest.mark.parametrize("changes", [None, {}, "invalid"])
def test_non_list_changes_default_to_modifying_target(tmp_path, changes):
    assert not usefulness.is_useful_plan(_plan(changes=changes), project=tmp_path)


def test_score_threshold_is_inclusive():
    plan = _plan()
    score = usefulness.plan_usefulness_score(plan)
    assert usefulness.is_useful_plan(plan, min_score=score)
    assert not usefulness.is_useful_plan(plan, min_score=score + 0.01)


def test_directory_is_not_an_existing_file(tmp_path):
    (tmp_path / "src/main.py").mkdir(parents=True)
    assert not usefulness.is_useful_plan(_plan(), project=tmp_path)


def test_failed_precondition_does_not_evaluate_score(tmp_path, monkeypatch):
    def unexpected(*args, **kwargs):
        pytest.fail("missing modification target reached score evaluation")

    monkeypatch.setattr(usefulness, "plan_usefulness_score", unexpected)
    assert not usefulness.is_useful_plan(_plan(), project=tmp_path)
