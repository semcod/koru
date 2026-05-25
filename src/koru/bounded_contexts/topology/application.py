"""Application services for the topology bounded context."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru.bounded_contexts.topology.commands import (
    PersistTopologyCommand,
    ToggleComponentCommand,
    TogglePipelineCommand,
)
from koru.bounded_contexts.topology.events import (
    TOPOLOGY_COMPONENT_TOGGLED,
    TOPOLOGY_CONTEXT,
    TOPOLOGY_PIPELINE_TOGGLED,
    TOPOLOGY_SAVED,
    TopologyComponentToggled,
    TopologyPipelineToggled,
    TopologySaved,
)
from koru.bounded_contexts.topology.queries import (
    EnabledComponentsForPipelineQuery,
    IsEnabledQuery,
    LoadTopologyQuery,
)
from koru.cqrs import CqrsService
from koru.topology import (
    ToggleResult,
    enabled_components_for_pipeline,
    load_topology,
    save_topology,
    set_component_enabled,
    set_pipeline_enabled,
)


class TopologyCommandService(CqrsService):
    """Handles state-changing topology operations."""

    def toggle_component(self, command: ToggleComponentCommand) -> ToggleResult:
        result = set_component_enabled(
            command.topology,
            command.component_id,
            command.enabled,
        )
        if result.found:
            event = TopologyComponentToggled(
                project=str(command.project.resolve()),
                component_id=result.id,
                previous=bool(result.previous),
                current=result.current,
            )
            self.runtime.append_event(
                context=TOPOLOGY_CONTEXT,
                event_type=TOPOLOGY_COMPONENT_TOGGLED,
                payload=event.to_payload(),
                aggregate_id=result.id,
            )
        return result

    def toggle_pipeline(self, command: TogglePipelineCommand) -> ToggleResult:
        result = set_pipeline_enabled(
            command.topology,
            command.pipeline_id,
            command.enabled,
        )
        if result.found:
            event = TopologyPipelineToggled(
                project=str(command.project.resolve()),
                pipeline_id=result.id,
                previous=bool(result.previous),
                current=result.current,
            )
            self.runtime.append_event(
                context=TOPOLOGY_CONTEXT,
                event_type=TOPOLOGY_PIPELINE_TOGGLED,
                payload=event.to_payload(),
                aggregate_id=result.id,
            )
        return result

    def persist(self, command: PersistTopologyCommand) -> Path:
        path = save_topology(command.project, command.topology)
        event = TopologySaved(project=str(command.project.resolve()), path=str(path))
        self.runtime.append_event(
            context=TOPOLOGY_CONTEXT,
            event_type=TOPOLOGY_SAVED,
            payload=event.to_payload(),
            aggregate_id=str(command.project.resolve()),
        )
        return path


class TopologyQueryService:
    """Handles read-only topology queries."""

    def load(self, query: LoadTopologyQuery) -> dict[str, Any]:
        return load_topology(query.project)

    def is_enabled(self, query: IsEnabledQuery) -> bool | None:
        topo = load_topology(query.project)
        target = query.target_id
        comp = (topo.get("components") or {}).get(target)
        if isinstance(comp, dict):
            return bool(comp.get("enabled", True))
        pipe = (topo.get("pipelines") or {}).get(target)
        if isinstance(pipe, dict):
            return bool(pipe.get("enabled", True))
        return None

    def enabled_components_for_pipeline(
        self,
        query: EnabledComponentsForPipelineQuery,
    ) -> list[str]:
        return enabled_components_for_pipeline(query.project, query.pipeline_id)


__all__ = ["TopologyCommandService", "TopologyQueryService"]
