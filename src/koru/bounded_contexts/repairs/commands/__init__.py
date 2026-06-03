"""Commands for repair diagnostics and repair attempts."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class RecordRepairDiagnosticCommand:
    subject: str
    repair_kind: str
    project: str
    summary: str
    status: dict[str, Any]
    hypotheses: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class RecordRepairAttemptCommand:
    subject: str
    repair_kind: str
    project: str
    attempted: bool
    ok: bool
    actions: list[str] = field(default_factory=list)
    summary: str = ""


__all__ = [
    "RecordRepairAttemptCommand",
    "RecordRepairDiagnosticCommand",
]
