"""Task-owned acceptance for structured Koru replies; never executes commands."""
from __future__ import annotations

import json
from typing import Any

from nlp2koru.to_dsl import _VALID_ACTIONS


def _unique_object(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate response field")
        result[key] = value
    return result


def _invalid_constant(value: str) -> None:
    raise ValueError("non-finite response value: " + value)


def response_object(text: str) -> dict[str, Any]:
    value = json.loads(text, object_pairs_hook=_unique_object, parse_constant=_invalid_constant)
    if not isinstance(value, dict):
        raise ValueError("response must be a JSON object")
    return value


def valid_intent_payload(payload: dict[str, Any]) -> bool:
    action = payload.get("action")
    return (
        isinstance(action, str)
        and action.strip().lower() in _VALID_ACTIONS
        and set(payload) <= {"action", "ide", "instance", "install"}
        and type(payload.get("install", False)) is bool
        and all(payload.get(key) is None or isinstance(payload[key], str) for key in ("ide", "instance"))
    )


def valid_intent_response(text: str) -> bool:
    try:
        return valid_intent_payload(response_object(text))
    except (ValueError, TypeError):
        return False


def valid_dsl_response(text: str, *, project: str | None = None) -> bool:
    from dsl2koru.codec import parse_text
    from dsl2koru.schema_registry import KORU_DELEGATE_VERBS
    from jsonschema.exceptions import ValidationError

    try:
        payload = response_object(text)
        line = payload.get("dsl")
        if set(payload) != {"dsl"} or not isinstance(line, str) or not line.strip():
            return False
        if any(character in line for character in ("\n", "\r", "\0")):
            return False
        parsed = parse_text(line.strip(), default_project=project)
        return parsed.get("verb") in KORU_DELEGATE_VERBS
    except (ValueError, TypeError, ValidationError):
        return False
