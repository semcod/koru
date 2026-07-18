"""The one legal shape of a patch run's life, as a transition graph.

Every journal append is checked against this graph, so an impossible history —
``promoted`` before anything was staged, ``completed`` out of nowhere — is
rejected at write time instead of being discovered by an auditor. The graph is
the union of what the transaction, the retry loop and crash recovery actually
do; anything outside it is a bug announcing itself.
"""

from __future__ import annotations

from koru.queue.journal import (
    PHASE_APPLIED,
    PHASE_APPLYING,
    PHASE_AUTHORIZED,
    PHASE_COMPLETED,
    PHASE_FROZEN,
    PHASE_PROMOTED,
    PHASE_PROMOTING,
    PHASE_REFUSED,
    PHASE_RESOLVED,
    PHASE_ROLLED_BACK,
    PHASE_STAGED,
    PHASE_STAGING,
    PHASE_STAGING_UNAVAILABLE,
    PHASE_VERIFIED,
)


class LifecycleViolation(Exception):
    """A phase was journaled that cannot follow the run's current phase."""


#: prev phase → the phases that may legally follow it. ``None`` is the start.
TRANSITIONS: dict[str | None, frozenset[str]] = {
    None: frozenset({PHASE_RESOLVED}),
    PHASE_RESOLVED: frozenset({PHASE_REFUSED, PHASE_FROZEN}),
    # ``frozen → refused`` exists for recovery closing a run that died right
    # after the freeze; ``frozen → completed`` is artifact delivery. The direct
    # ``frozen → staging/applying`` arcs remain legal for runs without an
    # authorizer — authorization narrows, its absence must not forge history.
    PHASE_FROZEN: frozenset(
        {PHASE_AUTHORIZED, PHASE_STAGING, PHASE_APPLYING, PHASE_COMPLETED, PHASE_REFUSED},
    ),
    PHASE_AUTHORIZED: frozenset({PHASE_STAGING, PHASE_APPLYING, PHASE_REFUSED}),
    # ``staging → promoted`` is recovery finishing a run whose branch commit
    # exists but whose bookkeeping died with the process.
    PHASE_STAGING: frozenset(
        {PHASE_STAGED, PHASE_STAGING_UNAVAILABLE, PHASE_REFUSED, PHASE_PROMOTED},
    ),
    PHASE_STAGED: frozenset({PHASE_PROMOTED, PHASE_REFUSED, PHASE_APPLYING}),
    PHASE_STAGING_UNAVAILABLE: frozenset({PHASE_REFUSED, PHASE_APPLYING}),
    PHASE_APPLYING: frozenset({PHASE_APPLIED, PHASE_REFUSED}),
    PHASE_APPLIED: frozenset(
        {PHASE_VERIFIED, PHASE_ROLLED_BACK, PHASE_PROMOTING, PHASE_COMPLETED},
    ),
    PHASE_VERIFIED: frozenset({PHASE_PROMOTING, PHASE_COMPLETED}),
    PHASE_PROMOTING: frozenset({PHASE_PROMOTED, PHASE_ROLLED_BACK}),
    PHASE_PROMOTED: frozenset({PHASE_COMPLETED}),
    # A refusal ends an attempt, not necessarily the run: the retry loop may
    # open a fresh attempt in the same journal.
    PHASE_REFUSED: frozenset({PHASE_RESOLVED}),
    PHASE_ROLLED_BACK: frozenset({PHASE_RESOLVED}),
    PHASE_COMPLETED: frozenset(),
}


def is_valid_transition(prev: str | None, phase: str) -> bool:
    return phase in TRANSITIONS.get(prev, frozenset())


def validate_transition(prev: str | None, phase: str) -> None:
    """Refuse an impossible history at write time."""
    if not is_valid_transition(prev, phase):
        raise LifecycleViolation(
            f"phase `{phase}` cannot follow `{prev or '(start)'}` — "
            "an impossible history must fail loudly, not be archived",
        )
