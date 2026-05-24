"""Tests for PromptStrategy — context-aware prompt building for autopilot."""

from __future__ import annotations

import pytest

from koru.autonomy.prompts import (
    DEFAULT_ESCALATION_THRESHOLD,
    build_prompt,
)


def _call(**overrides):
    base = dict(
        queue_status="idle",
        last_message="",
        waiting_ticket_id=None,
        drive_prompt="continue with the next ticket",
        autopilot_action="drive",
        stagnation_streak=0,
    )
    base.update(overrides)
    return build_prompt(**base)


def test_idle_status_uses_drive_prompt():
    """Idle queue → outer drive prompt is used as-is."""
    decision = _call(queue_status="idle")
    assert decision.kind == "drive_prompt"
    assert decision.prompt == "continue with the next ticket"
    assert decision.skip is False


def test_handoff_action_returns_drive_prompt():
    """Handoff action overrides everything → drive_prompt."""
    decision = _call(
        autopilot_action="handoff",
        queue_status="waiting_input",
        last_message="ignored",
    )
    assert decision.kind == "handoff"
    assert decision.prompt == "continue with the next ticket"


def test_waiting_input_with_message_uses_ticket_prompt():
    """waiting_input + ticket message → ticket message is sent."""
    decision = _call(
        queue_status="waiting_input",
        last_message="Please review the tests for module X",
        waiting_ticket_id="PLF-1234",
    )
    assert decision.kind == "ticket_prompt"
    assert decision.prompt.startswith("Please review the tests for module X")
    assert "planfile ticket done PLF-1234" in decision.prompt
    assert "planfile ticket input PLF-1234" in decision.prompt


def test_waiting_input_empty_message_uses_fallback_prompt():
    """waiting_input + empty message → fallback (NOT skip) so loop progresses."""
    decision = _call(
        queue_status="waiting_input",
        last_message="",
        waiting_ticket_id="PLF-1234",
    )
    assert decision.kind == "fallback_prompt"
    assert decision.skip is False
    assert "PLF-1234" in decision.prompt
    assert "planfile ticket done PLF-1234" in decision.prompt
    assert "next pending ticket" in decision.prompt.lower() or "continue" in decision.prompt.lower()


def test_waiting_input_empty_message_no_ticket_id():
    """Empty message + no ticket id → still produces a fallback prompt."""
    decision = _call(
        queue_status="waiting_input",
        last_message="",
        waiting_ticket_id=None,
    )
    assert decision.kind == "fallback_prompt"
    assert decision.prompt  # non-empty
    assert decision.skip is False


def test_waiting_input_strips_whitespace_message():
    """A message of only whitespace is treated as empty."""
    decision = _call(
        queue_status="waiting_input",
        last_message="   \n   ",
        waiting_ticket_id="PLF-9",
    )
    assert decision.kind == "fallback_prompt"


def test_waiting_input_does_not_duplicate_planfile_handoff():
    decision = _call(
        queue_status="waiting_input",
        last_message="Do it\n\nPlanfile status handoff:\n- When complete, run: `planfile ticket done PLF-9`",
        waiting_ticket_id="PLF-9",
    )
    assert decision.kind == "ticket_prompt"
    assert decision.prompt.count("planfile ticket done PLF-9") == 1


def test_stagnation_below_threshold_no_escalation():
    """Stagnation streak below threshold → normal prompt, no escalation."""
    decision = _call(
        queue_status="waiting_input",
        last_message="msg",
        waiting_ticket_id="PLF-1",
        stagnation_streak=DEFAULT_ESCALATION_THRESHOLD - 1,
    )
    assert decision.kind == "ticket_prompt"


def test_stagnation_at_threshold_triggers_escalation():
    """Stagnation streak >= threshold → escalation_prompt."""
    decision = _call(
        queue_status="waiting_input",
        last_message="Refactor duplicate classes",
        waiting_ticket_id="PLF-42",
        stagnation_streak=DEFAULT_ESCALATION_THRESHOLD,
    )
    assert decision.kind == "escalation_prompt"
    assert "PLF-42" in decision.prompt
    assert "stuck" in decision.prompt.lower()
    assert "Refactor duplicate classes" in decision.prompt
    assert "planfile ticket done PLF-42" in decision.prompt
    assert "planfile ticket input PLF-42" in decision.prompt
    assert "planfile ticket fail PLF-42" in decision.prompt


def test_escalation_includes_status_and_streak():
    """Escalation prompt mentions both status and streak count."""
    decision = _call(
        queue_status="waiting_input",
        waiting_ticket_id="PLF-7",
        stagnation_streak=5,
    )
    assert decision.kind == "escalation_prompt"
    assert "waiting_input" in decision.prompt
    assert "5" in decision.prompt


def test_escalation_skipped_without_ticket_id():
    """No ticket id → cannot escalate (we don't know which ticket); fallback instead."""
    decision = _call(
        queue_status="waiting_input",
        last_message="",
        waiting_ticket_id=None,
        stagnation_streak=DEFAULT_ESCALATION_THRESHOLD + 5,
    )
    # Without a ticket id, escalation is meaningless → fallback
    assert decision.kind == "fallback_prompt"


def test_custom_escalation_threshold():
    """Caller can override escalation threshold."""
    decision = _call(
        queue_status="waiting_input",
        waiting_ticket_id="PLF-1",
        stagnation_streak=2,
        escalation_threshold=2,
    )
    assert decision.kind == "escalation_prompt"


def test_drive_action_with_running_status():
    """Non-blocking status → outer drive prompt."""
    decision = _call(queue_status="running", autopilot_action="drive")
    assert decision.kind == "drive_prompt"


def test_decision_is_frozen():
    """PromptDecision is immutable (frozen dataclass)."""
    decision = _call()
    with pytest.raises(AttributeError):
        decision.prompt = "modified"  # type: ignore
