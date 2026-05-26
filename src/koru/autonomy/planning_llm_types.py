from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class LlmEvaluation:
    """LLM-enhanced assessment of a drive result."""

    outcome: str
    confidence: float
    reason: str
    suggestion: str = ""
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


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


@dataclass(frozen=True)
class LlmReflection:
    """LLM interpretation of ambiguous IDE chat events."""

    done: bool
    needs_input: bool
    summary: str
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StrategyTuning:
    """LLM-proposed changes to autonomy.strategy in koru.yaml."""

    patch: str
    reason: str
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TicketPriority:
    """LLM-recommended ticket execution order."""

    ordered_ticket_ids: tuple[str, ...]
    reason: str
    confidence: float = 0.0
    raw: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "ordered_ticket_ids": list(self.ordered_ticket_ids)}
