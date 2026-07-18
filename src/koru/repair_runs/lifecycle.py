"""The one legal shape of a repair run's life.

Two design rules encoded here, both from the autonomy plan:

- ``model_blocked`` is an *operational* event, not a verdict — a provider
  refusing a request says nothing about the repair, so the run routes to the
  next model instead of dying. Only ``model_exhausted`` (every configured
  model refused) escalates, and it escalates to ``safe_blocked``, never to
  "do whatever closes the ticket".
- The terminal states are exactly ``completed``, ``failed`` and
  ``safe_blocked``. Everything else is resumable, which is what makes the
  store a recovery mechanism rather than a log.
"""

from __future__ import annotations

# Happy path.
CREATED = "created"
CONTEXT_REQUIRED = "context_required"
CONTEXT_READY = "context_ready"
MODEL_RUNNING = "model_running"
ACTION_PROPOSED = "action_proposed"
ACTION_VALIDATED = "action_validated"
STAGING = "staging"
VERIFYING = "verifying"
PROMOTED = "promoted"
COMPLETED = "completed"

# Alternate states.
MODEL_BLOCKED = "model_blocked"
MODEL_EXHAUSTED = "model_exhausted"
PROBE_REQUIRED = "probe_required"
PATCH_REJECTED = "patch_rejected"
VERIFICATION_FAILED = "verification_failed"
WORKSPACE_DRIFT = "workspace_drift"
ROLLBACK_STARTED = "rollback_started"
ROLLED_BACK = "rolled_back"
SAFE_BLOCKED = "safe_blocked"
FAILED = "failed"

TERMINAL_STATES = frozenset({COMPLETED, FAILED, SAFE_BLOCKED})

#: Every state a restarted worker may pick a run up from.
RESUMABLE_STATES = frozenset(
    {
        CREATED,
        CONTEXT_REQUIRED,
        CONTEXT_READY,
        MODEL_RUNNING,
        ACTION_PROPOSED,
        ACTION_VALIDATED,
        STAGING,
        VERIFYING,
        PROMOTED,
        MODEL_BLOCKED,
        MODEL_EXHAUSTED,
        PROBE_REQUIRED,
        PATCH_REJECTED,
        VERIFICATION_FAILED,
        WORKSPACE_DRIFT,
        ROLLBACK_STARTED,
        ROLLED_BACK,
    },
)


class RepairLifecycleViolation(Exception):
    """A status was requested that cannot follow the run's current status."""


TRANSITIONS: dict[str, frozenset[str]] = {
    CREATED: frozenset({CONTEXT_REQUIRED, CONTEXT_READY, FAILED}),
    CONTEXT_REQUIRED: frozenset({CONTEXT_READY, PROBE_REQUIRED, SAFE_BLOCKED, FAILED}),
    PROBE_REQUIRED: frozenset({CONTEXT_REQUIRED, CONTEXT_READY, SAFE_BLOCKED, FAILED}),
    CONTEXT_READY: frozenset({MODEL_RUNNING, SAFE_BLOCKED, FAILED}),
    # A provider block routes to the next model; it never fails the run.
    MODEL_RUNNING: frozenset(
        {ACTION_PROPOSED, MODEL_BLOCKED, MODEL_EXHAUSTED, FAILED},
    ),
    MODEL_BLOCKED: frozenset({MODEL_RUNNING, MODEL_EXHAUSTED}),
    MODEL_EXHAUSTED: frozenset({SAFE_BLOCKED}),
    ACTION_PROPOSED: frozenset({ACTION_VALIDATED, PATCH_REJECTED, FAILED}),
    # ``action_validated → context_required`` is request_fact: the model asked
    # for evidence instead of guessing, and the loop goes round again.
    ACTION_VALIDATED: frozenset({STAGING, CONTEXT_REQUIRED, COMPLETED, SAFE_BLOCKED}),
    PATCH_REJECTED: frozenset({MODEL_RUNNING, SAFE_BLOCKED, FAILED}),
    STAGING: frozenset({VERIFYING, PATCH_REJECTED, WORKSPACE_DRIFT, ROLLBACK_STARTED, FAILED}),
    VERIFYING: frozenset({PROMOTED, VERIFICATION_FAILED, WORKSPACE_DRIFT, FAILED}),
    # A failed verify opens a fresh repair iteration, with fresh context.
    VERIFICATION_FAILED: frozenset({CONTEXT_REQUIRED, SAFE_BLOCKED, FAILED}),
    WORKSPACE_DRIFT: frozenset({CONTEXT_REQUIRED, SAFE_BLOCKED}),
    PROMOTED: frozenset({COMPLETED, FAILED}),
    ROLLBACK_STARTED: frozenset({ROLLED_BACK, FAILED}),
    ROLLED_BACK: frozenset({CONTEXT_REQUIRED, SAFE_BLOCKED, FAILED}),
    COMPLETED: frozenset(),
    FAILED: frozenset(),
    SAFE_BLOCKED: frozenset(),
}


def is_valid_transition(current: str, requested: str) -> bool:
    return requested in TRANSITIONS.get(current, frozenset())


def validate_transition(current: str, requested: str) -> None:
    if not is_valid_transition(current, requested):
        raise RepairLifecycleViolation(
            f"repair run cannot move from `{current}` to `{requested}`",
        )
