"""Unit tests for autonomous_cycle_chat_activity_tickets.py (R7a)."""
from __future__ import annotations

from typing import Any
from unittest import mock

import pytest

import time

from koru.autonomous_cycle_chat_activity_tickets import (
    _external_message_sent_text,
    _llm_needs_input_operator_payload,
    _llm_needs_input_summary,
    _llm_needs_input_waiting_ticket,
    _recent_llm_reflection_summary,
    _upsert_chat_intake_operator_ticket,
    _upsert_llm_needs_input_operator_ticket,
)


def _make_queue_result(**kwargs: Any) -> mock.Mock:
    qr = mock.Mock()
    qr.last_status = kwargs.get("last_status", "waiting_input")
    qr.last_message = kwargs.get("last_message", "")
    qr.last_ticket_id = kwargs.get("last_ticket_id", "")
    qr.waiting_ticket_id = kwargs.get("waiting_ticket_id", "")
    qr.waiting = kwargs.get("waiting", [])
    return qr


# ---------------------------------------------------------------------------
# _llm_needs_input_waiting_ticket
# ---------------------------------------------------------------------------

def test_waiting_ticket_uses_queue_label_when_present(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "STARTER-42",
    )
    qr = _make_queue_result(last_ticket_id="STARTER-99")
    assert _llm_needs_input_waiting_ticket(qr) == "STARTER-42"


def test_waiting_ticket_falls_back_to_last_ticket_id(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "-",
    )
    qr = _make_queue_result(last_ticket_id="STARTER-99")
    assert _llm_needs_input_waiting_ticket(qr) == "STARTER-99"


def test_waiting_ticket_returns_dash_when_nothing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "-",
    )
    qr = _make_queue_result(last_ticket_id="")
    assert _llm_needs_input_waiting_ticket(qr) == "-"


# ---------------------------------------------------------------------------
# _llm_needs_input_summary
# ---------------------------------------------------------------------------

def test_summary_returns_reflection_summary_when_set() -> None:
    qr = _make_queue_result(last_message="other")
    assert _llm_needs_input_summary(qr, "  the reflection  ") == "the reflection"


def test_summary_falls_back_to_queue_message() -> None:
    qr = _make_queue_result(last_message="  the queue msg  ")
    assert _llm_needs_input_summary(qr, "") == "the queue msg"


def test_summary_default_when_empty() -> None:
    qr = _make_queue_result(last_message="")
    assert _llm_needs_input_summary(qr, "") == (
        "IDE-side LLM requested additional input without details."
    )


# ---------------------------------------------------------------------------
# _llm_needs_input_operator_payload
# ---------------------------------------------------------------------------

def test_operator_payload_contains_expected_fields() -> None:
    qr = _make_queue_result(last_message="we are blocked")
    title, prompt, scaffold = _llm_needs_input_operator_payload(
        queue_result=qr,
        waiting_ticket="STARTER-7",
        summary="missing API key",
        question="Which API key should I use?",
    )
    assert title == "[OPERATOR] STARTER-7: provide missing IDE input"
    assert "Blocked ticket: STARTER-7" in prompt
    assert "Detected question: Which API key should I use?" in prompt
    assert "Reflection summary: missing API key" in prompt
    assert scaffold["executor_kind"] == "human"
    assert "waiting:STARTER-7" in scaffold["labels"]
    assert scaffold["source_context"]["dedupe_key"] == "autopilot-needs-input:STARTER-7"


def test_operator_payload_omits_question_line_when_empty() -> None:
    qr = _make_queue_result()
    _title, prompt, _scaffold = _llm_needs_input_operator_payload(
        queue_result=qr,
        waiting_ticket="-",
        summary="some summary",
        question="",
    )
    assert "Detected question:" not in prompt


# ---------------------------------------------------------------------------
# _upsert_llm_needs_input_operator_ticket
# ---------------------------------------------------------------------------

