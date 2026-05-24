from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from koru.cqrs import EventSourcingRuntime
from koru.autonomous_wup import WupHealthResult
from koru.bounded_contexts.wup.application import WupCommandService, WupQueryService
from koru.bounded_contexts.wup.commands import EvaluateWupHealthCommand
from koru.bounded_contexts.wup.events import WUP_CONTEXT, WUP_HEALTH_FAILED
from koru.bounded_contexts.wup.events import WUP_HEALTH_INTERRUPTED
from koru.bounded_contexts.wup.queries import LoadWupHealthSnapshotQuery
from koru.bounded_contexts.wup.read_model import WupEventLogProjection


@dataclass
class _State:
    wup_seen_events: int = 0


def test_wup_command_evaluates_health_and_emits_event(monkeypatch, tmp_path: Path) -> None:
    def fake_read_wup_health_impl(**_kwargs) -> WupHealthResult:
        return WupHealthResult(
            status="failed",
            failing_services=["koru-core"],
            new_events=2,
        )

    monkeypatch.setattr(
        "koru.bounded_contexts.wup.application._read_wup_health_impl",
        fake_read_wup_health_impl,
    )

    runtime = EventSourcingRuntime()
    projection = WupEventLogProjection()
    runtime.bus.subscribe(projection.handle)
    command_service = WupCommandService(runtime)
    result = command_service.evaluate_health(
        EvaluateWupHealthCommand(
            project=tmp_path,
            state=_State(),
            diagnostic_tickets=True,
            ticket_queue="default",
            state_dir=tmp_path / ".planfile/.koru/autoloop-diag",
            create_diagnostic_ticket=lambda **_kwargs: None,
        ),
    )

    assert result.status == "failed"
    assert result.failing_services == ["koru-core"]
    assert result.new_events == 2

    events = command_service.runtime.store.all_events(context=WUP_CONTEXT)
    assert len(events) == 1
    assert events[0].event_type == WUP_HEALTH_FAILED
    assert events[0].payload["status"] == "failed"
    assert events[0].payload["failing_services"] == ["koru-core"]

    projected = projection.recent()
    assert len(projected) == 1
    assert projected[0].event_type == WUP_HEALTH_FAILED
    assert projected[0].payload["status"] == "failed"


def test_wup_query_loads_health_snapshot(tmp_path: Path) -> None:
    wup_dir = tmp_path / ".wup"
    wup_dir.mkdir(parents=True)
    health_payload = {
        "koru-core": {"status": "ok", "message": "all good"},
        "koru-shell": {"status": "failed", "message": "quick test failed"},
    }
    (wup_dir / "service-health.json").write_text(
        json.dumps(health_payload),
        encoding="utf-8",
    )

    query_service = WupQueryService()
    snapshot = query_service.health_snapshot(LoadWupHealthSnapshotQuery(project=tmp_path))

    assert snapshot == health_payload


def test_wup_command_emits_interrupted_event(monkeypatch, tmp_path: Path) -> None:
    def fake_read_wup_health_impl(**_kwargs) -> WupHealthResult:
        return WupHealthResult(
            status="interrupted",
            failing_services=[],
            new_events=1,
        )

    monkeypatch.setattr(
        "koru.bounded_contexts.wup.application._read_wup_health_impl",
        fake_read_wup_health_impl,
    )

    runtime = EventSourcingRuntime()
    command_service = WupCommandService(runtime)
    result = command_service.evaluate_health(
        EvaluateWupHealthCommand(
            project=tmp_path,
            state=_State(),
            diagnostic_tickets=False,
            ticket_queue="default",
            state_dir=tmp_path / ".planfile/.koru/autoloop-diag",
            create_diagnostic_ticket=None,
        ),
    )

    assert result.status == "interrupted"
    events = command_service.runtime.store.all_events(context=WUP_CONTEXT)
    assert len(events) == 1
    assert events[0].event_type == WUP_HEALTH_INTERRUPTED
    assert events[0].payload["status"] == "interrupted"