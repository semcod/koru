"""Command objects for the environment-config bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class WriteEnvConfigCommand:
    project: Path
    updates: dict[str, str]


@dataclass(frozen=True)
class ApplyEnvUpdatesCommand:
    project: Path
    updates: dict[str, str]
    environ: dict[str, str]


__all__ = ["ApplyEnvUpdatesCommand", "WriteEnvConfigCommand"]