"""Application services for the planfile queue bounded context."""

from __future__ import annotations

from typing import Any

from koru.cqrs import CqrsService, EventLogEntry, EventLogQueryService
from koru.queue.runner import _run_next_planfile_task_impl
from koru.queue.ticket import parse_next_ticket, planfile_command
from koru.queue.types import QueueRunResult

from .commands import RunNextPlanfileTaskCommand
from .events import (
    PLANFILE_QUEUE_CONTEXT,
    PLANFILE_QUEUE_IDLE,
    PLANFILE_QUEUE_TASK_COMPLETED,
    PLANFILE_QUEUE_TASK_FAILED,
    PLANFILE_QUEUE_TASK_WAITING,
    PLANFILE_QUEUE_TICK_ERROR,
    PlanfileQueueIdle,
    PlanfileQueueTaskCompleted,
    PlanfileQueueTaskFailed,
    PlanfileQueueTaskWaiting,
    PlanfileQueueTickError,
)
from .queries import LoadNextRunnableTicketQuery, LoadPlanfileQueueHistoryQuery


def _event_for_result(result: QueueRunResult) -> tuple[str, dict[str, Any], str]:
    ticket_id = str(result.ticket_id or "-")
    if result.status == "completed":
        event = PlanfileQueueTaskCompleted(
            ticket_id=ticket_id,
            executor_kind=str(result.executor_kind or ""),
            message=result.message,
            exit_code=int(result.exit_code or 0),
        )
        return PLANFILE_QUEUE_TASK_COMPLETED, event.to_payload(), ticket_id
    if result.status in {"failed", "claim_failed"}:
        event = PlanfileQueueTaskFailed(
            ticket_id=ticket_id,
            executor_kind=str(result.executor_kind or ""),
            message=result.message,
            exit_code=int(result.exit_code or 0),
            stderr=result.stderr,
        )
        return PLANFILE_QUEUE_TASK_FAILED, event.to_payload(), ticket_id
    if result.status in {"waiting_input", "dry_run", "unsupported_executor"}:
        event = PlanfileQueueTaskWaiting(
            ticket_id=ticket_id,
            executor_kind=str(result.executor_kind or ""),
            status=result.status,
            message=result.message,
        )
        return PLANFILE_QUEUE_TASK_WAITING, event.to_payload(), ticket_id
    if result.status == "idle":
        event = PlanfileQueueIdle(message=result.message)
        return PLANFILE_QUEUE_IDLE, event.to_payload(), PLANFILE_QUEUE_CONTEXT
    event = PlanfileQueueTickError(
        status=result.status,
        ticket_id=ticket_id,
        message=result.message,
        exit_code=int(result.exit_code or 0),
        stderr=result.stderr,
    )
    return PLANFILE_QUEUE_TICK_ERROR, event.to_payload(), ticket_id


class PlanfileQueueCommandService(CqrsService):
    """Handles state-changing queue operations."""

    def run_next_task(self, command: RunNextPlanfileTaskCommand) -> QueueRunResult:
        result = _run_next_planfile_task_impl(
            project=command.project,
            actor=command.actor,
            dry_run=command.dry_run,
            queue_name=command.queue_name,
            interactive=command.interactive,
            planfile_runner=command.planfile_runner,
            shell_runner=command.shell_runner,
            api_runner=command.api_runner,
            llm_runner=command.llm_runner,
            prompt_runner=command.prompt_runner,
        )
        event_type, payload, aggregate_id = _event_for_result(result)
        self.runtime.append_event(
            context=PLANFILE_QUEUE_CONTEXT,
            event_type=event_type,
            payload=payload,
            aggregate_id=aggregate_id,
        )
        return result


class PlanfileQueueQueryService(CqrsService):
    """Handles read-only queue queries."""

    def load_next_runnable_ticket(
        self,
        query: LoadNextRunnableTicketQuery,
    ) -> dict[str, Any] | None:
        result = planfile_command(
            query.project,
            ["ticket", "list", "--status", "open", "--format", "json"],
            runner=query.planfile_runner,
        )
        if result.returncode != 0:
            return None
        ticket = parse_next_ticket(result.stdout)
        return dict(ticket) if isinstance(ticket, dict) else None

    def history(self, query: LoadPlanfileQueueHistoryQuery) -> list[EventLogEntry]:
        return EventLogQueryService(self.runtime.store).recent(
            context=PLANFILE_QUEUE_CONTEXT,
            aggregate_id=query.ticket_id,
            limit=query.limit,
        )


__all__ = ["PlanfileQueueCommandService", "PlanfileQueueQueryService"]