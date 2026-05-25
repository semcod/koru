"""Planning LLM — OpenRouter-backed planner and evaluator.

Phase 3 of ADR AUTO-002.  Provides three capabilities:

1. **evaluate_drive_result** — LLM-enhanced verdict (augments heuristic)
2. **generate_better_prompt** — improved prompt after failed drives
3. **plan_next_action** — advisory action plan from LLM (optional)

All functions are **fail-safe**: if OpenRouter is unavailable, over budget,
or returns garbage, the caller gets a typed ``None`` (or a fallback) and
the cycle continues with heuristics only.
"""

from __future__ import annotations

import json
import os
import time
from dataclasses import asdict, dataclass, field
from typing import Any

from koru.autonomy.verification_engine import Evidence, Verdict
from koru.autonomy_strategy.openrouter import call_openrouter_json

# ---------------------------------------------------------------------------
# Budget tracking (per-process, intentionally not persisted)
# ---------------------------------------------------------------------------

_DEFAULT_BUDGET_PER_CYCLE_USD = 0.02
_DEFAULT_BUDGET_PER_HOUR_USD = 0.50
_DEFAULT_MODEL = "qwen/qwen3-coder-next"


@dataclass
class BudgetTracker:
    """In-memory spend tracker.  Resets on process restart."""

    spent_usd: float = 0.0
    calls: int = 0
    first_call_ts: float = 0.0
    last_call_ts: float = 0.0
    budget_per_cycle_usd: float = _DEFAULT_BUDGET_PER_CYCLE_USD
    budget_per_hour_usd: float = _DEFAULT_BUDGET_PER_HOUR_USD

    def record(self, cost_usd: float) -> None:
        now = time.time()
        if self.first_call_ts == 0.0:
            self.first_call_ts = now
        self.last_call_ts = now
        self.calls += 1
        self.spent_usd += cost_usd

    def over_cycle_budget(self) -> bool:
        return self.spent_usd >= self.budget_per_cycle_usd

    def over_hour_budget(self) -> bool:
        if self.first_call_ts == 0.0:
            return False
        elapsed = time.time() - self.first_call_ts
        if elapsed >= 3600:
            self.spent_usd = 0.0
            self.calls = 0
            self.first_call_ts = time.time()
            return False
        return self.spent_usd >= self.budget_per_hour_usd

    def within_budget(self) -> bool:
        return not self.over_cycle_budget() and not self.over_hour_budget()

    def reset_cycle(self) -> None:
        """Call at the start of each cycle to allow per-cycle spend."""
        self.spent_usd = 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


_budget = BudgetTracker()


def get_budget_tracker() -> BudgetTracker:
    return _budget


# ---------------------------------------------------------------------------
# Configuration helpers
# ---------------------------------------------------------------------------

