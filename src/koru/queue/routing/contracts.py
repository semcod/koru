"""Typed routing inputs; candidates are client/model/transport identities."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ToolClass(StrEnum):
    DETERMINISTIC = "deterministic"
    API = "api"
    CLI = "cli"
    IDE = "ide"


class TaskClass(StrEnum):
    SIMPLE = "simple"
    COMPLEX = "complex"
    OTHER = "other"


@dataclass(frozen=True)
class Task:
    difficulty: TaskClass
    kind: str
    reason: str

    @property
    def key(self) -> str:
        return f"{self.difficulty}:{self.kind}"


@dataclass(frozen=True)
class Candidate:
    id: str
    tool_class: ToolClass
    client: str
    transport: str
    fingerprint: str
    capabilities: frozenset[str]
    available: bool = True
    unavailable_reason: str = ""
    model: str = ""

    def supports(self, task: Task) -> bool:
        return task.key in self.capabilities


@dataclass(frozen=True)
class ProbeResult:
    status: str
    duration_ms: int
    validator_digest: str = ""
    tokens: int | None = None
    cost: float | None = None
    detail: str = ""


@dataclass(frozen=True)
class Decision:
    candidate: Candidate | None
    task: Task
    reason: str
    evidence_date: str | None = None
    samples: int = 0
    low_confidence: bool = True
    rejected: dict[str, str] = field(default_factory=dict)
