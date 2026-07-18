"""Route a repair run's next model attempt from the last attempt's outcome.

The store (models/lifecycle/sqlite) records *what happened*; this decides *what
to try next* when a model attempt fails. Pure and deterministic: it reads the
failure and the model registry and returns a decision. It never calls a model,
never mutates the workspace, never touches the store — those belong to the
runner, so a routing decision cannot itself change anything.

The load-bearing rule, from the design: **a provider policy block is an
operational event, not a verdict.** When a model refuses, the run keeps its
ledger, its manifest, and its file scope; the router only picks a different
model to carry the same contract forward. Switching models never widens the
run's rights — the router deals in model ids, not permissions, so it is
structurally incapable of escalation.

Failure codes are named here so the free-string ``ModelAttempt.failure_code``
has one authority to compare against, rather than each caller inventing its own.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

# ── Canonical model-attempt failure codes ────────────────────────────────────
PROVIDER_POLICY_BLOCK = "provider_policy_block"
PROVIDER_TIMEOUT = "provider_timeout"
PROVIDER_UNAVAILABLE = "provider_unavailable"
INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"
CONTEXT_LENGTH_EXCEEDED = "context_length_exceeded"
MISSING_FACT = "missing_fact"
PATCH_INVALID = "patch_invalid"
VERIFICATION_FAILED = "verification_failed"
RUNTIME_POLICY_DENIED = "runtime_policy_denied"
WORKSPACE_DRIFT = "workspace_drift"
CAPABILITY_UNAVAILABLE = "capability_unavailable"

# ── Routing verbs the runner acts on ─────────────────────────────────────────
SWITCH_MODEL = "switch_model"  # this model cannot; a different one might
RETRY_SAME_MODEL = "retry_same_model"  # transient; give the same model one more go
REDUCE_CONTEXT = "reduce_context"  # ask the Context Broker to shrink the snapshot
RUN_PROBE = "run_probe"  # a required fact is missing; observe it
REGENERATE_PATCH = "regenerate_patch"  # the diff was malformed; ask again once
REPAIR_ITERATION = "repair_iteration"  # patch applied but failed verify; new iteration
DISCOVERY_PROBE = "discovery_probe"  # a capability is missing; discover, don't reroll
REMANIFEST_OR_STOP = "remanifest_or_stop"  # the base moved; re-pin or stop safely
FORBIDDEN_STOP = "forbidden_stop"  # runtime denied it; no model may proceed
MODEL_EXHAUSTED = "model_exhausted"  # every eligible model has been spent


# ── Failure classification: raw invocation result → a canonical code ─────────
# The queue recorder writes a coarse ``invoke_failed``; the router needs to know
# *why* to decide whether to switch models, shrink context, or stop. This maps
# the model's own error text onto a canonical code. Ordered most-specific first;
# unmatched failures stay unclassified so the router treats them conservatively.
_FAILURE_SIGNATURES: tuple[tuple[str, re.Pattern[str]], ...] = (
    (RUNTIME_POLICY_DENIED,
     re.compile(r"runtime[_ ]policy|not permitted|forbidden by policy|risk ceiling", re.I)),
    (PROVIDER_POLICY_BLOCK,
     re.compile(r"\b(policy|content[_ ]policy|refus|declined|blocked by|not allowed|safety)\b", re.I)),
    (CONTEXT_LENGTH_EXCEEDED,
     re.compile(r"context[_ ]length|maximum context|too many tokens|context window|413\b", re.I)),
    (PROVIDER_TIMEOUT,
     re.compile(r"\b(time[d]? ?out|timeout|deadline exceeded|etimedout)\b", re.I)),
    (PROVIDER_UNAVAILABLE,
     re.compile(r"\b(unavailable|503|502|econnrefused|econnreset|bad gateway|overloaded|rate ?limit|429)\b", re.I)),
    (INVALID_STRUCTURED_OUTPUT,
     re.compile(r"\b(invalid json|json ?decode|schema|malformed|unparse|not valid)\b", re.I)),
)


def classify_failure(returncode: int, stderr: str = "", stdout: str = "") -> str | None:
    """Turn a raw model-invocation result into a canonical failure code.

    Returns ``None`` on success (returncode 0) or when nothing matches — an
    unclassified failure, which the router handles conservatively as a model
    change. Deliberately matches on the provider's own words rather than status
    codes alone, since OpenRouter surfaces policy blocks and timeouts as text.
    """
    if returncode == 0:
        return None
    text = f"{stderr or ''}\n{stdout or ''}"
    for code, pattern in _FAILURE_SIGNATURES:
        if pattern.search(text):
            return code
    return None


@dataclass(frozen=True)
class ModelSpec:
    """One routable model. Names are configuration, never hardcoded logic."""

    id: str
    model: str
    provider: str
    capabilities: frozenset[str] = frozenset()
    max_attempts: int = 1


@dataclass(frozen=True)
class RoutingDecision:
    """What the runner should do next. ``next_model`` is set only for a model change."""

    verb: str
    reason: str
    next_model: ModelSpec | None = None
    retryable: bool = False
    escalate: bool = False

    def as_event(self) -> dict:
        """Shape for a ``model_attempt_routed`` ledger event."""
        return {
            "verb": self.verb,
            "reason": self.reason,
            "next_model_id": self.next_model.id if self.next_model else None,
            "retryable": self.retryable,
            "escalate": self.escalate,
        }


# A failure either reroutes to another model, or stays with a non-model remedy.
# Kept as data, not an if-chain, so the mapping is auditable in one place.
_MODEL_CHANGING: frozenset[str] = frozenset(
    {PROVIDER_POLICY_BLOCK, PROVIDER_UNAVAILABLE, INVALID_STRUCTURED_OUTPUT},
)
_TRANSIENT_THEN_SWITCH: frozenset[str] = frozenset({PROVIDER_TIMEOUT})
_NON_MODEL_REMEDY: dict[str, tuple[str, str, bool]] = {
    # code: (verb, reason, retryable)
    CONTEXT_LENGTH_EXCEEDED: (REDUCE_CONTEXT, "context too large; shrink the snapshot before retrying", True),
    MISSING_FACT: (RUN_PROBE, "a required fact is absent; run its probe, do not reroll the model", True),
    PATCH_INVALID: (REGENERATE_PATCH, "diff was malformed; ask the same model once with the git error", True),
    VERIFICATION_FAILED: (REPAIR_ITERATION, "patch applied but failed verify; open a corrective iteration", True),
    CAPABILITY_UNAVAILABLE: (DISCOVERY_PROBE, "a capability is missing; discover it, not a random model retry", True),
    WORKSPACE_DRIFT: (REMANIFEST_OR_STOP, "the base moved under the run; re-pin the manifest or stop safely", True),
    RUNTIME_POLICY_DENIED: (FORBIDDEN_STOP, "runtime denied the operation; no model may proceed", False),
}


def _attempts_for(model: ModelSpec, attempts: list) -> int:
    return sum(1 for a in attempts if getattr(a, "model", None) == model.model)


def _eligible(registry: list[ModelSpec], attempts: list) -> list[ModelSpec]:
    """Models that still have attempts left in their budget."""
    return [m for m in registry if _attempts_for(m, attempts) < max(1, m.max_attempts)]


def route(
    failure_code: str | None,
    *,
    registry: list[ModelSpec],
    attempts: list,
    last_model: ModelSpec | None = None,
) -> RoutingDecision:
    """Decide the next step after a failed model attempt.

    ``attempts`` is the run's ``ModelAttempt`` history (any objects exposing
    ``model``); ``registry`` is the configured, ordered model list. The order of
    ``registry`` is the tie-breaker, so routing is deterministic for a given
    history — no ranking heuristics here.
    """
    code = (failure_code or "").strip()

    # Non-model remedies: the model is not the problem, so do not spend another.
    if code in _NON_MODEL_REMEDY:
        verb, reason, retryable = _NON_MODEL_REMEDY[code]
        return RoutingDecision(
            verb=verb, reason=reason, retryable=retryable, escalate=(verb == FORBIDDEN_STOP),
        )

    # A timeout gets one more go on the same model before moving on.
    if code in _TRANSIENT_THEN_SWITCH and last_model is not None:
        if _attempts_for(last_model, attempts) < max(1, last_model.max_attempts):
            return RoutingDecision(
                verb=RETRY_SAME_MODEL,
                reason="transient timeout; retry the same model once before switching",
                next_model=last_model,
                retryable=True,
            )

    # Model-changing failures (and an exhausted timeout) look for a fresh model.
    if code in _MODEL_CHANGING or code in _TRANSIENT_THEN_SWITCH or not code:
        candidates = [m for m in _eligible(registry, attempts) if last_model is None or m.model != last_model.model]
        # If only the last model is left with budget, do not re-pick it here —
        # a policy block or bad output will just repeat.
        if candidates:
            return RoutingDecision(
                verb=SWITCH_MODEL,
                reason=f"{code or 'unknown failure'}: this model cannot proceed; trying the next configured model",
                next_model=candidates[0],
                retryable=True,
            )
        return RoutingDecision(
            verb=MODEL_EXHAUSTED,
            reason="every configured model has been tried without a usable result",
            escalate=True,
        )

    # Unknown code: treat conservatively as a model change, then exhaustion.
    candidates = [m for m in _eligible(registry, attempts) if last_model is None or m.model != last_model.model]
    if candidates:
        return RoutingDecision(
            verb=SWITCH_MODEL,
            reason=f"unrecognised failure {code!r}; trying the next model",
            next_model=candidates[0],
            retryable=True,
        )
    return RoutingDecision(
        verb=MODEL_EXHAUSTED, reason=f"unrecognised failure {code!r} and no models left", escalate=True,
    )
