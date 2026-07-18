"""The facts a patch transaction is decided on, and what it decided.

``PatchPlan`` is resolved once, before anything is mutated, and every later
phase reads from it rather than re-deriving. That is what makes the phases
independently testable: give a phase a plan and it needs nothing else to run.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from koru.queue.patch_mode import PatchOutcome
from koru.queue.types import CommandResult


@dataclass(frozen=True)
class PatchPlan:
    """Everything the transaction resolved before touching the workspace.

    ``isolated`` is not a preference but a conclusion: verification can only be
    staged when there is a command to verify *with* and worktrees are enabled.
    """

    project: Path
    ticket: dict
    diff: str
    targets: tuple[str, ...]
    verify_command: str
    mode: str
    run_id: str
    isolated: bool

    @property
    def ticket_id(self) -> str:
        return str(self.ticket.get("id") or "ticket")


@dataclass(frozen=True)
class PatchTransactionResult:
    """The agent's reply, plus why the patch was refused — or ``None`` if it landed."""

    result: CommandResult
    outcome: PatchOutcome | None

    def as_tuple(self) -> tuple[CommandResult, PatchOutcome | None]:
        """Adapt to the ``(result, outcome)`` pair callers have always taken."""
        return self.result, self.outcome
