"""Tests for the Planning LLM module (ADR AUTO-002 Phase 3)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from koru.autonomy.planning_llm import (
    BudgetTracker,
    LlmActionAdvice,
    LlmEvaluation,
    LlmResponse,
    _call_openrouter,
    evaluate_drive_result,
    generate_better_prompt,
    get_budget_tracker,
    plan_next_action,
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


def _fake_openrouter_response(content: dict, ok: bool = True):
    """Build an OpenRouterStrategyResponse-like object."""
    @dataclass(frozen=True)
    class FakeResp:
        ok: bool
        content: str
        error: str = ""
    return FakeResp(ok=ok, content=json.dumps(content) if ok else "", error="" if ok else "fail")


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
        bt = BudgetTracker(budget_per_cycle_usd=0.05)
        bt.record(0.02)
        assert bt.spent_usd == 0.02
        assert bt.calls == 1
        assert bt.within_budget()

    def test_over_cycle_budget(self):
        bt = BudgetTracker(budget_per_cycle_usd=0.01)
        bt.record(0.01)
        assert bt.over_cycle_budget()
        assert not bt.within_budget()

    def test_reset_cycle(self):
        bt = BudgetTracker(budget_per_cycle_usd=0.01)
        bt.record(0.01)
        assert bt.over_cycle_budget()
        bt.reset_cycle()
        assert not bt.over_cycle_budget()
        assert bt.within_budget()

    def test_to_dict(self):
        bt = BudgetTracker()
        d = bt.to_dict()
        assert "spent_usd" in d
        assert "calls" in d


# ---------------------------------------------------------------------------
# _call_openrouter
# ---------------------------------------------------------------------------

class TestCallOpenrouter:
    def test_disabled_returns_error(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "off")
        resp = _call_openrouter("test", system_prompt="test")
        assert not resp.ok
        assert "disabled" in resp.error

    def test_no_api_key_returns_error(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
        resp = _call_openrouter("test", system_prompt="test")
        assert not resp.ok
        assert "API_KEY" in resp.error

    def test_over_budget_returns_error(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        old_budget = tracker.budget_per_cycle_usd
        tracker.budget_per_cycle_usd = 0.001
        tracker.spent_usd = 0.001
        try:
            resp = _call_openrouter("test", system_prompt="test")
            assert not resp.ok
            assert "budget" in resp.error
        finally:
            tracker.budget_per_cycle_usd = old_budget
            tracker.reset_cycle()

    def test_successful_call(self, monkeypatch):
        monkeypatch.setenv("KORU_PLANNING_LLM", "1")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        tracker = get_budget_tracker()
        tracker.reset_cycle()

        fake_resp = _fake_openrouter_response({"result": "ok"})
        with patch(
            "koru.autonomy.planning_llm.call_openrouter_json",
            return_value=fake_resp,
        ) as mock_call:
            resp = _call_openrouter("test prompt", system_prompt="sys")
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
            ok: bool = True
            content: str = "not valid json {{"
            error: str = ""

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
