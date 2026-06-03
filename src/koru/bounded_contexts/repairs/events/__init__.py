"""Domain events for repair diagnostics and repair attempts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from koru.cqrs import DomainEvent

REPAIR_CONTEXT = "repairs"

REPAIR_DIAGNOSTIC_RECORDED = "repairs.diagnostic.recorded"
REPAIR_ATTEMPT_RECORDED = "repairs.attempt.recorded"


@dataclass(frozen=True)
class RepairDiagnosticRecorded(DomainEvent):
    subject: str
    repair_kind: str
    project: str
    summary: str
    status: dict[str, Any]
    hypotheses: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RepairAttemptRecorded(DomainEvent):
    subject: str
    repair_kind: str
    project: str
    attempted: bool
    ok: bool
    actions: list[str] = field(default_factory=list)
    summary: str = ""


__all__ = [
    "REPAIR_ATTEMPT_RECORDED",
    "REPAIR_CONTEXT",
    "REPAIR_DIAGNOSTIC_RECORDED",
    "RepairAttemptRecorded",
    "RepairDiagnosticRecorded",
]
