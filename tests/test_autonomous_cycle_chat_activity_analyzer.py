"""Unit tests for autonomous_cycle_chat_activity_analyzer.py (R-CA3)."""
from __future__ import annotations

import time
from typing import Any
from unittest import mock

import pytest

from koru.autonomous_cycle_chat_activity_analyzer import (
    _age_seconds_from_label,
    _chat_activity_cooldown_for_state,
    _event_is_self_drive_for_other_ticket,
    _event_matches_last_driven_prompt,
    _event_timestamp,
    _filter_chat_activity_events_for_waiting_ticket,
    _last_self_drive_event_age,
    _last_successful_drive_ack_age,
    _recent_chat_activity_events,
    classify_chat_event,
    decide_intake_ticket,
    decide_redrive_cooldown,
    explain_skip,
)


# ---------------------------------------------------------------------------
# _event_timestamp
# ---------------------------------------------------------------------------

def test_event_timestamp_returns_float() -> None:
    assert _event_timestamp({"ts": 1234.5}) == 1234.5


def test_event_timestamp_falls_back_to_default() -> None:
    assert _event_timestamp({}, default=99.0) == 99.0


def test_event_timestamp_handles_none_ts() -> None:
    assert _event_timestamp({"ts": None}, default=7.0) == 7.0


def test_event_timestamp_handles_bad_value() -> None:
    assert _event_timestamp({"ts": "bad"}, default=3.0) == 3.0


# ---------------------------------------------------------------------------
# _recent_chat_activity_events
# ---------------------------------------------------------------------------

def _make_state(events: list[dict[str, Any]], **kwargs: Any) -> mock.Mock:
    state = mock.Mock()
    state.autopilot_events = events
    for k, v in kwargs.items():
        setattr(state, k, v)
    return state


def test_recent_chat_activity_events_returns_matching() -> None:
    now = time.time()
    events = [
        {"type": "message.sent", "ide": "vscode", "ts": now - 10},
        {"type": "message.received", "ide": "vscode", "ts": now - 5},
        {"type": "other.event", "ide": "vscode", "ts": now - 1},
    ]
    state = _make_state(events)
    result = _recent_chat_activity_events(state, ide="vscode", within_seconds=300)
    assert len(result) == 2
    assert all(e["type"] in ("message.sent", "message.received") for e in result)


def test_recent_chat_activity_events_filters_by_ide() -> None:
    now = time.time()
    events = [
        {"type": "message.sent", "ide": "jetbrains", "ts": now - 10},
        {"type": "message.sent", "ide": "vscode", "ts": now - 5},
    ]
    state = _make_state(events)
    result = _recent_chat_activity_events(state, ide="vscode", within_seconds=300)
    assert len(result) == 1
    assert result[0]["ide"] == "vscode"


def test_recent_chat_activity_events_excludes_stale() -> None:
    now = time.time()
    events = [
        {"type": "message.sent", "ide": "vscode", "ts": now - 400},
        {"type": "message.sent", "ide": "vscode", "ts": now - 10},
    ]
    state = _make_state(events)
    result = _recent_chat_activity_events(state, ide=None, within_seconds=300)
    assert len(result) == 1
    assert result[0]["ts"] > now - 300


def test_recent_chat_activity_events_no_events() -> None:
    state = _make_state([])
    assert _recent_chat_activity_events(state, ide=None, within_seconds=300) == []


def test_recent_chat_activity_events_non_list_returns_empty() -> None:
    state = mock.Mock()
    state.autopilot_events = "not a list"
    assert _recent_chat_activity_events(state, ide=None, within_seconds=300) == []


# ---------------------------------------------------------------------------
# _chat_activity_cooldown_for_state
# ---------------------------------------------------------------------------

def test_cooldown_normal_returns_redrive_value(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "120")
    monkeypatch.delenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", raising=False)
    state = _make_state([], last_driven_kind="ticket_prompt")
    assert _chat_activity_cooldown_for_state(state) == 120.0


def test_cooldown_escalation_uses_multiplier(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "60")
    monkeypatch.delenv("KORU_AUTOPILOT_ESCALATION_COOLDOWN_SECONDS", raising=False)
    state = _make_state([], last_driven_kind="escalation_prompt")
    result = _chat_activity_cooldown_for_state(state)
    assert result > 60.0


def test_cooldown_zero_returns_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_REDRIVE_COOLDOWN_SECONDS", "0")
    state = _make_state([])
    assert _chat_activity_cooldown_for_state(state) == 0.0


# ---------------------------------------------------------------------------
# _last_successful_drive_ack_age
# ---------------------------------------------------------------------------

