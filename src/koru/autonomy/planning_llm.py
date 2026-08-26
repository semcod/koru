"""Planning LLM facade for autonomous planning and reflection."""

from __future__ import annotations

from pathlib import Path

from koru.autonomy.verification_engine import Evidence, Verdict
from korullm import run_subllm

from .planning_llm_budget import BudgetTracker, get_budget_tracker
from .planning_llm_parsing import (
    parse_action_advice,
    parse_evaluation,
    parse_improved_prompt,
    parse_reflection,
    parse_strategy_tuning,
    parse_ticket_priority,
)
from .planning_llm_prompts import (
    build_evaluate_drive_result_prompt,
    build_generate_better_prompt_prompt,
    build_plan_next_action_prompt,
    build_prioritize_tickets_prompt,
    build_propose_strategy_tuning_prompt,
    build_reflect_on_chat_prompt,
)
from .planning_llm_runtime import (
    LlmResponse,
    planning_llm_enabled,
    request_timeout,
)
from .planning_llm_types import (
    LlmActionAdvice,
    LlmEvaluation,
    LlmReflection,
    StrategyTuning,
    TicketPriority,
)

# Backward-compatible injection seam for older tests/extensions. The bound
# transport is selected by SubLLM policy; no provider is forced locally.
call_openrouter_json = run_subllm


def _call_planning_llm(
    prompt: str,
    *,
    system_prompt: str,
    response_json: bool = True,
) -> LlmResponse:
    """Call the strict provider-neutral SubLLM planning route."""
    del response_json
    if not planning_llm_enabled():
        return LlmResponse(ok=False, content="", error="planning LLM disabled")
    result = call_openrouter_json(
        prompt,
        Path.cwd(),
        route_function="planning-assistant",
        system_prompt=system_prompt,
        timeout_seconds=request_timeout(),
    )
    get_budget_tracker().record(0.0)
    if result.returncode != 0:
        return LlmResponse(
            ok=False,
            content="",
            error=result.stderr,
            model=result.model,
            usage=result.usage,
        )
    return LlmResponse(
        ok=True,
        content=result.stdout,
        model=result.model,
        usage=result.usage,
    )


def evaluate_drive_result(
    evidence: Evidence,
    *,
    ticket_id: str = "",
    ticket_title: str = "",
    driven_prompt: str = "",
    heuristic_verdict: Verdict | None = None,
) -> LlmEvaluation | None:
    resp = _call_planning_llm(
        build_evaluate_drive_result_prompt(
            evidence,
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            driven_prompt=driven_prompt,
            heuristic_verdict=heuristic_verdict,
        ),
        system_prompt=(
            "You are a code review assistant evaluating IDE autopilot drive results. "
            "Return only valid JSON with keys: outcome, confidence, reason, suggestion."
        ),
    )
    return parse_evaluation(resp.content) if resp.ok else None


def generate_better_prompt(
    *,
    ticket_id: str,
    ticket_title: str,
    original_prompt: str,
    drive_count: int,
    last_verdict_reason: str = "",
    evidence_summary: str = "",
) -> str | None:
    resp = _call_planning_llm(
        build_generate_better_prompt_prompt(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            original_prompt=original_prompt,
            drive_count=drive_count,
            last_verdict_reason=last_verdict_reason,
            evidence_summary=evidence_summary,
        ),
        system_prompt=(
            "You are a prompt engineering assistant. Generate an improved IDE autopilot prompt. "
            "Return only valid JSON with keys: improved_prompt, changes."
        ),
    )
    return parse_improved_prompt(resp.content) if resp.ok else None


def plan_next_action(
    *,
    queue_status: str,
    waiting_tickets: list[str],
    stagnation_streak: int,
    test_status: str,
    last_verdict: dict[str, object] | None = None,
    last_action_plan: dict[str, object] | None = None,
) -> LlmActionAdvice | None:
    resp = _call_planning_llm(
        build_plan_next_action_prompt(
            queue_status=queue_status,
            waiting_tickets=waiting_tickets,
            stagnation_streak=stagnation_streak,
            test_status=test_status,
            last_verdict=last_verdict,
            last_action_plan=last_action_plan,
        ),
        system_prompt=(
            "You are an autonomous coding planner. Return only valid JSON "
            "with keys: action, ticket_id, reason, confidence."
        ),
    )
    return parse_action_advice(resp.content) if resp.ok else None


def reflect_on_chat(
    *,
    ticket_id: str,
    ticket_title: str,
    driven_prompt: str,
    chat_events: list[dict[str, object]],
) -> LlmReflection | None:
    if not chat_events:
        return None
    resp = _call_planning_llm(
        build_reflect_on_chat_prompt(
            ticket_id=ticket_id,
            ticket_title=ticket_title,
            driven_prompt=driven_prompt,
            chat_events=chat_events,
        ),
        system_prompt=(
            "You are a reflection assistant. Return only valid JSON "
            "with keys: done, needs_input, summary."
        ),
    )
    return parse_reflection(resp.content) if resp.ok else None


def propose_strategy_tuning(
    *,
    current_strategy_yaml: str,
    recent_decisions: list[dict[str, object]],
    cycle_metrics: dict[str, object] | None = None,
) -> StrategyTuning | None:
    if not recent_decisions:
        return None
    resp = _call_planning_llm(
        build_propose_strategy_tuning_prompt(
            current_strategy_yaml=current_strategy_yaml,
            recent_decisions=recent_decisions,
            cycle_metrics=cycle_metrics,
        ),
        system_prompt=(
            "You are a strategy tuning assistant. Analyze telemetry and propose "
            "YAML patches for koru.yaml. Return only valid JSON with keys: "
            "patch, reason, confidence."
        ),
    )
    return parse_strategy_tuning(resp.content) if resp.ok else None


def prioritize_tickets(
    *,
    tickets: list[dict[str, object]],
    test_status: str = "unknown",
    recent_verdicts: list[dict[str, object]] | None = None,
) -> TicketPriority | None:
    if len(tickets) < 2:
        return None
    resp = _call_planning_llm(
        build_prioritize_tickets_prompt(
            tickets=tickets,
            test_status=test_status,
            recent_verdicts=recent_verdicts,
        ),
        system_prompt=(
            "You are a ticket prioritization assistant. Return only valid JSON "
            "with keys: ordered (list of ticket ids), reason, confidence."
        ),
    )
    return parse_ticket_priority(resp.content, tickets) if resp.ok else None


__all__ = [
    "BudgetTracker",
    "LlmActionAdvice",
    "LlmEvaluation",
    "LlmReflection",
    "LlmResponse",
    "StrategyTuning",
    "TicketPriority",
    "_call_planning_llm",
    "evaluate_drive_result",
    "generate_better_prompt",
    "get_budget_tracker",
    "plan_next_action",
    "prioritize_tickets",
    "propose_strategy_tuning",
    "reflect_on_chat",
]
