"""Data classes and protocols for the planfile queue system."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol


class CommandResult(Protocol):
    """Protocol for subprocess-like command results."""

    returncode: int
    stdout: str
    stderr: str


@dataclass(frozen=True)
class QueueRunResult:
    """Result of a single queue tick."""

    status: str
    ticket_id: str | None = None
    executor_kind: str | None = None
    message: str = ""
    exit_code: int | None = None
    stdout: str = ""
    stderr: str = ""


@dataclass(frozen=True)
class QueueLoopResult:
    """Aggregate result of draining the planfile queue with run_planfile_queue_loop."""

    iterations: int
    completed: list[str]
    failed: list[str]
    waiting: list[str]
    last_status: str
    last_message: str = ""
    last_ticket_id: str | None = None

    @property
    def ticket_id(self) -> str | None:
        """Backward-compatible alias for the final iteration's ticket id."""
        return self.last_ticket_id

    def summary(self) -> str:
        lines = [
            f"iterations={self.iterations}",
            f"completed={len(self.completed)}",
            f"failed={len(self.failed)}",
            f"waiting={len(self.waiting)}",
            f"last_status={self.last_status}",
        ]
        waiting_ticket = self.waiting[-1] if self.waiting else "none"
        lines.append(f"waiting_ticket={waiting_ticket}")
        return " ".join(lines)


@dataclass(frozen=True)
class ApiRunResult:
    """Result of a direct HTTP API executor call."""

    returncode: int
    stdout: str
    stderr: str
    status_code: int
    headers: dict[str, str]


@dataclass(frozen=True)
class LlmRunResult:
    """Result of an OpenRouter (or compatible) chat-completion call.

    ``stdout`` carries the assistant's text content (extracted from
    ``choices[0].message.content``) so the rest of the queue runner can
    treat it like any other executor's stdout. ``model`` and ``usage``
    expose model/token info for cost tracking and ``raw`` carries the
    full JSON response in case downstream tooling wants it.
    """

    returncode: int
    stdout: str
    stderr: str
    status_code: int
    model: str
    usage: dict[str, int]
    raw: dict[str, Any]
