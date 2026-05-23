"""Query objects for the environment-config bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadEnvConfigQuery:
    project: Path
    environ: dict[str, str]


@dataclass(frozen=True)
class LoadEnvConfigHistoryQuery:
    project: Path | None = None
    limit: int | None = None


__all__ = ["LoadEnvConfigHistoryQuery", "LoadEnvConfigQuery"]