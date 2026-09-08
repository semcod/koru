"""Characterize dispatch precedence and ticket selector boundaries."""

from __future__ import annotations

import pytest

from koru.autonomy import execution_plan as execution


@pytest.mark.parametrize("match", [None, [], "bad", 7])
def test_non_mapping_match_is_rejected(match):
    assert not execution._profile_matches({"match": match}, ticket={}, phase="work")


@pytest.mark.parametrize(("phase", "expected"), [("work", True), ("WORK", False)])
def test_phase_match_overrides_ticket_selectors_and_missing_ticket(phase, expected):
    profile = {"match": {"phase": "work", "labels_any": ["absent"]}}
    assert execution._profile_matches(profile, ticket=None, phase=phase) is expected


@pytest.mark.parametrize("match", [{}, {"phase": ""}, {"labels_any": []}, {"signals_any": []}, {"name_patterns": []}])
def test_empty_selectors_never_match(match):
    assert not execution._profile_matches({"match": match}, ticket={}, phase="work")


def test_ticket_is_required_without_phase_selector():
    assert not execution._profile_matches({"match": {"name_patterns": ["*"]}}, ticket=None, phase="work")


@pytest.mark.parametrize(
    ("match", "ticket", "expected"),
    [
        ({"labels_any": ["HOT"]}, {"labels": ["hot"]}, True),
        ({"labels_any": ["hot"]}, {"labels": "hot"}, False),
        ({"labels_any": ["hot"]}, {"labels": [" hot "]}, False),
        ({"signals_any": ["CC"]}, {"source": {"context": {"signal": "CC"}}}, True),
        ({"signals_any": ["cc"]}, {"source": {"context": {"signal": "CC"}}}, False),
        ({"signals_any": ["CC"]}, {"source": []}, False),
        ({"name_patterns": ["TASK-*"]}, {"id": "TASK-1"}, True),
        ({"name_patterns": ["Task *"]}, {"name": " Task one "}, True),
        ({"phase": "", "labels_any": ["hot"]}, {"labels": ["HOT"]}, True),
    ],
)
def test_selector_normalization_and_fallbacks(match, ticket, expected):
    assert execution._profile_matches({"match": match}, ticket=ticket, phase="work") is expected


@pytest.mark.parametrize("missing", [None, "labels", "source", "name"])
def test_all_declared_selector_groups_must_match(missing):
    match = {"labels_any": ["hot"], "signals_any": ["CC"], "name_patterns": ["Task *"]}
    ticket = {"labels": ["HOT"], "source": {"context": {"signal": "CC"}}, "name": "Task one"}
    if missing:
        ticket.pop(missing)
    assert execution._profile_matches({"match": match}, ticket=ticket, phase="work") is (missing is None)


def test_failed_labels_do_not_read_later_selectors(monkeypatch):
    def unexpected(*args):
        pytest.fail("later selector evaluated after labels rejected the profile")

    monkeypatch.setattr(execution, "_ticket_signal", unexpected)
    assert not execution._profile_matches({"match": {"labels_any": ["hot"]}}, ticket={}, phase="work")
