from __future__ import annotations

from pathlib import Path

from koru.autonomous_checkpoint import load_loop_checkpoint, save_loop_checkpoint
from koru.autonomy.state import AutoloopState
from koru.bounded_contexts.autonomous_checkpoint.application import (
    AutonomousCheckpointCommandService,
    AutonomousCheckpointQueryService,
)
from koru.bounded_contexts.autonomous_checkpoint.commands import (
    RestoreLoopCheckpointCommand,
    SaveLoopCheckpointCommand,
)
from koru.bounded_contexts.autonomous_checkpoint.events import (
    AUTONOMOUS_CHECKPOINT_CONTEXT,
    LOOP_CHECKPOINT_RESTORED,
    LOOP_CHECKPOINT_SAVED,
)
from koru.bounded_contexts.autonomous_checkpoint.queries import (
    LoadCheckpointHistoryQuery,
    LoadLoopCheckpointSnapshotQuery,
)
from koru.bounded_contexts.autonomous_checkpoint.read_model import (
    AutonomousCheckpointEventLogProjection,
)
from koru.cqrs import EventSourcingRuntime, runtime_for_storage_dir
from koru.cqrs.event_store import JsonlEventStore


def test_autonomous_checkpoint_commands_emit_domain_events(tmp_path: Path) -> None:
    runtime = EventSourcingRuntime()
    projection = AutonomousCheckpointEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = AutonomousCheckpointCommandService(runtime)
    query_service = AutonomousCheckpointQueryService()

    path = tmp_path / ".koru" / "checkpoint.json"
    state = AutoloopState(previous_signature="abc", stagnation_streak=2)
    state.autopilot_events = [{"kind": "message.received"}, "ignored", {"kind": "message.sent"}]
    command_service.save(
        SaveLoopCheckpointCommand(
            path=path,
            cycle=7,
            state=state,
            queue_status="waiting",
            waiting_ticket="T-123",
        ),
    )

    snapshot = query_service.load_snapshot(LoadLoopCheckpointSnapshotQuery(path=path))
    restored = AutoloopState()
    cycle = command_service.restore(
        RestoreLoopCheckpointCommand(path=path, state=restored, stdio_format="jsonl"),
    )

    assert snapshot is not None
    assert snapshot["cycle"] == 7
    assert snapshot["queue_status"] == "waiting"
    assert cycle == 7
    assert restored.previous_signature == "abc"
    assert restored.stagnation_streak == 2
    assert restored.autopilot_events == [
        {"kind": "message.received"},
        {"kind": "message.sent"},
    ]

    events = runtime.store.all_events(context=AUTONOMOUS_CHECKPOINT_CONTEXT)
    assert [event.event_type for event in events] == [
        LOOP_CHECKPOINT_SAVED,
        LOOP_CHECKPOINT_RESTORED,
    ]

    projected = projection.recent()
    assert [entry.event_type for entry in projected] == [
        LOOP_CHECKPOINT_SAVED,
        LOOP_CHECKPOINT_RESTORED,
    ]
    assert projected[0].aggregate_id == str(path)


def test_public_checkpoint_helpers_round_trip_state(tmp_path: Path) -> None:
    path = tmp_path / ".koru" / "checkpoint.json"
    saved = AutoloopState(
        previous_signature="sig-1",
        scan_clean_streak=3,
        last_scan_create_failed_fingerprint="1:deadbeef",
        last_scan_create_failed_ts=123.0,
        last_scan_duplicate_fingerprint="14:cafebabe",
        last_scan_duplicate_ts=456.0,
    )

    save_loop_checkpoint(
        path,
        cycle=4,
        state=saved,
        queue_status="idle",
        waiting_ticket="-",
    )

    restored = AutoloopState()
    cycle = load_loop_checkpoint(path, state=restored, stdio_format="jsonl")

    assert cycle == 4
    assert restored.previous_signature == "sig-1"
    assert restored.scan_clean_streak == 3
    assert restored.last_scan_create_failed_fingerprint == "1:deadbeef"
    assert restored.last_scan_create_failed_ts == 123.0
    assert restored.last_scan_duplicate_fingerprint == "14:cafebabe"
    assert restored.last_scan_duplicate_ts == 456.0

    events = JsonlEventStore(path.parent / "event-store.jsonl").all_events(
        context=AUTONOMOUS_CHECKPOINT_CONTEXT
    )
    assert [event.event_type for event in events] == [
        LOOP_CHECKPOINT_SAVED,
        LOOP_CHECKPOINT_RESTORED,
    ]


def test_checkpoint_history_query_reads_persisted_events(tmp_path: Path) -> None:
    path = tmp_path / ".koru" / "checkpoint.json"
    runtime = runtime_for_storage_dir(path.parent)
    command_service = AutonomousCheckpointCommandService(runtime)
    query_service = AutonomousCheckpointQueryService(runtime)

    state = AutoloopState(previous_signature="sig-2")
    command_service.save(
        SaveLoopCheckpointCommand(
            path=path,
            cycle=2,
            state=state,
            queue_status="idle",
            waiting_ticket="-",
        ),
    )
    command_service.restore(
        RestoreLoopCheckpointCommand(path=path, state=AutoloopState(), stdio_format="jsonl"),
    )

    history = query_service.history(LoadCheckpointHistoryQuery(path=path, limit=10))

    assert [entry.event_type for entry in history] == [
        LOOP_CHECKPOINT_SAVED,
        LOOP_CHECKPOINT_RESTORED,
    ]
    assert all(entry.aggregate_id == str(path) for entry in history)
