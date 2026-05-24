"""Domain events for the WUP bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

WUP_CONTEXT = "wup"

WUP_HEALTH_OK = "wup.health_ok"
WUP_HEALTH_CHANGED = "wup.health_changed"
WUP_HEALTH_FAILED = "wup.health_failed"
WUP_HEALTH_INTERRUPTED = "wup.health_interrupted"


@dataclass(frozen=True)
class WupHealthEvaluated(DomainEvent):
    project: str
    status: str
    failing_services: list[str]
    new_events: int


__all__ = [
    "WUP_CONTEXT",
    "WUP_HEALTH_CHANGED",
    "WUP_HEALTH_FAILED",
    "WUP_HEALTH_INTERRUPTED",
    "WUP_HEALTH_OK",
    "WupHealthEvaluated",
]