"""Query objects for the autonomous-checkpoint bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadLoopCheckpointSnapshotQuery:
    path: Path


__all__ = ["LoadLoopCheckpointSnapshotQuery"]