"""Application services for the WUP bounded context."""

from __future__ import annotations

from typing import Any

from koru.autonomous_wup import WupHealthResult, _load_wup_health
from koru.autonomous_wup import _read_wup_health as _read_wup_health_impl
from koru.cqrs import CqrsService

from .commands import EvaluateWupHealthCommand
from .events import (
    WUP_CONTEXT,
    WUP_HEALTH_CHANGED,
    WUP_HEALTH_FAILED,
    WUP_HEALTH_INTERRUPTED,
    WUP_HEALTH_OK,
    WupHealthEvaluated,
)
from .queries import LoadWupHealthSnapshotQuery


def _wup_health_event_type(status: str) -> str:
    normalized = status.strip().lower()
    if normalized == "failed":
        return WUP_HEALTH_FAILED
    if normalized == "interrupted":
        return WUP_HEALTH_INTERRUPTED
    if normalized == "changed":
        return WUP_HEALTH_CHANGED
    return WUP_HEALTH_OK


class WupCommandService(CqrsService):
    """Handles state-changing WUP operations."""

    def evaluate_health(self, command: EvaluateWupHealthCommand) -> WupHealthResult:
        result = _read_wup_health_impl(
            project=command.project,
            state=command.state,
            diagnostic_tickets=command.diagnostic_tickets,
            ticket_queue=command.ticket_queue,
            state_dir=command.state_dir,
            create_diagnostic_ticket=command.create_diagnostic_ticket,
        )
        event = WupHealthEvaluated(
            project=str(command.project.resolve()),
            status=result.status,
            failing_services=list(result.failing_services),
            new_events=result.new_events,
        )
        self.runtime.append_event(
            context=WUP_CONTEXT,
            event_type=_wup_health_event_type(result.status),
            payload=event.to_payload(),
            aggregate_id=str(command.project.resolve()),
        )
        return result


class WupQueryService:
    """Handles read-only WUP queries."""

    def health_snapshot(self, query: LoadWupHealthSnapshotQuery) -> dict[str, dict[str, Any]]:
        return _load_wup_health(query.project / ".wup" / "service-health.json")


__all__ = ["WupCommandService", "WupQueryService"]