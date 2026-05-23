from __future__ import annotations

from pathlib import Path

from koru.cqrs import EventSourcingRuntime, runtime_for_project
from koru.bounded_contexts.topology.application import TopologyCommandService, TopologyQueryService
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
)
from koru.bounded_contexts.topology.read_model import TopologyEventLogProjection
from koru.bounded_contexts.topology.queries import LoadTopologyQuery
from koru.cqrs.event_store import JsonlEventStore


def test_topology_commands_emit_events_and_persist(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = TopologyEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = TopologyCommandService(runtime)
    query_service = TopologyQueryService()

    topology = query_service.load(LoadTopologyQuery(project=tmp_path))

    component_result = command_service.toggle_component(
        ToggleComponentCommand(
            project=tmp_path,
            topology=topology,
            component_id="redsl",
            enabled=True,
        ),
    )
    pipeline_result = command_service.toggle_pipeline(
        TogglePipelineCommand(
            project=tmp_path,
            topology=topology,
            pipeline_id="gate:wup",
            enabled=False,
        ),
    )
    saved_path = command_service.persist(
        PersistTopologyCommand(project=tmp_path, topology=topology),
    )

    assert component_result.found is True
    assert pipeline_result.found is True
    assert saved_path.is_file()

    events = command_service.runtime.store.all_events(context=TOPOLOGY_CONTEXT)
    assert [event.event_type for event in events] == [
        TOPOLOGY_COMPONENT_TOGGLED,
        TOPOLOGY_PIPELINE_TOGGLED,
        TOPOLOGY_SAVED,
    ]
    assert events[0].aggregate_id == "redsl"
    assert events[1].aggregate_id == "gate:wup"

    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [
        TOPOLOGY_COMPONENT_TOGGLED,
        TOPOLOGY_PIPELINE_TOGGLED,
        TOPOLOGY_SAVED,
    ]
    assert projected[0].aggregate_id == "redsl"


def test_topology_projection_replays_persisted_event_log(tmp_path: Path) -> None:
    runtime = runtime_for_project(tmp_path)
    command_service = TopologyCommandService(runtime)
    query_service = TopologyQueryService()

    topology = query_service.load(LoadTopologyQuery(project=tmp_path))
    command_service.toggle_component(
        ToggleComponentCommand(
            project=tmp_path,
            topology=topology,
            component_id="redsl",
            enabled=True,
        ),
    )
    command_service.persist(PersistTopologyCommand(project=tmp_path, topology=topology))

    projection = TopologyEventLogProjection()
    projection.replay(JsonlEventStore(tmp_path / ".koru" / "event-store.jsonl"))

    assert [entry.event_type for entry in projection.recent()] == [
        TOPOLOGY_COMPONENT_TOGGLED,
        TOPOLOGY_SAVED,
    ]
    assert [entry.aggregate_id for entry in projection.recent(aggregate_id="redsl")] == ["redsl"]
