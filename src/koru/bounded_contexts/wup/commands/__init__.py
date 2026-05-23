"""Command objects for the WUP bounded context."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class EvaluateWupHealthCommand:
    project: Path
    state: Any
    diagnostic_tickets: bool
    ticket_queue: str
    state_dir: Path
    create_diagnostic_ticket: Callable[..., None] | None = None


__all__ = ["EvaluateWupHealthCommand"]