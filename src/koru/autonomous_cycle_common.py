from dataclasses import dataclass

from koru.queue import QueueLoopResult


@dataclass(frozen=True)
class DiagnosticResult:
    status: str
    failed: list[str]


def _queue_loop_waiting_ticket_label(queue_result: QueueLoopResult) -> str:
    waiting = getattr(queue_result, "waiting", None) or []
    return waiting[-1] if waiting else "-"


def _status_in_skip_list(status: str, skip_statuses: str) -> bool:
    return status.lower() in {
        item.strip().lower() for item in skip_statuses.split(",") if item.strip()
    }
