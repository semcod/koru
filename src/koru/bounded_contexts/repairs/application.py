"""Application services for repair diagnostics and repair history."""

from __future__ import annotations

from koru.cqrs import CqrsService, EventLogEntry, EventLogQueryService

from .commands import RecordRepairAttemptCommand, RecordRepairDiagnosticCommand
from .events import (
    REPAIR_ATTEMPT_RECORDED,
    REPAIR_CONTEXT,
    REPAIR_DIAGNOSTIC_RECORDED,
    RepairAttemptRecorded,
    RepairDiagnosticRecorded,
)
from .queries import LoadRepairHistoryQuery


class RepairCommandService(CqrsService):
    """Handles state-changing repair audit operations."""

    def record_diagnostic(self, command: RecordRepairDiagnosticCommand) -> None:
        event = RepairDiagnosticRecorded(
            subject=command.subject,
            repair_kind=command.repair_kind,
            project=command.project,
            summary=command.summary,
            status=command.status,
            hypotheses=command.hypotheses,
        )
        self.runtime.append_event(
            context=REPAIR_CONTEXT,
            event_type=REPAIR_DIAGNOSTIC_RECORDED,
            payload=event.to_payload(),
            aggregate_id=command.subject,
        )

    def record_attempt(self, command: RecordRepairAttemptCommand) -> None:
        event = RepairAttemptRecorded(
            subject=command.subject,
            repair_kind=command.repair_kind,
            project=command.project,
            attempted=command.attempted,
            ok=command.ok,
            actions=command.actions,
            summary=command.summary,
        )
        self.runtime.append_event(
            context=REPAIR_CONTEXT,
            event_type=REPAIR_ATTEMPT_RECORDED,
            payload=event.to_payload(),
            aggregate_id=command.subject,
        )


class RepairQueryService(CqrsService):
    """Handles read-only repair history queries."""

    def history(self, query: LoadRepairHistoryQuery) -> list[EventLogEntry]:
        return EventLogQueryService(self.runtime.store).recent(
            context=REPAIR_CONTEXT,
            aggregate_id=query.subject,
            limit=query.limit,
        )


__all__ = ["RepairCommandService", "RepairQueryService"]