def test_upsert_returns_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_enabled",
        lambda: False,
    )
    state = mock.Mock()
    qr = _make_queue_result()
    result = _upsert_llm_needs_input_operator_ticket(
        project=mock.Mock(),
        queue_result=qr,
        state=state,
        reflection_summary="x",
        reflection_events=[],
        report_progress=lambda *_a, **_k: None,
    )
    assert result is None


def test_upsert_dedupes_on_signature(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "STARTER-1",
    )
    qr = _make_queue_result(last_message="msg")

    state = mock.Mock()
    state.last_operator_needs_input_signature = "STARTER-1|the summary"
    state.last_operator_needs_input_ticket_id = "STARTER-OP-9"

    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._extract_needs_input_question",
        lambda *_a, **_k: "",
    )

    result = _upsert_llm_needs_input_operator_ticket(
        project=tmp_path,
        queue_result=qr,
        state=state,
        reflection_summary="the summary",
        reflection_events=[],
        report_progress=lambda *_a, **_k: None,
    )
    assert result == "STARTER-OP-9"


def test_upsert_creates_ticket_via_create_nl_task(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_queue_name",
        lambda: "operator",
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_priority",
        lambda: 1,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "STARTER-1",
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._extract_needs_input_question",
        lambda *_a, **_k: "Q?",
    )

    captured: dict[str, Any] = {}

    def _fake_create(project, prompt, *, queue_name, priority, scaffold):
        captured.update(
            project=project, prompt=prompt, queue_name=queue_name,
            priority=priority, scaffold=scaffold,
        )
        return mock.Mock(ticket_id="STARTER-OP-100", reused=False)

    # Monkeypatch through koru.autonomous_cycle so the lazy lookup picks it up.
    import koru.autonomous_cycle as cycle_mod

    monkeypatch.setattr(cycle_mod, "create_nl_task", _fake_create, raising=False)

    state = mock.Mock()
    state.last_operator_needs_input_signature = ""
    state.last_operator_needs_input_ticket_id = ""

    qr = _make_queue_result(last_message="msg")
    notes: list[str] = []
    result = _upsert_llm_needs_input_operator_ticket(
        project=tmp_path,
        queue_result=qr,
        state=state,
        reflection_summary="the summary",
        reflection_events=[],
        report_progress=lambda msg, *_a, **_k: notes.append(str(msg)),
    )
    assert result == "STARTER-OP-100"
    assert state.last_operator_needs_input_ticket_id == "STARTER-OP-100"
    assert captured["queue_name"] == "operator"
    assert captured["priority"] == 1
    assert any("created operator ticket" in n for n in notes)


def test_upsert_returns_none_on_create_failure(
    monkeypatch: pytest.MonkeyPatch, tmp_path
) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_queue_name",
        lambda: "operator",
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._llm_needs_input_ticket_priority",
        lambda: 1,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._queue_loop_waiting_ticket_label",
        lambda _qr: "STARTER-1",
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._extract_needs_input_question",
        lambda *_a, **_k: "",
    )

    def _boom(*_a, **_k):
        raise RuntimeError("planfile down")

    import koru.autonomous_cycle as cycle_mod

    monkeypatch.setattr(cycle_mod, "create_nl_task", _boom, raising=False)

    state = mock.Mock()
    state.last_operator_needs_input_signature = ""
    state.last_operator_needs_input_ticket_id = ""

    notes: list[str] = []
    result = _upsert_llm_needs_input_operator_ticket(
        project=tmp_path,
        queue_result=_make_queue_result(),
        state=state,
        reflection_summary="x",
        reflection_events=[],
        report_progress=lambda msg, *_a, **_k: notes.append(str(msg)),
    )
    assert result is None
    assert any("upsert failed" in n for n in notes)


# ---------------------------------------------------------------------------
# _recent_llm_reflection_summary
# ---------------------------------------------------------------------------

def test_recent_llm_reflection_summary_valid() -> None:
    state = mock.Mock()
    state.last_llm_reflection_summary = "found issue"
    state.last_llm_reflection_ts = time.time() - 10
    assert _recent_llm_reflection_summary(state) == "found issue"


