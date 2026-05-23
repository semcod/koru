"""Domain events for the topology bounded context."""

from __future__ import annotations

from dataclasses import dataclass

from koru.cqrs import DomainEvent

TOPOLOGY_CONTEXT = "topology"

TOPOLOGY_COMPONENT_TOGGLED = "topology.component_toggled"
TOPOLOGY_PIPELINE_TOGGLED = "topology.pipeline_toggled"
TOPOLOGY_SAVED = "topology.saved"


@dataclass(frozen=True)
class TopologyComponentToggled(DomainEvent):
    project: str
    component_id: str
    previous: bool
    current: bool


@dataclass(frozen=True)
class TopologyPipelineToggled(DomainEvent):
    project: str
    pipeline_id: str
    previous: bool
    current: bool


@dataclass(frozen=True)
class TopologySaved(DomainEvent):
    project: str
    path: str


__all__ = [
    "TOPOLOGY_COMPONENT_TOGGLED",
    "TOPOLOGY_CONTEXT",
    "TOPOLOGY_PIPELINE_TOGGLED",
    "TOPOLOGY_SAVED",
    "TopologyComponentToggled",
    "TopologyPipelineToggled",
    "TopologySaved",
]
