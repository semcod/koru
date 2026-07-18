"""Model routing: a blocked provider is an operational event, not a verdict.

The router owns two decisions and nothing else: *what kind of failure was
that* (classification) and *who answers next* (selection). It reads the
attempt ledger and the registry; it never invokes a model, never mutates a
workspace, and — the rule that matters most — **switching models never widens
the run's rights**: every candidate works under the same contract, the same
file scope and the same risk ceiling, because the router hands out nothing
but a model name.

Model names are configuration, not code:

.. code-block:: yaml

    queue:
      repair_models:
        - id: primary
          model: anthropic/claude-sonnet
          capabilities: [code, reasoning]
        - id: fallback-policy
          model: openai/gpt
          capabilities: [code, strict-json]
        - id: fallback-context
          model: google/gemini
          capabilities: [long-context]
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from koru.repair_runs.models import ModelAttempt

# Invocation failure codes, per the plan's classification table.
PROVIDER_POLICY_BLOCK = "provider_policy_block"
PROVIDER_TIMEOUT = "provider_timeout"
INVALID_STRUCTURED_OUTPUT = "invalid_structured_output"
CONTEXT_LENGTH_EXCEEDED = "context_length_exceeded"
RUNTIME_POLICY_DENIED = "runtime_policy_denied"
PROVIDER_ERROR = "provider_error"
WORKER_DIED = "worker_died"

#: Failures that stick to the *model* across iterations: they describe the
#: provider relationship, not the patch, so retrying the same model with the
#: same request is spending an attempt on a known answer. A red verify, by
#: contrast, never marks the model.
STICKY_CODES = frozenset(
    {
        PROVIDER_POLICY_BLOCK,
        INVALID_STRUCTURED_OUTPUT,
        CONTEXT_LENGTH_EXCEEDED,
        WORKER_DIED,
    },
)

#: Failures where switching is pointless or forbidden.
NO_SWITCH_CODES = frozenset({RUNTIME_POLICY_DENIED})


@dataclass(frozen=True)
class ModelSpec:
    id: str
    model: str
    provider: str = "openrouter"
    capabilities: tuple[str, ...] = ()


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
        specs.append(
            ModelSpec(
                id=str(entry.get("id") or model),
                model=model,
                provider=str(entry.get("provider") or "openrouter"),
                capabilities=tuple(str(c) for c in (entry.get("capabilities") or [])),
            ),
        )
    return tuple(specs)


def classify_invocation(result) -> str | None:
    """What kind of failure an invocation was; ``None`` means it answered.

    Classification reads the transport surface (status code, stderr), never
    the model's prose — a model cannot talk its way into a different failure
    class any more than into wider permissions.
    """
    if getattr(result, "returncode", 1) == 0:
        return None
    status = getattr(result, "status_code", None)
    stderr = (getattr(result, "stderr", "") or "").lower()
    if status == 403 or "policy" in stderr and "denied" not in stderr:
        return PROVIDER_POLICY_BLOCK
    if status in {408, 504} or "timed out" in stderr or "timeout" in stderr:
        return PROVIDER_TIMEOUT
    if status == 413 or "context length" in stderr or "context_length" in stderr:
        return CONTEXT_LENGTH_EXCEEDED
    if "runtime_policy_denied" in stderr:
        return RUNTIME_POLICY_DENIED
    return PROVIDER_ERROR


def choose_model(
    registry: tuple[ModelSpec, ...],
    attempts: list[ModelAttempt],
    *,
    last_failure: str | None = None,
) -> ModelSpec | None:
    """The next model to ask, or ``None`` when the roster is exhausted.

    Models whose ledger shows a sticky failure are skipped for the rest of the
    run. After a context-length failure, candidates carrying ``long-context``
    are preferred (until the Context Broker exists to shrink the context
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