def _planning_llm_enabled() -> bool:
    raw = os.environ.get("KORU_PLANNING_LLM", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def _api_key() -> str:
    return os.environ.get("OPENROUTER_API_KEY", "").strip()


def _model() -> str:
    return os.environ.get("KORU_PLANNING_LLM_MODEL", "").strip() or _DEFAULT_MODEL


def _timeout() -> float:
    raw = os.environ.get("KORU_PLANNING_LLM_TIMEOUT", "").strip()
    try:
        return max(5.0, float(raw)) if raw else 30.0
    except ValueError:
        return 30.0


# ---------------------------------------------------------------------------
# Low-level OpenRouter call (reuses existing infra)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LlmResponse:
    ok: bool
    content: str
    error: str = ""
    cost_usd: float = 0.0
    model: str = ""
    usage: dict[str, Any] = field(default_factory=dict)


def _call_openrouter(
    prompt: str,
    *,
    system_prompt: str,
    response_json: bool = True,
) -> LlmResponse:
    """Call OpenRouter with budget guard and fallback."""
    if not _planning_llm_enabled():
        return LlmResponse(ok=False, content="", error="planning LLM disabled")
    key = _api_key()
    if not key:
        return LlmResponse(ok=False, content="", error="OPENROUTER_API_KEY not set")
    if not _budget.within_budget():
        return LlmResponse(ok=False, content="", error="over budget")

    model = _model()
    resp = call_openrouter_json(
        prompt,
        system_prompt=system_prompt,
        model=model,
        api_key=key,
        timeout_seconds=_timeout(),
    )
    cost = 0.0
    _budget.record(cost)

    if not resp.ok:
        return LlmResponse(ok=False, content="", error=resp.error, model=model)
    return LlmResponse(ok=True, content=resp.content, model=model, cost_usd=cost)


# ---------------------------------------------------------------------------
# 1. evaluate_drive_result — LLM-enhanced verdict
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LlmEvaluation:
    """LLM-enhanced assessment of a drive result."""
    outcome: str  # completed | in_progress | no_change | degraded
    confidence: float
    reason: str
    suggestion: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def evaluate_drive_result(
    evidence: Evidence,
    *,
    ticket_id: str = "",
    ticket_title: str = "",
    driven_prompt: str = "",
    heuristic_verdict: Verdict | None = None,
) -> LlmEvaluation | None:
    """Ask LLM to assess whether the drive accomplished the task.

    Returns ``None`` if the LLM is unavailable/over-budget (caller
    should fall back to heuristic verdict).
    """
    prompt_parts = [
        "Evaluate whether an IDE autopilot drive accomplished the task.",
        "",
        f"Ticket: {ticket_id or '(none)'}",
        f"Title: {ticket_title or '(none)'}",
        f"Driven prompt: {driven_prompt[:500]}" if driven_prompt else "",
        "",
        "Evidence collected after drive:",
        f"  Git files changed: {evidence.git.files_changed}",
        f"  Git insertions: {evidence.git.insertions}",
        f"  Git deletions: {evidence.git.deletions}",
        f"  Test status: {evidence.tests.status}",
        f"  Failing services: {', '.join(evidence.tests.failing_services) or 'none'}",
        f"  Chat events since drive: {evidence.chat.events_since_drive}",
        f"  Chat has message.sent: {evidence.chat.has_message_sent}",
        f"  Chat session ended: {evidence.chat.has_session_ended}",
    ]
    if heuristic_verdict:
        prompt_parts.extend([
            "",
            "Heuristic verdict (for reference):",
            f"  Outcome: {heuristic_verdict.outcome}",
            f"  Confidence: {heuristic_verdict.confidence}",
            f"  Reason: {heuristic_verdict.reason}",
        ])
    prompt_parts.extend([
        "",
        'Return JSON: {"outcome":"completed|in_progress|no_change|degraded",'
        '"confidence":0.0-1.0,"reason":"short explanation",'
        '"suggestion":"what to do next"}',
    ])

    resp = _call_openrouter(
        "\n".join(p for p in prompt_parts if p is not None),
        system_prompt=(
            "You are a code review assistant evaluating IDE autopilot drive results. "
            "Return only valid JSON with keys: outcome, confidence, reason, suggestion."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    outcome = str(data.get("outcome", "unknown"))
    if outcome not in {"completed", "in_progress", "no_change", "degraded"}:
        outcome = "unknown"

    return LlmEvaluation(
        outcome=outcome,
        confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        reason=str(data.get("reason", ""))[:500],
        suggestion=str(data.get("suggestion", ""))[:500],
        raw=data,
    )


# ---------------------------------------------------------------------------
# 2. generate_better_prompt — improved prompt after failed drives
# ---------------------------------------------------------------------------

def generate_better_prompt(
    *,
    ticket_id: str,
    ticket_title: str,
    original_prompt: str,
    drive_count: int,
    last_verdict_reason: str = "",
    evidence_summary: str = "",
) -> str | None:
    """Ask LLM to generate an improved prompt for a stuck ticket.

    Returns ``None`` if the LLM is unavailable (caller keeps original prompt).
    """
    prompt = "\n".join([
        "The following autopilot prompt has been driven to an IDE LLM multiple times "
        "but the task remains incomplete.",
        "",
        f"Ticket: {ticket_id}",
        f"Title: {ticket_title}",
        f"Drive attempts: {drive_count}",
        f"Last verdict: {last_verdict_reason}" if last_verdict_reason else "",
        f"Evidence: {evidence_summary[:300]}" if evidence_summary else "",
        "",
        "Original prompt:",
        original_prompt[:2000],
        "",
        "Generate an improved version of this prompt that:",
        "1. Is more specific about what needs to change",
        "2. Mentions files or functions if evident from the context",
        "3. Avoids repeating instructions the LLM already tried",
        "4. Stays concise (under 500 words)",
        "",
        'Return JSON: {"improved_prompt":"the new prompt text","changes":"what you changed and why"}',
    ])

    resp = _call_openrouter(
        prompt,
        system_prompt=(
            "You are a prompt engineering assistant. Generate an improved IDE autopilot prompt. "
            "Return only valid JSON with keys: improved_prompt, changes."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    improved = str(data.get("improved_prompt", "")).strip()
    return improved if improved else None


# ---------------------------------------------------------------------------
# 3. plan_next_action — advisory LLM-based action plan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LlmActionAdvice:
    """LLM's recommendation for the next cycle action."""
    action: str
    ticket_id: str | None = None
    reason: str = ""
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def plan_next_action(
    *,
    queue_status: str,
    waiting_tickets: list[str],
    stagnation_streak: int,
    test_status: str,
    last_verdict: dict[str, Any] | None = None,
    last_action_plan: dict[str, Any] | None = None,
) -> LlmActionAdvice | None:
    """Ask LLM what the autonomous loop should do next.

    This is advisory — the arbiter may override it with heuristic vetoes.
    Returns ``None`` if unavailable.
    """
    prompt_parts = [
        "You are the planning brain of an autonomous coding assistant (koru).",
        "Given the current project state, recommend the next action.",
        "",
        f"Queue status: {queue_status}",
        f"Waiting tickets: {', '.join(waiting_tickets) or 'none'}",
        f"Stagnation streak: {stagnation_streak}",
        f"Test status: {test_status}",
    ]
    if last_verdict:
        prompt_parts.append(f"Last drive verdict: {json.dumps(last_verdict)[:500]}")
    if last_action_plan:
        prompt_parts.append(f"Last action plan: {json.dumps(last_action_plan)[:500]}")
    prompt_parts.extend([
        "",
        "Possible actions: drive_ticket, redrive_improved, close_ticket, "
        "escalate_ticket, switch_ticket, run_discovery, wait, reflect, noop",
        "",
        'Return JSON: {"action":"one_of_above","ticket_id":"or null",'
        '"reason":"short","confidence":0.0-1.0}',
    ])

    resp = _call_openrouter(
        "\n".join(prompt_parts),
        system_prompt=(
            "You are an autonomous coding planner. Return only valid JSON "
            "with keys: action, ticket_id, reason, confidence."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    valid_actions = {
        "drive_ticket", "redrive_improved", "close_ticket", "escalate_ticket",
        "switch_ticket", "run_discovery", "wait", "reflect", "noop",
    }
    action = str(data.get("action", "noop"))
    if action not in valid_actions:
        action = "noop"

    return LlmActionAdvice(
        action=action,
        ticket_id=data.get("ticket_id"),
        reason=str(data.get("reason", ""))[:500],
        confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        raw=data,
    )


__all__ = [
    "BudgetTracker",
    "LlmActionAdvice",
    "LlmEvaluation",
    "LlmResponse",
    "evaluate_drive_result",
    "generate_better_prompt",
    "get_budget_tracker",
    "plan_next_action",
]
