"""Characterize the rendered request passed from discovery to execution."""

import pytest

from koru.autonomy.todo2code_discovery import _ticket_text

RESTRICTION = (
    "Implement only the declared target paths, then re-run "
    "`t2c evaluate-code-change` / pipeline before marking the ticket done."
)


@pytest.mark.parametrize(
    ("plan", "opening"),
    [
        ({}, "Implement grounded todo2code code-change plan."),
        ({"title": " Title "}, "Title"),
        ({"description": " Detail ", "title": "Title"}, "Detail"),
        ({"description": " ", "title": 42}, "42"),
    ],
)
def test_ticket_text_opening_and_execution_restriction(plan, opening):
    assert _ticket_text(plan, plans_rel="plans.json") == opening + "\n\n" + RESTRICTION


def test_ticket_text_preserves_complete_request_and_section_order():
    plan = {
        "description": " Implement parser ",
        "id": " plan-1 ",
        "planHash": " abc ",
        "target": {"paths": ["src/parser.py"]},
        "changes": [
            {"path": " src/parser.py ", "action": " add ", "symbols": ["parse", " "], "rationale": " Handle input "},
            {"path": "src/parser.py"},
            None,
        ],
        "acceptanceCriteria": [" Preserved spacing ", "", "Parses input"],
        "risk": {"level": " low ", "reasons": [" Reason "]},
        "rollback": " Revert parser ",
        "evidence": {"diagnosticIds": ["D-1", "D-2"]},
    }
    assert _ticket_text(plan, plans_rel="project/plans.json") == "\n".join(
        [
            "Implement parser",
            "",
            "Plan id: plan-1",
            "Plan hash: abc",
            "Source artifact: project/plans.json",
            "",
            "Target paths:",
            "- src/parser.py",
            "",
            "Proposed changes:",
            "- add `src/parser.py` (parse): Handle input",
            "- modify `src/parser.py`",
            "",
            "Acceptance criteria:",
            "-  Preserved spacing ",
            "- Parses input",
            "",
            "Risk: low",
            "-  Reason ",
            "",
            "Rollback: Revert parser",
            "",
            "Diagnostics:",
            "- D-1",
            "- D-2",
            "",
            RESTRICTION,
        ]
    )


@pytest.mark.parametrize("value", [None, [], "bad", 7])
def test_ticket_text_ignores_non_mapping_risk_and_evidence(value):
    plan = {"title": "Task", "risk": value, "evidence": value}
    assert _ticket_text(plan, plans_rel="plans.json") == "Task\n\n" + RESTRICTION


def test_ticket_text_preserves_partial_sections_and_change_defaults():
    plan = {
        "title": "Task",
        "planHash": "hash",
        "changes": [False, {}],
        "risk": {"reasons": ["Review needed"]},
    }
    assert _ticket_text(plan, plans_rel="plans.json") == "\n".join(
        [
            "Task",
            "",
            "Plan id: n/a",
            "Plan hash: hash",
            "Source artifact: plans.json",
            "",
            "Proposed changes:",
            "- modify ``",
            "",
            "Risk: unknown",
            "- Review needed",
            "",
            RESTRICTION,
        ]
    )


@pytest.mark.parametrize("changes", [None, {}, "bad", 7, [None, False, "bad"]])
def test_ticket_text_ignores_invalid_change_containers_and_entries(changes):
    assert _ticket_text({"title": "Task", "changes": changes}, plans_rel="p") == ("Task\n\n" + RESTRICTION)


def test_ticket_text_does_not_hide_invalid_criteria_type():
    with pytest.raises(TypeError):
        _ticket_text({"acceptanceCriteria": 7}, plans_rel="p")
