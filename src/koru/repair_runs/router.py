"""The wired model-selection layer over :mod:`model_router`'s single authority.

One vocabulary, one classifier, one ``ModelSpec`` — all owned by
``model_router``. This module keeps the two pieces the queue wrapper actually
plugs in:

- ``load_model_registry`` — the koru.yaml roster (names are configuration);
- ``classify_invocation`` / ``choose_model`` — the invocation-level loop the
  recording session drives: classify the reply's transport surface, skip
  models whose ledger shows a sticky failure, hand back nothing but a name.

``model_router.route`` is the full decision table (non-model remedies:
reduce context, run probe, corrective iteration, remanifest, forbidden stop)
for the coming plan-level runner; this layer is deliberately the small subset
a single wrapped LLM call needs. Both read the same codes, so a failure never
means two things.
"""

from __future__ import annotations

from pathlib import Path

from koru.repair_runs.model_router import (
    CONTEXT_LENGTH_EXCEEDED,
    INVALID_STRUCTURED_OUTPUT,
    MODEL_DECLINED,
    NO_SWITCH_CODES,
    PROVIDER_ERROR,
    PROVIDER_POLICY_BLOCK,
    PROVIDER_TIMEOUT,
    PROVIDER_UNAVAILABLE,
    RUNTIME_POLICY_DENIED,
    STICKY_CODES,
    WORKER_DIED,
    ModelSpec,
    classify_failure,
)
from koru.repair_runs.models import ModelAttempt

__all__ = [
    "CONTEXT_LENGTH_EXCEEDED",
    "INVALID_STRUCTURED_OUTPUT",
    "MODEL_DECLINED",
    "NO_SWITCH_CODES",
    "PROVIDER_ERROR",
    "PROVIDER_POLICY_BLOCK",
    "PROVIDER_TIMEOUT",
    "PROVIDER_UNAVAILABLE",
    "RUNTIME_POLICY_DENIED",
    "STICKY_CODES",
    "WORKER_DIED",
    "ModelSpec",
    "choose_model",
    "classify_invocation",
    "load_model_registry",
]


def load_model_registry(project: Path) -> tuple[ModelSpec, ...]:
    """The project's model roster from koru.yaml; empty means no routing."""
    try:
        import yaml
    except ImportError:
        return ()
    try:
        config = yaml.safe_load((project / "koru.yaml").read_text(encoding="utf-8"))
        entries = ((config or {}).get("queue") or {}).get("repair_models") or []
    except (OSError, AttributeError, yaml.YAMLError):
        return ()
    specs = []
    for entry in entries:
        if not isinstance(entry, dict):
            continue
        model = str(entry.get("model") or "").strip()
        if not model:
            continue
        try:
            max_attempts = max(1, int(entry.get("max_attempts") or 1))
        except (TypeError, ValueError):
            max_attempts = 1
        specs.append(
            ModelSpec(
                id=str(entry.get("id") or model),
                model=model,
                provider=str(entry.get("provider") or "openrouter"),
                capabilities=tuple(str(c) for c in (entry.get("capabilities") or [])),
                max_attempts=max_attempts,
            ),
        )
    return tuple(specs)


def classify_invocation(result) -> str | None:
    """What kind of failure an invocation was; ``None`` means it answered.

    Delegates to the single classifier — transport status codes first, then
    the provider's own words; never the model's prose. A failure nothing
    explains is ``provider_error``: on this layer every failed invocation
    carries *some* code, because the attempt ledger requires one.
    """
    returncode = getattr(result, "returncode", 1)
    if returncode == 0:
        return None
    code = classify_failure(
        returncode,
        getattr(result, "stderr", "") or "",
        getattr(result, "stdout", "") or "",
        status_code=getattr(result, "status_code", None),
    )
    return code or PROVIDER_ERROR


def choose_model(
    registry: tuple[ModelSpec, ...],
    attempts: list[ModelAttempt],
    *,
    last_failure: str | None = None,
) -> ModelSpec | None:
    """The next model to ask, or ``None`` when the roster is exhausted.

    Models whose ledger shows a sticky failure are skipped for the rest of the
    run. After a context-length failure, candidates carrying ``long-context``
    are preferred (until the Context Broker learns to shrink the snapshot
    instead). Returning ``None`` is the *only* escalation — there is no
    "try anything once more" path.
    """
    burned = {
        attempt.model
        for attempt in attempts
        if attempt.failure_code in STICKY_CODES or attempt.status == "interrupted"
    }
    candidates = [spec for spec in registry if spec.model not in burned]
    if not candidates:
        return None
    if last_failure == CONTEXT_LENGTH_EXCEEDED:
        roomy = [c for c in candidates if "long-context" in c.capabilities]
        if roomy:
            return roomy[0]
    return candidates[0]
