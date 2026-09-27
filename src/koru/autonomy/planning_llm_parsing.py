from __future__ import annotations

import json
from typing import Any

from .planning_llm_types import (
    LlmActionAdvice,
    LlmEvaluation,
    LlmReflection,
    StrategyTuning,
    TicketPriority,
)


def parse_json_object(content: str) -> dict[str, Any] | None:
    try:
        decoded = json.loads(content)
    except json.JSONDecodeError:
        return None
    return decoded if isinstance(decoded, dict) else None


def parse_evaluation(content: str) -> LlmEvaluation | None:
    evaluation = parse_json_object(content)
    if evaluation is None:
        return None
    outcome = str(evaluation.get("outcome", "unknown"))
    if outcome not in {"completed", "in_progress", "no_change", "degraded"}:
        outcome = "unknown"
    return LlmEvaluation(
        outcome=outcome,
        confidence=max(0.0, min(1.0, float(evaluation.get("confidence", 0.5)))),
        reason=str(evaluation.get("reason", ""))[:500],
        suggestion=str(evaluation.get("suggestion", ""))[:500],
        raw=evaluation,
    )


def parse_improved_prompt(content: str) -> str | None:
    prompt_payload = parse_json_object(content)
    if prompt_payload is None:
        return None
    improved = str(prompt_payload.get("improved_prompt", "")).strip()
    return improved if improved else None


def parse_action_advice(content: str) -> LlmActionAdvice | None:
    advice = parse_json_object(content)
    if advice is None:
        return None
    valid_actions = {
        "drive_ticket", "redrive_improved", "close_ticket", "escalate_ticket",
        "switch_ticket", "run_discovery", "wait", "reflect", "noop",
    }
    action = str(advice.get("action", "noop"))
    if action not in valid_actions:
        action = "noop"
    return LlmActionAdvice(
        action=action,
        ticket_id=advice.get("ticket_id"),
        reason=str(advice.get("reason", ""))[:500],
        confidence=max(0.0, min(1.0, float(advice.get("confidence", 0.5)))),
        raw=advice,
    )


def parse_reflection(content: str) -> LlmReflection | None:
    reflection = parse_json_object(content)
    if reflection is None:
        return None
    return LlmReflection(
        done=bool(reflection.get("done", False)),
        needs_input=bool(reflection.get("needs_input", False)),
        summary=str(reflection.get("summary", ""))[:500],
        raw=reflection,
    )


def parse_strategy_tuning(content: str) -> StrategyTuning | None:
    tuning = parse_json_object(content)
    if tuning is None:
        return None
    patch = str(tuning.get("patch", "")).strip()
    reason = str(tuning.get("reason", "")).strip()
    if not patch and not reason:
        return None
    return StrategyTuning(
        patch=patch[:3000],
        reason=reason[:500],
        confidence=max(0.0, min(1.0, float(tuning.get("confidence", 0.5)))),
        raw=tuning,
    )


def parse_ticket_priority(content: str, tickets: list[dict[str, Any]]) -> TicketPriority | None:
    priority_payload = parse_json_object(content)
    if priority_payload is None:
        return None
    ordered = priority_payload.get("ordered")
    if not isinstance(ordered, list):
        return None
    valid_ids = {str(t.get("id", "")) for t in tickets}
    clean = tuple(str(tid) for tid in ordered if str(tid) in valid_ids)
    if not clean:
        return None
    return TicketPriority(
        ordered_ticket_ids=clean,
        reason=str(priority_payload.get("reason", ""))[:500],
        confidence=max(0.0, min(1.0, float(priority_payload.get("confidence", 0.5)))),
        raw=priority_payload,
    )
