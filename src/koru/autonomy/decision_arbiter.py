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

def decide(signals: ArbiterSignals) -> ActionPlan:
    """Produce an ``ActionPlan`` from the current signals.

    The function applies the priority chain documented in the module
    docstring.  Each rule can short-circuit with a return.
    """

    # 1. Heuristic vetoes --------------------------------------------------

    if signals.cooldown_active:
        return ActionPlan(
            action="wait",
            ticket_id=signals.waiting_ticket or None,
            reason=f"cooldown active ({signals.cooldown_remaining_seconds:.0f}s)",
            sleep_seconds=signals.cooldown_remaining_seconds,
        )

    if signals.chat_activity_blocked:
        return ActionPlan(
            action="wait",
            ticket_id=signals.waiting_ticket or None,
            reason="chat activity cooldown (would clobber user)",
            sleep_seconds=30.0,
        )

    if signals.test_status in {"failing", "failed", "error", "down"}:
        return ActionPlan(
            action="wait",
            ticket_id=signals.waiting_ticket or None,
            reason=f"tests {signals.test_status} — waiting for fix",
            sleep_seconds=15.0,
        )

    # 2. Verification verdict ----------------------------------------------

    if signals.verdict is not None:
        verdict = signals.verdict
        if verdict.outcome == "completed" and verdict.confidence >= 0.6:
            return ActionPlan(
                action="close_ticket",
                ticket_id=verdict.ticket_id or signals.waiting_ticket or None,
                reason=verdict.reason,
                confidence=verdict.confidence,
                evidence=verdict.to_dict(),
            )

        if verdict.outcome == "degraded":
            return ActionPlan(
                action="escalate_ticket",
                ticket_id=verdict.ticket_id or signals.waiting_ticket or None,
                reason=f"tests degraded after drive: {verdict.reason}",
                confidence=verdict.confidence,
                evidence=verdict.to_dict(),
            )

        if verdict.outcome == "no_change" and signals.drive_count_for_ticket >= 3:
            return ActionPlan(
                action="escalate_ticket",
                ticket_id=verdict.ticket_id or signals.waiting_ticket or None,
                reason=f"no change after {signals.drive_count_for_ticket} drives",
                confidence=verdict.confidence,
                evidence=verdict.to_dict(),
            )

        if verdict.outcome == "no_change" and signals.drive_count_for_ticket >= 2:
            return ActionPlan(
                action="redrive_improved",
                ticket_id=verdict.ticket_id or signals.waiting_ticket or None,
                reason=f"no change after {signals.drive_count_for_ticket} drives — retry with improved prompt",
                confidence=verdict.confidence,
                evidence=verdict.to_dict(),
            )

    # 3. Queue-based decisions ---------------------------------------------

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

    # 4. Default: drive current ticket -------------------------------------

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


__all__ = [
    "ActionKind",
    "ActionPlan",
    "ArbiterSignals",
    "decide",
]
