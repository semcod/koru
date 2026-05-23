"""Command objects for the autonomous-checkpoint bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from koru.autonomy.state import AutoloopState


@dataclass(frozen=True)
class SaveLoopCheckpointCommand:
    path: Path
    cycle: int
    state: AutoloopState
    queue_status: str
    waiting_ticket: str


@dataclass(frozen=True)
class RestoreLoopCheckpointCommand:
    path: Path
    state: AutoloopState
    stdio_format: str = "human"


__all__ = ["RestoreLoopCheckpointCommand", "SaveLoopCheckpointCommand"]