def test_drive_ack_age_returns_age_for_matching_ticket() -> None:
    now = time.time()
    state = _make_state(
        [],
        last_message_sent_ts=now - 30,
        last_message_sent_ide="vscode",
        last_driven_ticket_id="STARTER-1",
    )
    age = _last_successful_drive_ack_age(state, waiting_ticket="STARTER-1", ide="vscode")
    assert age is not None
    assert 28 < age < 35


def test_drive_ack_age_returns_none_for_different_ticket() -> None:
    now = time.time()
    state = _make_state(
        [],
        last_message_sent_ts=now - 10,
        last_message_sent_ide="vscode",
        last_driven_ticket_id="STARTER-2",
    )
    assert _last_successful_drive_ack_age(state, waiting_ticket="STARTER-1", ide=None) is None


def test_drive_ack_age_returns_none_for_dash_ticket() -> None:
    now = time.time()
    state = _make_state(
        [],
        last_message_sent_ts=now - 5,
        last_message_sent_ide="",
        last_driven_ticket_id="-",
    )
    assert _last_successful_drive_ack_age(state, waiting_ticket="-", ide=None) is None


def test_drive_ack_age_returns_none_for_different_ide() -> None:
    now = time.time()
    state = _make_state(
        [],
        last_message_sent_ts=now - 5,
        last_message_sent_ide="jetbrains",
        last_driven_ticket_id="STARTER-1",
    )
    assert _last_successful_drive_ack_age(state, waiting_ticket="STARTER-1", ide="vscode") is None


# ---------------------------------------------------------------------------
# _event_matches_last_driven_prompt
# ---------------------------------------------------------------------------

def test_event_matches_last_driven_prompt_exact() -> None:
    state = _make_state([], last_driven_prompt="implement feature X")
    event = {"type": "message.sent", "text": "implement feature X"}
    assert _event_matches_last_driven_prompt(state, event) is True


def test_event_matches_last_driven_prompt_wrong_type() -> None:
    state = _make_state([], last_driven_prompt="implement feature X")
    event = {"type": "message.received", "text": "implement feature X"}
    assert _event_matches_last_driven_prompt(state, event) is False


def test_event_matches_last_driven_prompt_empty_prompt() -> None:
    state = _make_state([], last_driven_prompt="")
    event = {"type": "message.sent", "text": "something"}
    assert _event_matches_last_driven_prompt(state, event) is False


# ---------------------------------------------------------------------------
# _last_self_drive_event_age
# ---------------------------------------------------------------------------

def test_last_self_drive_event_age_finds_event() -> None:
    now = time.time()
    state = _make_state([], last_driven_prompt="do the thing")
    events = [{"type": "message.sent", "text": "do the thing", "ts": now - 20}]
    age = _last_self_drive_event_age(state, events)
    assert age is not None
    assert 18 < age < 25


def test_last_self_drive_event_age_no_match() -> None:
    state = _make_state([], last_driven_prompt="do the thing")
    events = [{"type": "message.sent", "text": "something else", "ts": time.time() - 5}]
    assert _last_self_drive_event_age(state, events) is None


# ---------------------------------------------------------------------------
# _event_is_self_drive_for_other_ticket
# ---------------------------------------------------------------------------

def test_event_is_self_drive_for_other_ticket_true() -> None:
    state = _make_state([], last_driven_prompt="prompt text", last_driven_ticket_id="STARTER-1")
    event = {"type": "message.sent", "text": "prompt text"}
    assert _event_is_self_drive_for_other_ticket(state, event, "STARTER-2") is True


def test_event_is_self_drive_for_other_ticket_same_ticket() -> None:
    state = _make_state([], last_driven_prompt="prompt text", last_driven_ticket_id="STARTER-1")
    event = {"type": "message.sent", "text": "prompt text"}
    assert _event_is_self_drive_for_other_ticket(state, event, "STARTER-1") is False


def test_event_is_self_drive_for_other_ticket_dash() -> None:
    state = _make_state([], last_driven_prompt="prompt text", last_driven_ticket_id="STARTER-1")
    event = {"type": "message.sent", "text": "prompt text"}
    assert _event_is_self_drive_for_other_ticket(state, event, "-") is False


# ---------------------------------------------------------------------------
# _filter_chat_activity_events_for_waiting_ticket
# ---------------------------------------------------------------------------

def test_filter_removes_self_drive_for_other_ticket() -> None:
    state = _make_state([], last_driven_prompt="old prompt", last_driven_ticket_id="STARTER-1")
    events = [
        {"type": "message.sent", "text": "old prompt", "ts": time.time()},
        {"type": "message.received", "text": "response", "ts": time.time()},
    ]
    result = _filter_chat_activity_events_for_waiting_ticket(state, events, "STARTER-2")
    assert len(result) == 1
    assert result[0]["type"] == "message.received"


