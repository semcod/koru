"""Tests for autonomous_cycle_chat_activity_text module (R-CA2 extraction).

Targets the pure text-processing helpers directly. These functions have no
Koru dependencies (only ``re``) so they can be tested in isolation.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from koru.autonomous_cycle_chat_activity_text import (
    compact_question_text,
    extract_needs_input_question,
    latest_received_text,
    looks_like_autopilot_generated_prompt,
    looks_like_explicit_intake_text,
    normalize_prompt_text,
)


# ---------------------------------------------------------------------------
# normalize_prompt_text
# ---------------------------------------------------------------------------


def test_normalize_prompt_text_collapses_whitespace_and_lowercases() -> None:
    assert normalize_prompt_text("  Hello   WORLD\n\t!  ") == "hello world !"


def test_normalize_prompt_text_handles_none_and_empty() -> None:
    assert normalize_prompt_text("") == ""
    assert normalize_prompt_text(None) == ""  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# looks_like_autopilot_generated_prompt
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "Ticket PLF-1 has been stuck in status 'waiting_input' for 5 cycles",
        "Work on planfile ticket PLF-2: implement X",
        "Planfile ticket done PLF-3 with status review",
        "The queue is blocked on waiting_input for ticket PLF-4",
    ],
)
def test_looks_like_autopilot_generated_prompt_true_for_autopilot_templates(text: str) -> None:
    assert looks_like_autopilot_generated_prompt(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "bug: foo crashes on startup",
        "please look at src/koru/queue.py:42",
        "What is the expected behavior here?",
    ],
)
def test_looks_like_autopilot_generated_prompt_false_for_user_intake(text: str) -> None:
    assert looks_like_autopilot_generated_prompt(text) is False


# ---------------------------------------------------------------------------
# looks_like_explicit_intake_text
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "text",
    [
        "/etc/hosts is unreadable",
        "./scripts/foo.py errors out",
        "../sibling/repo broken",
        "~/notes.md missing",
        "bug: crash on launch",
        "task: refactor module",
        "todo: write tests",
        "ticket: link to PLF-1",
        "fix: typo in README",
        "feature: dark mode",
        "Look at src/koru/queue.py for context",
        "tests/test_foo.py is failing",
        "docs/README.md needs update",
    ],
)
def test_looks_like_explicit_intake_text_true_for_real_intake(text: str) -> None:
    assert looks_like_explicit_intake_text(text) is True


@pytest.mark.parametrize(
    "text",
    [
        "",
        "hello there",
        "what should I do",
        "Ticket PLF-1 has been stuck in status",
    ],
)
def test_looks_like_explicit_intake_text_false_for_chat(text: str) -> None:
    assert looks_like_explicit_intake_text(text) is False


# ---------------------------------------------------------------------------
# compact_question_text
# ---------------------------------------------------------------------------


def test_compact_question_text_collapses_and_truncates() -> None:
    assert compact_question_text("  hello\n  world  ") == "hello world"


def test_compact_question_text_respects_limit() -> None:
    assert compact_question_text("a" * 1000, limit=10) == "a" * 10


def test_compact_question_text_empty_returns_empty() -> None:
    assert compact_question_text("") == ""
    assert compact_question_text("   ") == ""


# ---------------------------------------------------------------------------
# extract_needs_input_question
# ---------------------------------------------------------------------------


def _event(type_: str, text: str = "", summary: str = "") -> SimpleNamespace:
    return SimpleNamespace(type=type_, text=text, summary=summary)


def test_extract_needs_input_question_finds_question_mark_in_received_text() -> None:
    events = [
        _event("message.sent", "Working on the task..."),
        _event("message.received", "What configuration values should I use for production?"),
    ]
    result = extract_needs_input_question(events, reflection_summary="")
    assert result == "What configuration values should I use for production?"


def test_extract_needs_input_question_falls_back_to_clarification_marker() -> None:
    events = [
        _event(
            "message.received",
            "Please provide the deployment target before I can proceed",
        ),
    ]
    result = extract_needs_input_question(events, reflection_summary="")
    assert "please provide" in result.lower()


def test_extract_needs_input_question_falls_back_to_summary_with_question_mark() -> None:
    events: list[SimpleNamespace] = []
    summary = "Need input: which environment should I target?"
    result = extract_needs_input_question(events, reflection_summary=summary)
    assert "?" in result


def test_extract_needs_input_question_returns_empty_when_no_signal() -> None:
    events: list[SimpleNamespace] = []
    assert extract_needs_input_question(events, reflection_summary="just a status update") == ""


def test_extract_needs_input_question_prefers_newest_event() -> None:
    events = [
        _event("message.received", "Old question?"),
        _event("message.received", "New question for the user?"),
    ]
    result = extract_needs_input_question(events, reflection_summary="")
    assert result == "New question for the user?"


def test_extract_needs_input_question_skips_empty_events() -> None:
    events = [
        _event("message.received", "What value to use?"),
        _event("message.received", "   "),
    ]
    result = extract_needs_input_question(events, reflection_summary="")
    assert result == "What value to use?"


# ---------------------------------------------------------------------------
# latest_received_text
# ---------------------------------------------------------------------------


def test_latest_received_text_returns_newest_received_message() -> None:
    events = [
        _event("message.sent", "outgoing"),
        _event("message.received", "first response"),
        _event("message.received", "latest response from LLM"),
    ]
    assert latest_received_text(events) == "latest response from LLM"


def test_latest_received_text_returns_empty_when_no_received_message() -> None:
    events = [_event("message.sent", "only outgoing")]
    assert latest_received_text(events) == ""


def test_latest_received_text_falls_back_to_summary_field() -> None:
    events = [_event("message.received", text="", summary="summary text")]
    assert latest_received_text(events) == "summary text"


# ---------------------------------------------------------------------------
# Re-export contract
# ---------------------------------------------------------------------------


def test_legacy_aliases_remain_importable_from_chat_activity_module() -> None:
    """Existing imports of ``_normalize_prompt_text`` etc. from
    ``koru.autonomous_cycle_chat_activity`` must keep working after R-CA2."""

    from koru.autonomous_cycle_chat_activity import (
        _compact_question_text,
        _extract_needs_input_question,
        _latest_received_text,
        _looks_like_autopilot_generated_prompt,
        _looks_like_explicit_intake_text,
        _normalize_prompt_text,
    )

    assert _normalize_prompt_text is normalize_prompt_text
    assert _looks_like_autopilot_generated_prompt is looks_like_autopilot_generated_prompt
    assert _looks_like_explicit_intake_text is looks_like_explicit_intake_text
    assert _compact_question_text is compact_question_text
    assert _extract_needs_input_question is extract_needs_input_question
    assert _latest_received_text is latest_received_text
