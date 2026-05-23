"""Query objects for the planfile queue bounded context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from koru.queue.runners import run_process
from koru.queue.types import CommandResult


@dataclass(frozen=True)
class LoadNextRunnableTicketQuery:
    project: Path
    planfile_runner: Callable[[list[str], Path], CommandResult] = run_process


@dataclass(frozen=True)
class LoadPlanfileQueueHistoryQuery:
    ticket_id: str | None = None
    limit: int | None = None


__all__ = ["LoadNextRunnableTicketQuery", "LoadPlanfileQueueHistoryQuery"]