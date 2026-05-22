"""Query objects for the topology bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class LoadTopologyQuery:
    project: Path


@dataclass(frozen=True)
class IsEnabledQuery:
    project: Path
    target_id: str


@dataclass(frozen=True)
class EnabledComponentsForPipelineQuery:
    project: Path
    pipeline_id: str


__all__ = [
    "EnabledComponentsForPipelineQuery",
    "IsEnabledQuery",
    "LoadTopologyQuery",
]
