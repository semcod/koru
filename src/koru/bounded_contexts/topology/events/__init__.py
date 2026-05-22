"""Domain events for the topology bounded context."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

TOPOLOGY_CONTEXT = "topology"

TOPOLOGY_COMPONENT_TOGGLED = "topology.component_toggled"
TOPOLOGY_PIPELINE_TOGGLED = "topology.pipeline_toggled"
TOPOLOGY_SAVED = "topology.saved"


@dataclass(frozen=True)
class TopologyComponentToggled:
    project: str
    component_id: str
    previous: bool
    current: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "component_id": self.component_id,
            "previous": self.previous,
            "current": self.current,
        }


@dataclass(frozen=True)
class TopologyPipelineToggled:
    project: str
    pipeline_id: str
    previous: bool
    current: bool

    def to_payload(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "pipeline_id": self.pipeline_id,
            "previous": self.previous,
            "current": self.current,
        }


@dataclass(frozen=True)
class TopologySaved:
    project: str
    path: str

    def to_payload(self) -> dict[str, Any]:
        return {
            "project": self.project,
            "path": self.path,
        }


__all__ = [
    "TOPOLOGY_COMPONENT_TOGGLED",
    "TOPOLOGY_CONTEXT",
    "TOPOLOGY_PIPELINE_TOGGLED",
    "TOPOLOGY_SAVED",
    "TopologyComponentToggled",
    "TopologyPipelineToggled",
    "TopologySaved",
]
