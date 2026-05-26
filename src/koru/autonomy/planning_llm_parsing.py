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
        data = json.loads(content)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def parse_evaluation(content: str) -> LlmEvaluation | None:
    data = parse_json_object(content)
    if data is None:
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


def parse_improved_prompt(content: str) -> str | None:
    data = parse_json_object(content)
    if data is None:
        return None
    improved = str(data.get("improved_prompt", "")).strip()
    return improved if improved else None


def parse_action_advice(content: str) -> LlmActionAdvice | None:
    data = parse_json_object(content)
    if data is None:
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


def parse_reflection(content: str) -> LlmReflection | None:
    data = parse_json_object(content)
    if data is None:
        return None
    return LlmReflection(
        done=bool(data.get("done", False)),
        needs_input=bool(data.get("needs_input", False)),
        summary=str(data.get("summary", ""))[:500],
        raw=data,
    )


def parse_strategy_tuning(content: str) -> StrategyTuning | None:
    data = parse_json_object(content)
    if data is None:
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


def parse_ticket_priority(content: str, tickets: list[dict[str, Any]]) -> TicketPriority | None:
    data = parse_json_object(content)
    if data is None:
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
