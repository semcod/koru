"""Policy for deciding when to ask an LLM to interpret chat state."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any


@dataclass(frozen=True)
class ReflectionPolicyDecision:
    should_reflect: bool
    reason: str
    event_types: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def decide_chat_reflection(
    *,
    enabled: bool,
    last_type: str,
    reflection_events: list[Any],
) -> ReflectionPolicyDecision:
    """Ask LLM only when local heuristics cannot safely interpret the chat."""
    event_types = tuple(str(getattr(ev, "type", "") or "") for ev in reflection_events)
    if not enabled:
        return ReflectionPolicyDecision(False, "disabled", event_types)
    if not reflection_events:
        return ReflectionPolicyDecision(False, "no_events", event_types)
    if "message.received" in event_types:
        return ReflectionPolicyDecision(True, "message_received_ambiguous", event_types)
    if str(last_type or "") == "message.received":
        return ReflectionPolicyDecision(True, "last_event_received_ambiguous", event_types)
    if "message.sent" in event_types:
        return ReflectionPolicyDecision(True, "sent_only_operator_reflection_enabled", event_types)
    return ReflectionPolicyDecision(False, "no_ambiguous_chat_events", event_types)


__all__ = ["ReflectionPolicyDecision", "decide_chat_reflection"]
