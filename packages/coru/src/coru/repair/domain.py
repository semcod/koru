"""Domain types for coru bridge repair (shared by commands, events, queries)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Mapping

RepairSeverity = Literal["error", "warning", "info"]
RepairMode = Literal["auto", "replay", "manual"]


@dataclass(frozen=True)
class RepairProblem:
    code: str
    severity: RepairSeverity
    message: str
    fix_hint: str | None = None
    context: Mapping[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RepairStepDef:
    """Maps issue codes to a repair command (registry entry for new bugfixes)."""

    issue_codes: frozenset[str]
    action_id: str
    mode: RepairMode
    priority: int
    description: str
    llm_playbook: str = ""


@dataclass
class RepairAttempt:
    action_id: str
    mode: RepairMode
    ok: bool
    message: str
    automated: bool = True
    duration_ms: float | None = None


@dataclass
class RepairPlan:
    session_id: str
    problems: tuple[RepairProblem, ...]
    attempts: tuple[RepairAttempt, ...] = ()
    resolved: bool = False
    trigger: str = "unknown"


@dataclass(frozen=True)
class RepairCaseSummary:
    """Read-model row: one repair session projected for LLM/human history."""

    session_id: str
    occurred_at: str
    ide: str
    instance: str
    trigger: str
    problem_codes: tuple[str, ...]
    action_ids: tuple[str, ...]
    resolved: bool
    playbook: str
