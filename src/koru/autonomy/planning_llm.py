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



# ---------------------------------------------------------------------------
# 4. reflect_on_chat — OpenRouter-native chat reflection (Phase 4)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class LlmReflection:
    """LLM interpretation of ambiguous IDE chat events."""
    done: bool
    needs_input: bool
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def reflect_on_chat(
    *,
    ticket_id: str,
    ticket_title: str,
    driven_prompt: str,
    chat_events: list[dict[str, Any]],
) -> LlmReflection | None:
    """Interpret ambiguous IDE chat events via OpenRouter.

    This is the OpenRouter-native replacement for ``llm_reflect.py``'s
    ``llx``-subprocess approach.  Returns ``None`` if LLM unavailable.
    """
    if not chat_events:
        return None

    event_lines = []
    for ev in chat_events[-20:]:
        etype = str(ev.get("type", ""))
        text = str(ev.get("text", "") or ev.get("summary", ""))[:200]
        event_lines.append(f"  [{etype}] {text}")

    prompt = "\n".join([
        "You are a reflection assistant for the koru autonomous loop.",
        "The loop just drove the prompt below into the IDE chat.",
        "Based ONLY on the recent IDE chat events, decide:",
        "  - done = true: IDE produced a final answer or completed the task",
        "  - needs_input = true: IDE is asking a question and is blocked",
        "  - otherwise (still working): both false",
        "",
        f"Ticket: {ticket_id or '-'} — {ticket_title or '-'}",
        f"Driven prompt: {driven_prompt[:500]}",
        "",
        "Recent IDE chat events (newest last):",
        *event_lines,
        "",
        'Return JSON: {"done":bool,"needs_input":bool,"summary":"1 sentence"}',
    ])

    resp = _call_openrouter(
        prompt,
        system_prompt=(
            "You are a reflection assistant. Return only valid JSON "
            "with keys: done, needs_input, summary."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    return LlmReflection(
        done=bool(data.get("done", False)),
        needs_input=bool(data.get("needs_input", False)),
        summary=str(data.get("summary", ""))[:500],
        raw=data,
    )


# ---------------------------------------------------------------------------
# 5. propose_strategy_tuning — analyze telemetry and suggest koru.yaml patch
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class StrategyTuning:
    """LLM-proposed changes to autonomy.strategy in koru.yaml."""
    patch: str  # YAML or unified diff
    reason: str
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def propose_strategy_tuning(
    *,
    current_strategy_yaml: str,
    recent_decisions: list[dict[str, Any]],
    cycle_metrics: dict[str, Any] | None = None,
) -> StrategyTuning | None:
    """Ask LLM to analyze recent decision history and propose strategy improvements.

    Returns ``None`` if LLM unavailable or no meaningful suggestion.
    """
    if not recent_decisions:
        return None

    decisions_summary = json.dumps(recent_decisions[-10:], indent=1)[:2000]

    prompt_parts = [
        "You are helping tune Koru autonomy strategy based on telemetry.",
        "",
        "Current autonomy.strategy (koru.yaml):",
        "```yaml",
        current_strategy_yaml[:1500],
        "```",
        "",
        f"Recent decision history ({len(recent_decisions)} decisions, last 10 shown):",
        "```json",
        decisions_summary,
        "```",
    ]
    if cycle_metrics:
        prompt_parts.extend([
            "",
            f"Latest cycle metrics: {json.dumps(cycle_metrics)[:500]}",
        ])
    prompt_parts.extend([
        "",
        "Analyze patterns:",
        "- Are there too many stagnation/escalation events?",
        "- Should cooldown or idle_streak thresholds change?",
        "- Is the pipeline order optimal?",
        "- Any signals being ignored that should be added?",
        "",
        'Return JSON: {"patch":"yaml or diff","reason":"explanation","confidence":0.0-1.0}',
        'Set patch to empty string if no changes recommended.',
    ])

    resp = _call_openrouter(
        "\n".join(prompt_parts),
        system_prompt=(
            "You are a strategy tuning assistant. Analyze telemetry and propose "
            "YAML patches for koru.yaml. Return only valid JSON with keys: "
            "patch, reason, confidence."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    patch = str(data.get("patch", "")).strip()
    reason = str(data.get("reason", "")).strip()
    if not patch and not reason:
        return None

    return StrategyTuning(
        patch=patch[:3000],
        reason=reason[:500],
        confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        raw=data,
    )


# ---------------------------------------------------------------------------
# 6. prioritize_tickets — multi-ticket planning (LLM sees backlog)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class TicketPriority:
    """LLM-recommended ticket execution order."""
    ordered_ticket_ids: tuple[str, ...]
    reason: str
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "ordered_ticket_ids": list(self.ordered_ticket_ids)}


def prioritize_tickets(
    *,
    tickets: list[dict[str, Any]],
    test_status: str = "unknown",
    recent_verdicts: list[dict[str, Any]] | None = None,
) -> TicketPriority | None:
    """Ask LLM to order the ticket backlog by priority.

    Each ticket dict should have at least ``id`` and ``title`` keys.
    Returns ``None`` if LLM unavailable or too few tickets.
    """
    if len(tickets) < 2:
        return None

    ticket_lines = []
    for t in tickets[:20]:
        tid = str(t.get("id", "?"))
        title = str(t.get("title", ""))[:100]
        status = str(t.get("status", ""))
        ticket_lines.append(f"  {tid}: {title} [{status}]")

    prompt_parts = [
        "You are prioritizing work tickets for an autonomous coding assistant.",
        "",
        f"Test status: {test_status}",
        "",
        "Available tickets:",
        *ticket_lines,
    ]
    if recent_verdicts:
        prompt_parts.extend([
            "",
            f"Recent drive verdicts: {json.dumps(recent_verdicts[-5:])[:500]}",
        ])
    prompt_parts.extend([
        "",
        "Order tickets by execution priority. Consider:",
        "- Tickets related to failing tests should come first",
        "- Small, focused tickets before large refactors",
        "- Tickets with recent failed drives might need different approach",
        "",
        'Return JSON: {"ordered":["ticket-id-1","ticket-id-2",...],'
        '"reason":"short explanation","confidence":0.0-1.0}',
    ])

    resp = _call_openrouter(
        "\n".join(prompt_parts),
        system_prompt=(
            "You are a ticket prioritization assistant. Return only valid JSON "
            "with keys: ordered (list of ticket ids), reason, confidence."
        ),
    )
    if not resp.ok:
        return None

    try:
        data = json.loads(resp.content)
    except json.JSONDecodeError:
        return None

    ordered = data.get("ordered")
    if not isinstance(ordered, list):
        return None

    valid_ids = {str(t.get("id", "")) for t in tickets}
    clean = tuple(str(tid) for tid in ordered if str(tid) in valid_ids)
    if not clean:
        return None

    return TicketPriority(
        ordered_ticket_ids=clean,
        reason=str(data.get("reason", ""))[:500],
        confidence=max(0.0, min(1.0, float(data.get("confidence", 0.5)))),
        raw=data,
    )


__all__ = [
    "BudgetTracker",
    "LlmActionAdvice",
    "LlmEvaluation",
    "LlmReflection",
    "LlmResponse",
    "StrategyTuning",
    "TicketPriority",
    "evaluate_drive_result",
    "generate_better_prompt",
    "get_budget_tracker",
    "plan_next_action",
    "prioritize_tickets",
    "propose_strategy_tuning",
    "reflect_on_chat",
]
