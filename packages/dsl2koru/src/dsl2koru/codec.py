"""Validate and encode commands from both DSL command-name families."""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from dsl2koru.grammar import parse_line, to_text
from dsl2koru.pb_codec import decode_protobuf, encode_protobuf
from dsl2koru.schema_registry import normalize_verb, schema_for_verb


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    verb = normalize_verb(str(payload.get("verb", "")))
    if not verb:
        raise ValueError("missing verb")
    normalized = payload if payload.get("verb") == verb else {**payload, "verb": verb}
    jsonschema.validate(normalized, schema_for_verb(verb))
    return normalized


def parse_text(
    line: str,
    *,
    default_project: str | None = None,
    default_file: str | None = None,
) -> dict[str, Any]:
    payload = parse_line(line, default_project=default_project, default_file=default_file)
    return validate_payload(payload) if payload else {}


def envelope_to_bytes(
    payload: dict[str, Any],
    *,
    default_project: str = "",
    default_file: str = "",
    correlation_id: str = "",
) -> bytes:
    return encode_protobuf(
        validate_payload(payload),
        default_project=default_project,
        default_file=default_file,
        correlation_id=correlation_id,
    )


def envelope_from_bytes(data: bytes) -> dict[str, Any]:
    return validate_payload(decode_protobuf(data))


def envelope_to_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(validate_payload(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")


def envelope_from_json(data: bytes) -> dict[str, Any]:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("envelope must be a JSON object")
    return validate_payload(payload)


def roundtrip_text(
    line: str,
    *,
    default_project: str | None = None,
    default_file: str | None = None,
) -> str:
    payload = parse_text(line, default_project=default_project, default_file=default_file)
    wire = envelope_from_bytes(
        envelope_to_bytes(
            payload,
            default_project=default_project or "",
            default_file=default_file or "",
        )
    )
    return to_text(wire)
