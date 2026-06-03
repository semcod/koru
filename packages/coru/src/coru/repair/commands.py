"""CQRS write-side commands for repair sessions."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from typing import Any

from coru.repair.domain import RepairProblem


@dataclass(frozen=True)
class RunRepairSessionCommand:
    """Execute diagnostics-driven repair and append events."""

    ide: str
    instance: str
    problems: tuple[RepairProblem, ...]
    trigger: str = "manual"
    session_id: str = field(default_factory=lambda: uuid.uuid4().hex)


@dataclass(frozen=True)
class RecordDiagnosisCommand:
    ide: str
    instance: str
    problems: tuple[RepairProblem, ...]
    trigger: str = "diagnose"
    snapshot: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ExecuteRepairActionCommand:
    session_id: str
    ide: str
    instance: str
    action_id: str
    problem_codes: frozenset[str]
