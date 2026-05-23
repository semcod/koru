"""Command objects for the tasks bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class CreateNlTaskCommand:
    project: Path
    text: str
    sprint: str = "current"
    queue_name: str | None = None
    priority: str = "normal"
    scaffold: dict[str, Any] | None = None


__all__ = ["CreateNlTaskCommand"]