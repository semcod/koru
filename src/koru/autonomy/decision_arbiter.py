"""Decision arbiter — merges heuristic signals into a typed ``ActionPlan``.

Phase 2 of ADR AUTO-002.  The arbiter replaces scattered ``if/elif``
branches in ``autonomous_cycle_orchestrator`` with a single structured
decision object that the cycle runner can execute generically.

Priority chain:
  1. **Heuristic veto** — test failure ⇒ stop, cooldown ⇒ wait
  2. **Verification verdict** — task done ⇒ close, no change ⇒ redrive
  3. **Planning LLM** (Phase 3, optional) — priority, prompt improvement
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Literal

from koru.autonomy.verification_engine import Verdict

ActionKind = Literal[
    "drive_ticket",
    "redrive_improved",
    "close_ticket",
    "escalate_ticket",
    "switch_ticket",
    "run_discovery",
    "wait",
    "reflect",
    "noop",
]


@dataclass(frozen=True)
class ActionPlan:
    """What the autonomous loop should do next."""

    action: ActionKind
    ticket_id: str | None = None
    prompt: str | None = None
    reason: str = ""
    confidence: float = 0.0
    sleep_seconds: float = 0.0
    evidence: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ArbiterSignals:
    """Inputs the arbiter considers when making a decision."""

    queue_status: str = ""
    waiting_ticket: str = ""
    stagnation_streak: int = 0
    drive_count_for_ticket: int = 0
    cooldown_active: bool = False
    cooldown_remaining_seconds: float = 0.0
    test_status: str = "unknown"
    verdict: Verdict | None = None
    has_open_tickets: bool = False
    chat_activity_blocked: bool = False


# ---------------------------------------------------------------------------
# Core decision function
# ---------------------------------------------------------------------------

def _plan_wait(
    signals: ArbiterSignals,
    *,
    reason: str,
    sleep_seconds: float,
) -> ActionPlan:
    return ActionPlan(
        action="wait",
        ticket_id=signals.waiting_ticket or None,
        reason=reason,
        sleep_seconds=sleep_seconds,
    )


def _ticket_id_for_verdict(signals: ArbiterSignals, verdict: Verdict) -> str | None:
    return verdict.ticket_id or signals.waiting_ticket or None


def _verdict_plan(
    signals: ArbiterSignals,
    verdict: Verdict,
    *,
    action: ActionKind,
    reason: str,
) -> ActionPlan:
    return ActionPlan(
        action=action,
        ticket_id=_ticket_id_for_verdict(signals, verdict),
        reason=reason,
        confidence=verdict.confidence,
        evidence=verdict.to_dict(),
    )


def _decide_heuristic_veto(signals: ArbiterSignals) -> ActionPlan | None:
    if signals.cooldown_active:
        return _plan_wait(
            signals,
            reason=f"cooldown active ({signals.cooldown_remaining_seconds:.0f}s)",
            sleep_seconds=signals.cooldown_remaining_seconds,
        )

    if signals.chat_activity_blocked:
        return _plan_wait(
            signals,
            reason="chat activity cooldown (would clobber user)",
            sleep_seconds=30.0,
        )

    if signals.test_status in {"failing", "failed", "error", "down"}:
        return _plan_wait(
            signals,
            reason=f"tests {signals.test_status} — waiting for fix",
            sleep_seconds=15.0,
        )

    return None


def _decide_verdict(signals: ArbiterSignals) -> ActionPlan | None:
    verdict = signals.verdict
    if verdict is None:
        return None

    if verdict.outcome == "completed" and verdict.confidence >= 0.6:
        return _verdict_plan(
            signals,
            verdict,
            action="close_ticket",
            reason=verdict.reason,
        )

    if verdict.outcome == "degraded":
        return _verdict_plan(
            signals,
            verdict,
            action="escalate_ticket",
            reason=f"tests degraded after drive: {verdict.reason}",
        )

    if verdict.outcome == "submitted_but_no_effect":
        return _verdict_plan(
            signals,
            verdict,
            action="escalate_ticket",
            reason=(
                "prompt was submitted but no local work was applied; "
                f"{verdict.reason}"
            ),
        )

    if verdict.outcome != "no_change":
        return None

    if signals.drive_count_for_ticket >= 3:
        return _verdict_plan(
            signals,
            verdict,
            action="escalate_ticket",
            reason=f"no change after {signals.drive_count_for_ticket} drives",
        )

    if signals.drive_count_for_ticket >= 2:
        return _verdict_plan(
            signals,
            verdict,
            action="redrive_improved",
            reason=(
                f"no change after {signals.drive_count_for_ticket} drives "
                "— retry with improved prompt"
            ),
        )

    return None


def _decide_queue_state(signals: ArbiterSignals) -> ActionPlan | None:
    if signals.queue_status == "idle" and not signals.has_open_tickets:
        return ActionPlan(
            action="run_discovery",
            reason="queue idle, no open tickets",
        )

    if signals.queue_status == "waiting_input" and signals.waiting_ticket:
        return ActionPlan(
            action="drive_ticket",
            ticket_id=signals.waiting_ticket,
            reason="ticket waiting for input",
        )

    if signals.stagnation_streak >= 5:
        return ActionPlan(
            action="switch_ticket",
            ticket_id=signals.waiting_ticket or None,
            reason=f"stagnation streak={signals.stagnation_streak}",
        )

    return None


def _default_plan(signals: ArbiterSignals) -> ActionPlan:
    if signals.waiting_ticket:
        return ActionPlan(
            action="drive_ticket",
            ticket_id=signals.waiting_ticket,
            reason="default: drive waiting ticket",
        )

    return ActionPlan(
        action="noop",
        reason="no actionable signal",
    )


def decide(signals: ArbiterSignals) -> ActionPlan:
    """Produce an ``ActionPlan`` from the current signals.

    The function applies the priority chain documented in the module
    docstring.  Each rule can short-circuit with a return.
    """
    for decider in (_decide_heuristic_veto, _decide_verdict, _decide_queue_state):
        plan = decider(signals)
        if plan is not None:
            return plan
    return _default_plan(signals)


__all__ = [
    "ActionKind",
    "ActionPlan",
    "ArbiterSignals",
    "decide",
]