def test_recent_llm_reflection_summary_stale() -> None:
    state = mock.Mock()
    state.last_llm_reflection_summary = "found issue"
    state.last_llm_reflection_ts = time.time() - 100000
    assert _recent_llm_reflection_summary(state) == ""


# ---------------------------------------------------------------------------
# _external_message_sent_text
# ---------------------------------------------------------------------------

def test_external_message_sent_text_finds_msg() -> None:
    state = mock.Mock()
    state.last_driven_prompt = "re-drive"
    events = [
        {"type": "message.sent", "text": "bug: hey computer"},
    ]
    assert _external_message_sent_text(state=state, recent_events=events) == "bug: hey computer"


def test_external_message_sent_text_skips_generated() -> None:
    state = mock.Mock()
    state.last_driven_prompt = "re-drive"
    events = [
        {"type": "message.sent", "text": "[AUTOPILOT] go"},
    ]
    assert _external_message_sent_text(state=state, recent_events=events) == ""


# ---------------------------------------------------------------------------
# _upsert_chat_intake_operator_ticket
# ---------------------------------------------------------------------------

def test_upsert_chat_intake_returns_none_when_disabled(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._chat_intake_ticket_enabled",
        lambda: False,
    )
    result = _upsert_chat_intake_operator_ticket(
        project=mock.Mock(),
        queue_result=_make_queue_result(),
        state=mock.Mock(),
        recent_events=[],
        cycle_telemetry={},
        report_progress=lambda *_a, **_k: None,
    )
    assert result is None


def test_upsert_chat_intake_creates_ticket(monkeypatch: pytest.MonkeyPatch, tmp_path) -> None:
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._chat_intake_ticket_enabled",
        lambda: True,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._waiting_ticket_has_chat_intake_label",
        lambda *_a, **_k: False,
    )
    monkeypatch.setattr(
        "koru.autonomous_cycle_chat_activity_tickets._external_message_sent_text",
        lambda **_k: "help me",
    )

    captured = {}
    def _fake_create(project, prompt, *, queue_name, priority, scaffold):
        captured.update(prompt=prompt, queue_name=queue_name, priority=priority, scaffold=scaffold)
        return mock.Mock(ticket_id="STARTER-OP-500", reused=False)

    import koru.autonomous_cycle as cycle_mod
    monkeypatch.setattr(cycle_mod, "create_nl_task", _fake_create, raising=False)

    telemetry = {}
    qr = _make_queue_result(last_status="waiting_input")
    result = _upsert_chat_intake_operator_ticket(
        project=tmp_path,
        queue_result=qr,
        state=mock.Mock(),
        recent_events=[],
        cycle_telemetry=telemetry,
        report_progress=lambda *_a, **_k: None,
    )
    assert result == "STARTER-OP-500"
    assert telemetry["autopilot_chat_intake_ticket"] == "STARTER-OP-500"
    assert "help me" in captured["prompt"]


# ---------------------------------------------------------------------------
# Backward-compat re-exports
# ---------------------------------------------------------------------------

def test_backward_compat_reexports_from_main_module() -> None:
    from koru.autonomous_cycle_chat_activity import (
        _llm_needs_input_operator_payload as legacy_payload,
        _llm_needs_input_summary as legacy_summary,
        _llm_needs_input_waiting_ticket as legacy_waiting,
        _upsert_llm_needs_input_operator_ticket as legacy_upsert,
        _recent_llm_reflection_summary as legacy_reflection,
        _upsert_chat_intake_operator_ticket as legacy_intake,
    )

    assert legacy_payload is _llm_needs_input_operator_payload
    assert legacy_summary is _llm_needs_input_summary
    assert legacy_waiting is _llm_needs_input_waiting_ticket
    assert legacy_upsert is _upsert_llm_needs_input_operator_ticket
    assert legacy_reflection is _recent_llm_reflection_summary
    assert legacy_intake is _upsert_chat_intake_operator_ticket
