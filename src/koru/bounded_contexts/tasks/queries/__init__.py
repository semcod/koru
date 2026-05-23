"""Query objects for the tasks bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadTaskConfigQuery:
    path: Path
    project_name: str


@dataclass(frozen=True)
class LoadTaskSprintQuery:
    path: Path
    sprint: str = "current"


@dataclass(frozen=True)
class LoadTaskHistoryQuery:
    ticket_id: str | None = None
    limit: int | None = None


__all__ = ["LoadTaskConfigQuery", "LoadTaskHistoryQuery", "LoadTaskSprintQuery"]