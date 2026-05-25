"""Tests for koru.autonomy.decision_arbiter."""

import pytest

from koru.autonomy.decision_arbiter import (
    ActionPlan,
    ArbiterSignals,
    decide,
)
from koru.autonomy.verification_engine import (
    Evidence,
    GitEvidence,
    TestEvidence,
    ChatEvidence,
    Verdict,
)


# ---------------------------------------------------------------------------
# Heuristic vetoes
# ---------------------------------------------------------------------------


class TestHeuristicVetoes:
    def test_cooldown_active(self):
        signals = ArbiterSignals(
            cooldown_active=True,
            cooldown_remaining_seconds=120.0,
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "wait"
        assert plan.sleep_seconds == 120.0
        assert "cooldown" in plan.reason

    def test_chat_activity_blocked(self):
        signals = ArbiterSignals(
            chat_activity_blocked=True,
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "wait"
        assert "clobber" in plan.reason

    def test_tests_failing(self):
        signals = ArbiterSignals(
            test_status="failing",
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "wait"
        assert "failing" in plan.reason


# ---------------------------------------------------------------------------
# Verdict-based decisions
# ---------------------------------------------------------------------------


class TestVerdictDecisions:
    def test_completed_closes_ticket(self):
        verdict = Verdict(
            outcome="completed",
            confidence=0.8,
            reason="git: 3 files changed; tests: passing",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            verdict=verdict,
            waiting_ticket="T-1",
            queue_status="waiting_input",
        )
        plan = decide(signals)
        assert plan.action == "close_ticket"
        assert plan.ticket_id == "T-1"
        assert plan.confidence == 0.8

    def test_degraded_escalates(self):
        verdict = Verdict(
            outcome="degraded",
            confidence=0.3,
            reason="tests: failing",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            verdict=verdict,
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "escalate_ticket"

    def test_no_change_after_3_drives_escalates(self):
        verdict = Verdict(
            outcome="no_change",
            confidence=0.1,
            reason="git: no changes",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            verdict=verdict,
            waiting_ticket="T-1",
            drive_count_for_ticket=3,
        )
        plan = decide(signals)
        assert plan.action == "escalate_ticket"
        assert "3 drives" in plan.reason

    def test_no_change_after_2_drives_redrives(self):
        verdict = Verdict(
            outcome="no_change",
            confidence=0.1,
            reason="git: no changes",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            verdict=verdict,
            waiting_ticket="T-1",
            drive_count_for_ticket=2,
        )
        plan = decide(signals)
        assert plan.action == "redrive_improved"

    def test_low_confidence_completed_not_closed(self):
        verdict = Verdict(
            outcome="completed",
            confidence=0.5,
            reason="partial evidence",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            verdict=verdict,
            waiting_ticket="T-1",
            queue_status="waiting_input",
        )
        plan = decide(signals)
        assert plan.action != "close_ticket"


# ---------------------------------------------------------------------------
# Queue-based decisions
# ---------------------------------------------------------------------------


class TestQueueDecisions:
    def test_idle_no_tickets_runs_discovery(self):
        signals = ArbiterSignals(
            queue_status="idle",
            has_open_tickets=False,
        )
        plan = decide(signals)
        assert plan.action == "run_discovery"

    def test_waiting_input_drives_ticket(self):
        signals = ArbiterSignals(
            queue_status="waiting_input",
            waiting_ticket="T-2",
        )
        plan = decide(signals)
        assert plan.action == "drive_ticket"
        assert plan.ticket_id == "T-2"

    def test_stagnation_switches(self):
        signals = ArbiterSignals(
            stagnation_streak=5,
            waiting_ticket="T-3",
        )
        plan = decide(signals)
        assert plan.action == "switch_ticket"

    def test_default_noop(self):
        signals = ArbiterSignals()
        plan = decide(signals)
        assert plan.action == "noop"


# ---------------------------------------------------------------------------
# ActionPlan serialization
# ---------------------------------------------------------------------------


class TestActionPlanSerialization:
    def test_to_dict(self):
        plan = ActionPlan(
            action="drive_ticket",
            ticket_id="T-1",
            reason="test",
            confidence=0.9,
        )
        d = plan.to_dict()
        assert d["action"] == "drive_ticket"
        assert d["ticket_id"] == "T-1"
        assert d["confidence"] == 0.9


# ---------------------------------------------------------------------------
# Priority chain integration
# ---------------------------------------------------------------------------


class TestPriorityChain:
    def test_cooldown_overrides_verdict(self):
        """Heuristic veto (cooldown) has higher priority than verdict."""
        verdict = Verdict(
            outcome="completed",
            confidence=0.9,
            reason="all good",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            cooldown_active=True,
            cooldown_remaining_seconds=60.0,
            verdict=verdict,
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "wait"

    def test_test_failure_overrides_verdict(self):
        """Heuristic veto (test failure) overrides completed verdict."""
        verdict = Verdict(
            outcome="completed",
            confidence=0.8,
            reason="git changes present",
            ticket_id="T-1",
        )
        signals = ArbiterSignals(
            test_status="failing",
            verdict=verdict,
            waiting_ticket="T-1",
        )
        plan = decide(signals)
        assert plan.action == "wait"
        assert "failing" in plan.reason
