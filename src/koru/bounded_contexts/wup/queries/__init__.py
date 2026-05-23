"""Query objects for the WUP bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadWupHealthSnapshotQuery:
    project: Path


__all__ = ["LoadWupHealthSnapshotQuery"]