"""Tests for the Planning LLM module (ADR AUTO-002 Phase 3)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path  # noqa: F401
from unittest.mock import MagicMock, patch  # noqa: F401

import pytest  # noqa: F401

from koru.autonomy.planning_llm import (
    BudgetTracker,
    LlmActionAdvice,
    LlmEvaluation,
    LlmReflection,
    LlmResponse,  # noqa: F401
    StrategyTuning,
    TicketPriority,
    _call_planning_llm,
    evaluate_drive_result,
    generate_better_prompt,
    get_budget_tracker,
    plan_next_action,
    prioritize_tickets,
    propose_strategy_tuning,
    reflect_on_chat,
)
from koru.autonomy.verification_engine import (
    ChatEvidence,
    Evidence,
    GitEvidence,
    TestEvidence,
    Verdict,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_evidence(
    *,
    files_changed: int = 0,
    insertions: int = 0,
    deletions: int = 0,
    test_status: str = "ok",
    chat_events: int = 0,
    has_message_sent: bool = False,
) -> Evidence:
    return Evidence(
        git=GitEvidence(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
        ),
        tests=TestEvidence(status=test_status),
        chat=ChatEvidence(
            events_since_drive=chat_events,
            has_message_sent=has_message_sent,
        ),
    )


def _fake_cursor_response(content: dict, ok: bool = True):
    """Build a CursorLlmResult-like object."""
    @dataclass(frozen=True)
    class FakeResp:
        returncode: int
        stdout: str
        stderr: str = ""
        model: str = "grok-4.6"
        usage: dict | None = None

    return FakeResp(
        returncode=0 if ok else 1,
        stdout=json.dumps(content) if ok else "",
        stderr="" if ok else "fail",
        usage={},
    )


_fake_openrouter_response = _fake_cursor_response


# ---------------------------------------------------------------------------
# BudgetTracker
# ---------------------------------------------------------------------------

class TestBudgetTracker:
    def test_initial_state(self):
        bt = BudgetTracker()
        assert bt.spent_usd == 0.0
        assert bt.calls == 0
        assert bt.within_budget()

    def test_record_spend(self):
        bt = BudgetTracker()
        bt.record(0.02)
        assert bt.spent_usd == 0.02
        assert bt.calls == 1
        assert bt.within_budget()

    def test_spend_never_blocks_calls(self):
        bt = BudgetTracker()
        bt.record(1_000_000.0)
        assert bt.within_budget()

    def test_reset_cycle(self):
        bt = BudgetTracker()
        bt.record(0.01)
        bt.reset_cycle()
        assert bt.spent_usd == 0.0
        assert bt.within_budget()

    def test_to_dict(self):
        bt = BudgetTracker()
        d = bt.to_dict()
        assert "spent_usd" in d
        assert "calls" in d


# ---------------------------------------------------------------------------
# _call_planning_llm
# ---------------------------------------------------------------------------

class TestCallPlanningLlm:
    def test_disabled_returns_error(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        resp = _call_planning_llm("test", system_prompt="test")
        assert not resp.ok
        assert "disabled" in resp.error

    def test_cursor_route_error_is_returned(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        failed = _fake_cursor_response({}, ok=False)
        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=failed):
            resp = _call_planning_llm("test", system_prompt="test")
        assert not resp.ok
        assert "fail" in resp.error

    def test_successful_call(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        fake_resp = _fake_cursor_response({"result": "ok"})
        with patch(
            "koru.autonomy.planning_llm.call_openrouter_json",
            return_value=fake_resp,
        ) as mock_call:
            resp = _call_planning_llm("test prompt", system_prompt="sys")
            assert resp.ok
            assert '"result"' in resp.content
            mock_call.assert_called_once()


# ---------------------------------------------------------------------------
# evaluate_drive_result
# ---------------------------------------------------------------------------

class TestEvaluateDriveResult:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        evidence = _make_evidence()
        result = evaluate_drive_result(evidence, ticket_id="T-1")
        assert result is None

    def test_returns_evaluation_on_success(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "outcome": "completed",
            "confidence": 0.85,
            "reason": "Git shows new files, tests pass",
            "suggestion": "Close ticket",
        }
        fake_resp = _fake_openrouter_response(llm_response)
        evidence = _make_evidence(files_changed=3, test_status="ok")

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = evaluate_drive_result(
                evidence,
                ticket_id="T-1",
                ticket_title="Add login form",
                driven_prompt="Create a login form",
            )

        assert result is not None
        assert result.outcome == "completed"
        assert result.confidence == 0.85
        assert "pass" in result.reason
        assert result.suggestion == "Close ticket"

    def test_returns_none_on_invalid_json(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        @dataclass(frozen=True)
        class BadResp:
            returncode: int = 0
            stdout: str = "not valid json {{"
            stderr: str = ""
            model: str = "grok-4.6"
            usage: dict | None = None

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=BadResp()):
            result = evaluate_drive_result(_make_evidence(), ticket_id="T-1")
        assert result is None

    def test_clamps_confidence(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"outcome": "completed", "confidence": 99.0, "reason": "x"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = evaluate_drive_result(_make_evidence(), ticket_id="T-1")
        assert result is not None
        assert result.confidence == 1.0

    def test_includes_heuristic_verdict_in_prompt(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        verdict = Verdict(
            outcome="in_progress",
            confidence=0.4,
            reason="git: 1 file changed; tests: ok",
            evidence=_make_evidence(),
        )
        llm_response = {"outcome": "in_progress", "confidence": 0.6, "reason": "partial"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp) as mock:
            evaluate_drive_result(
                _make_evidence(),
                ticket_id="T-1",
                heuristic_verdict=verdict,
            )
            call_prompt = mock.call_args[0][0]
            assert "Heuristic verdict" in call_prompt
            assert "in_progress" in call_prompt


# ---------------------------------------------------------------------------
# generate_better_prompt
# ---------------------------------------------------------------------------

class TestGenerateBetterPrompt:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        result = generate_better_prompt(
            ticket_id="T-1",
            ticket_title="Fix bug",
            original_prompt="Fix the login bug",
            drive_count=3,
        )
        assert result is None

    def test_returns_improved_prompt(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "improved_prompt": "Fix the login validation in src/auth.py by adding email format check",
            "changes": "Added specific file path and function",
        }
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = generate_better_prompt(
                ticket_id="T-1",
                ticket_title="Fix login bug",
                original_prompt="Fix the login bug",
                drive_count=3,
                last_verdict_reason="no change after 3 drives",
            )

        assert result is not None
        assert "auth.py" in result

    def test_returns_none_on_empty_improved_prompt(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"improved_prompt": "", "changes": "nothing"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = generate_better_prompt(
                ticket_id="T-1",
                ticket_title="Fix",
                original_prompt="Fix it",
                drive_count=2,
            )
        assert result is None


# ---------------------------------------------------------------------------
# plan_next_action
# ---------------------------------------------------------------------------

class TestPlanNextAction:
    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        result = plan_next_action(
            queue_status="idle",
            waiting_tickets=[],
            stagnation_streak=0,
            test_status="ok",
        )
        assert result is None

    def test_returns_advice_on_success(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "action": "run_discovery",
            "ticket_id": None,
            "reason": "Queue is empty, find new work",
            "confidence": 0.9,
        }
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = plan_next_action(
                queue_status="idle",
                waiting_tickets=[],
                stagnation_streak=0,
                test_status="ok",
            )

        assert result is not None
        assert result.action == "run_discovery"
        assert result.confidence == 0.9

    def test_invalid_action_normalised_to_noop(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"action": "fly_to_moon", "reason": "x", "confidence": 0.5}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = plan_next_action(
                queue_status="idle",
                waiting_tickets=[],
                stagnation_streak=0,
                test_status="ok",
            )
        assert result is not None
        assert result.action == "noop"

    def test_to_dict(self):
        advice = LlmActionAdvice(action="drive_ticket", ticket_id="T-1", reason="go")
        d = advice.to_dict()
        assert d["action"] == "drive_ticket"
        assert d["ticket_id"] == "T-1"


# ---------------------------------------------------------------------------
# LlmEvaluation serialization
# ---------------------------------------------------------------------------

class TestLlmEvaluationSerialization:
    def test_to_dict(self):
        ev = LlmEvaluation(outcome="completed", confidence=0.8, reason="done")
        d = ev.to_dict()
        assert d["outcome"] == "completed"
        assert d["confidence"] == 0.8


# ---------------------------------------------------------------------------
# reflect_on_chat (Phase 4)
# ---------------------------------------------------------------------------


class TestReflectOnChat:
    def test_returns_none_for_empty_events(self):
        result = reflect_on_chat(
            ticket_id="T-1",
            ticket_title="Fix bug",
            driven_prompt="Fix the bug",
            chat_events=[],
        )
        assert result is None

    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        result = reflect_on_chat(
            ticket_id="T-1",
            ticket_title="Fix bug",
            driven_prompt="Fix it",
            chat_events=[{"type": "message.received", "text": "Done"}],
        )
        assert result is None

    def test_returns_reflection_on_success(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"done": True, "needs_input": False, "summary": "Task completed"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = reflect_on_chat(
                ticket_id="T-1",
                ticket_title="Fix bug",
                driven_prompt="Fix it",
                chat_events=[
                    {"type": "message.sent", "text": "Fix it"},
                    {"type": "message.received", "text": "Done, fixed the bug"},
                ],
            )

        assert result is not None
        assert result.done is True
        assert result.needs_input is False
        assert "completed" in result.summary

    def test_needs_input_flag(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"done": False, "needs_input": True, "summary": "LLM is asking a question"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = reflect_on_chat(
                ticket_id="T-1",
                ticket_title="Fix bug",
                driven_prompt="Fix it",
                chat_events=[{"type": "message.received", "text": "Which file?"}],
            )

        assert result is not None
        assert result.done is False
        assert result.needs_input is True

    def test_to_dict(self):
        r = LlmReflection(done=True, needs_input=False, summary="done")
        d = r.to_dict()
        assert d["done"] is True
        assert d["summary"] == "done"


# ---------------------------------------------------------------------------
# propose_strategy_tuning (Phase 4)
# ---------------------------------------------------------------------------


class TestProposeStrategyTuning:
    def test_returns_none_for_empty_decisions(self):
        result = propose_strategy_tuning(
            current_strategy_yaml="id: test",
            recent_decisions=[],
        )
        assert result is None

    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        result = propose_strategy_tuning(
            current_strategy_yaml="id: test",
            recent_decisions=[{"cycle": 1, "skip_code": "ok"}],
        )
        assert result is None

    def test_returns_tuning_on_success(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "patch": "idle_discovery:\n  min_interval_seconds: 30",
            "reason": "Too many idle cycles, reduce interval",
            "confidence": 0.7,
        }
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = propose_strategy_tuning(
                current_strategy_yaml="id: accordion\nidle_discovery:\n  min_interval_seconds: 60",
                recent_decisions=[
                    {"cycle": i, "skip_code": "idle_streak"} for i in range(5)
                ],
            )

        assert result is not None
        assert "30" in result.patch
        assert result.confidence == 0.7

    def test_returns_none_on_empty_patch_and_reason(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"patch": "", "reason": "", "confidence": 0.1}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = propose_strategy_tuning(
                current_strategy_yaml="id: test",
                recent_decisions=[{"cycle": 1}],
            )
        assert result is None

    def test_to_dict(self):
        t = StrategyTuning(patch="x: 1", reason="tune", confidence=0.5)
        d = t.to_dict()
        assert d["patch"] == "x: 1"


# ---------------------------------------------------------------------------
# prioritize_tickets (Phase 4)
# ---------------------------------------------------------------------------


class TestPrioritizeTickets:
    def test_returns_none_for_single_ticket(self):
        result = prioritize_tickets(tickets=[{"id": "T-1", "title": "Fix"}])
        assert result is None

    def test_returns_none_when_disabled(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        result = prioritize_tickets(
            tickets=[
                {"id": "T-1", "title": "Fix bug"},
                {"id": "T-2", "title": "Add feature"},
            ],
        )
        assert result is None

    def test_returns_priority_on_success(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "ordered": ["T-2", "T-1"],
            "reason": "T-2 fixes failing tests",
            "confidence": 0.8,
        }
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = prioritize_tickets(
                tickets=[
                    {"id": "T-1", "title": "Add feature"},
                    {"id": "T-2", "title": "Fix failing test"},
                ],
                test_status="failing",
            )

        assert result is not None
        assert result.ordered_ticket_ids == ("T-2", "T-1")
        assert result.confidence == 0.8

    def test_filters_invalid_ticket_ids(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {
            "ordered": ["T-1", "FAKE-99", "T-2"],
            "reason": "order",
            "confidence": 0.5,
        }
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = prioritize_tickets(
                tickets=[
                    {"id": "T-1", "title": "A"},
                    {"id": "T-2", "title": "B"},
                ],
            )

        assert result is not None
        assert "FAKE-99" not in result.ordered_ticket_ids
        assert result.ordered_ticket_ids == ("T-1", "T-2")

    def test_returns_none_if_no_valid_ids(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        llm_response = {"ordered": ["FAKE-1", "FAKE-2"], "reason": "x"}
        fake_resp = _fake_openrouter_response(llm_response)

        with patch("koru.autonomy.planning_llm.call_openrouter_json", return_value=fake_resp):
            result = prioritize_tickets(
                tickets=[{"id": "T-1", "title": "A"}, {"id": "T-2", "title": "B"}],
            )
        assert result is None

    def test_to_dict(self):
        tp = TicketPriority(ordered_ticket_ids=("T-1", "T-2"), reason="go")
        d = tp.to_dict()
        assert d["ordered_ticket_ids"] == ["T-1", "T-2"]
