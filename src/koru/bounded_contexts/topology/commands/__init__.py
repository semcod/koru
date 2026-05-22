"""Command objects for the topology bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class ToggleComponentCommand:
    project: Path
    topology: dict[str, Any]
    component_id: str
    enabled: bool


@dataclass(frozen=True)
class TogglePipelineCommand:
    project: Path
    topology: dict[str, Any]
    pipeline_id: str
    enabled: bool


@dataclass(frozen=True)
class PersistTopologyCommand:
    project: Path
    topology: dict[str, Any]


__all__ = [
    "PersistTopologyCommand",
    "ToggleComponentCommand",
    "TogglePipelineCommand",
]
