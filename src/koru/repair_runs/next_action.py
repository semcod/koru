"""Typed model output: the koru.repair.next-action/v1 contract.

A model does not return prose; it returns one action from a closed set, and
the set is the whole of its authority. There is no member for running a shell
command, committing, changing policy, touching the registry, widening file
scope or skipping verify — so the model cannot *ask* for any of those, let
alone receive them. The only payload that can change anything is ``patch``,
and it flows into the existing patch transaction with every contract, grant
and verify gate intact.

Unknown keys in the payload are dropped at the parser boundary and copied
nowhere: a model that smuggles ``"command": "rm -rf"`` into its JSON has
written a string into a void. A reply that does not parse against the schema
is ``invalid_structured_output`` — a *routing* fact (the router treats it as
sticky for the model), never an excuse to fall back to prose parsing.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

NEXT_ACTION_SCHEMA = "koru.repair.next-action/v1"

ACTION_PROPOSE_PATCH = "propose_patch"
ACTION_REQUEST_FACT = "request_fact"
ACTION_RUN_PROBE = "run_probe"
ACTION_RETRY_WITH_MODEL = "retry_with_model"
ACTION_DECLARE_NO_PATCH = "declare_no_patch"
ACTION_FINISH = "finish"

ALLOWED_ACTIONS = frozenset(
    {
        ACTION_PROPOSE_PATCH,
        ACTION_REQUEST_FACT,
        ACTION_RUN_PROBE,
        ACTION_RETRY_WITH_MODEL,
        ACTION_DECLARE_NO_PATCH,
        ACTION_FINISH,
    },
)

#: Appended to the prompt when structured output is on. The contract the model
#: answers under — stated once, at the boundary, in the model's language.
NEXT_ACTION_PROMPT_SUFFIX = f"""

## Output contract (structured)

Reply with a single JSON object and nothing else — no prose before or after:

{{
  "schema": "{NEXT_ACTION_SCHEMA}",
  "action": "propose_patch" | "request_fact" | "run_probe" | "retry_with_model" | "declare_no_patch" | "finish",
  "reason_code": "<short_snake_case_reason>",
  "required_facts": [{{"schema": "<fact-schema>", "key": "<key>"}}],
  "patch": "<unified diff — required for propose_patch, forbidden otherwise>",
  "confidence": 0.0
}}

Rules: `action` must be one of the six listed values. `propose_patch` requires
`patch` to be a unified diff. `request_fact` and `run_probe` require a
non-empty `required_facts`. You cannot request shell commands, commits,
policy or scope changes — there is no action for them.
"""


@dataclass(frozen=True)
class NextAction:
    """One validated instruction from the model. The type is the permission."""

    action: str
    reason_code: str = ""
    required_facts: tuple[dict, ...] = ()
    patch: str | None = None
    confidence: float = 0.0


@dataclass(frozen=True)
class NextActionError:
    """Why a reply failed the contract. Feeds router classification directly."""

    failure_code: str  # always invalid_structured_output today
    detail: str
    raw_excerpt: str = ""


_FENCE = re.compile(r"```(?:json)?\s*(\{.*?\})\s*```", re.DOTALL)


def parse_next_action(text: str) -> NextAction | NextActionError:
    """Validate a model reply against the contract; refuse everything else.

    Fenced JSON is unwrapped (models fence despite instructions); everything
    beyond that one courtesy is strict. Small validators, one concern each —
    the first refusal wins.
    """
    payload = _extract_payload(text)
    if isinstance(payload, NextActionError):
        return payload
    refusal = (
        _validate_schema(payload)
        or _validate_action(payload)
        or _validate_facts(payload)
        or _validate_patch(payload)
    )
    if refusal is not None:
        return _refuse(refusal, text)
    facts = payload.get("required_facts") or []
    action = payload["action"]
    return NextAction(
        action=action,
        reason_code=str(payload.get("reason_code") or ""),
        required_facts=tuple(
            {"schema": str(f["schema"]), "key": str(f["key"])} for f in facts
        ),
        patch=payload.get("patch") if action == ACTION_PROPOSE_PATCH else None,
        confidence=_clamped_confidence(payload),
    )


def _refuse(detail: str, text: str) -> NextActionError:
    return NextActionError(
        failure_code="invalid_structured_output",
        detail=detail,
        raw_excerpt=(text or "").strip()[:200],
    )


def _extract_payload(text: str) -> dict | NextActionError:
    raw = (text or "").strip()
    fenced = _FENCE.search(raw)
    if fenced:
        raw = fenced.group(1)
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return _refuse("reply is not a JSON object", text)
    if not isinstance(payload, dict):
        return _refuse("reply is JSON but not an object", text)
    return payload


def _validate_schema(payload: dict) -> str | None:
    if payload.get("schema") != NEXT_ACTION_SCHEMA:
        return f"schema is {payload.get('schema')!r}, not {NEXT_ACTION_SCHEMA}"
    return None


def _validate_action(payload: dict) -> str | None:
    action = payload.get("action")
    if action not in ALLOWED_ACTIONS:
        # The closed set IS the security boundary: "run_shell" dies here.
        return f"action {action!r} is not in the allowed set"
    return None


def _validate_facts(payload: dict) -> str | None:
    facts = payload.get("required_facts") or []
    if not isinstance(facts, list) or not all(
        isinstance(f, dict) and f.get("schema") and f.get("key") for f in facts
    ):
        return "required_facts must be a list of {schema, key} objects"
    action = payload.get("action")
    if action in {ACTION_REQUEST_FACT, ACTION_RUN_PROBE} and not facts:
        return f"{action} requires a non-empty required_facts"
    return None


def _validate_patch(payload: dict) -> str | None:
    action = payload.get("action")
    patch = payload.get("patch")
    if action == ACTION_PROPOSE_PATCH:
        if not isinstance(patch, str) or "--- " not in patch or "+++ " not in patch:
            return "propose_patch requires `patch` to be a unified diff"
    elif patch:
        return f"{action} must not carry a patch"
    return None


def _clamped_confidence(payload: dict) -> float:
    try:
        return min(1.0, max(0.0, float(payload.get("confidence") or 0.0)))
    except (TypeError, ValueError):
        return 0.0