# ---------------------------------------------------------------------------
# classify_chat_event
# ---------------------------------------------------------------------------

def test_classify_chat_event_with_state_events() -> None:
    now = time.time()
    state = _make_state([])
    events = [{"type": "message.received", "ts": now - 5}]
    has_activity, ev_type, age, ref_events = classify_chat_event(
        state=state, ide=None, cooldown=300, recent_events=events, reflection_events=[]
    )
    assert has_activity is True
    assert ev_type == "message.received"
    assert age.endswith("s")


def test_classify_chat_event_no_events_no_history(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the koruide.chat_history fallback so on-disk state from other tests
    # cannot leak into this isolation test.
    import koruide.chat_history as chat_history

    monkeypatch.setattr(chat_history, "has_recent_activity", lambda **_: False)
    state = _make_state([])
    has_activity, ev_type, age, ref_events = classify_chat_event(
        state=state, ide=None, cooldown=300, recent_events=[], reflection_events=[]
    )
    assert has_activity is False
    assert ev_type == ""
    assert age == ""


# ---------------------------------------------------------------------------
# decide_intake_ticket
# ---------------------------------------------------------------------------

def test_decide_intake_ticket_true_when_ticket_id() -> None:
    assert decide_intake_ticket("STARTER-42") is True


def test_decide_intake_ticket_false_when_none() -> None:
    assert decide_intake_ticket(None) is False


def test_decide_intake_ticket_false_when_empty() -> None:
    assert decide_intake_ticket("") is False


# ---------------------------------------------------------------------------
# decide_redrive_cooldown
# ---------------------------------------------------------------------------

def test_decide_redrive_cooldown_skip_within_cooldown() -> None:
    result = decide_redrive_cooldown(
        event_type="message.sent",
        age_seconds=15.0,
        cooldown_seconds=60.0,
        waiting_ticket="STARTER-1",
    )
    assert result["should_skip"] is True
    assert result["event_type"] == "message.sent"
    assert "STARTER-1" in str(result["because"])


def test_decide_redrive_cooldown_no_skip_past_cooldown() -> None:
    result = decide_redrive_cooldown(
        event_type="message.sent",
        age_seconds=120.0,
        cooldown_seconds=60.0,
        waiting_ticket="STARTER-1",
    )
    assert result["should_skip"] is False


def test_decide_redrive_cooldown_age_label_format() -> None:
    result = decide_redrive_cooldown(
        event_type="message.received",
        age_seconds=42.0,
        cooldown_seconds=300.0,
        waiting_ticket="-",
    )
    assert result["age"] == "42s"


# ---------------------------------------------------------------------------
# explain_skip
# ---------------------------------------------------------------------------

def test_explain_skip_returns_because_string() -> None:
    decision = {"should_skip": True, "because": "recent_chat_activity last=x age=10s"}
    assert explain_skip(decision) == "recent_chat_activity last=x age=10s"


def test_explain_skip_empty_decision() -> None:
    assert explain_skip({}) == ""


# ---------------------------------------------------------------------------
# _age_seconds_from_label
# ---------------------------------------------------------------------------

def test_age_seconds_from_label_parses_seconds() -> None:
    from koru.autonomous_cycle_chat_activity_analyzer import _age_seconds_from_label
    assert _age_seconds_from_label("42s") == 42.0
    assert _age_seconds_from_label("0s") == 0.0


def test_age_seconds_from_label_non_seconds_label() -> None:
    from koru.autonomous_cycle_chat_activity_analyzer import _age_seconds_from_label
    assert _age_seconds_from_label("bad") == 0.0


def test_age_seconds_from_label_invalid_number() -> None:
    from koru.autonomous_cycle_chat_activity_analyzer import _age_seconds_from_label
    assert _age_seconds_from_label("xs") == 0.0


# ---------------------------------------------------------------------------
# Backward-compat: public symbols still importable from main module
# ---------------------------------------------------------------------------

def test_backward_compat_imports_from_main_module() -> None:
    """classify_chat_event etc. must still be importable from the original module."""
    from koru.autonomous_cycle_chat_activity import (
        classify_chat_event as cc,
        decide_intake_ticket as di,
        decide_redrive_cooldown as dr,
        explain_skip as es,
    )
    assert cc is classify_chat_event
    assert di is decide_intake_ticket
    assert dr is decide_redrive_cooldown
    assert es is explain_skip
