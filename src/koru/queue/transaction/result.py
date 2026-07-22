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
    #: Which rung of the verify precedence ladder produced the command —
    #: "profile", "allowlist", "legacy" or "none". Evidence wants the why.
    verify_source: str = "legacy"
    #: Set when the ticket asked for a gate that cannot be honoured (unknown
    #: profile, un-allowlisted raw command). The transaction must refuse.
    verify_error: str | None = None
    #: Verified hash bindings of the ProposalEnvelope this diff arrived in
    #: (input/prompt-schema/artifact/proposal hashes + intent pack); ``None``
    #: for the legacy bare-diff contract. Carried into the evidence bundle so
    #: the hash ladder starts at the proposal, not at the manifest.
    proposal: dict | None = None

    @property
    def ticket_id(self) -> str:
        return str(self.ticket.get("id") or "ticket")


@dataclass(frozen=True)
class StagingResult:
    """What the worktree phase concluded — and whether it ran at all.

    ``isolated=False`` means no worktree could be created, which is not the same
    as a patch that passed. Collapsing the two into a bare ``None`` is what let
    an ungated patch reach the workspace on a read-only checkout.
    """

    isolated: bool
    outcome: PatchOutcome | None = None

    @classmethod
    def unavailable(cls) -> StagingResult:
        """No worktree could be created; the caller must find another way."""
        return cls(isolated=False)

    @classmethod
    def verified(cls) -> StagingResult:
        """The patch applied and passed its gate in isolation."""
        return cls(isolated=True)

    @classmethod
    def refused(cls, outcome: PatchOutcome) -> StagingResult:
        """The patch was judged in isolation and rejected."""
        return cls(isolated=True, outcome=outcome)


@dataclass(frozen=True)
class PatchTransactionResult:
    """The agent's reply, plus why the patch was refused — or ``None`` if it landed.

    ``plan`` and ``manifest`` are carried for the evidence layer: they are
    ``None`` exactly when the transaction refused before resolving a plan or
    freezing one, which is itself evidence — nothing was going to change.
    """

    result: CommandResult
    outcome: PatchOutcome | None
    plan: PatchPlan | None = None
    manifest: dict | None = None

    @property
    def ok(self) -> bool:
        """The patch landed and passed its gate."""
        return self.outcome is None

    @property
    def code(self) -> str | None:
        """Stable structural failure code, or ``None`` when the patch landed.

        External consumers (bridge, ticket notes) branch on this — never on
        the wording of ``outcome.message``.
        """
        return self.outcome.code if self.outcome else None

    def as_tuple(self) -> tuple[CommandResult, PatchOutcome | None]:
        """Adapt to the ``(result, outcome)`` pair callers have always taken."""
        return self.result, self.outcome
