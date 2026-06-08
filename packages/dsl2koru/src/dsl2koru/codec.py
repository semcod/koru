"""Validate dict commands and protobuf wire codec."""

from __future__ import annotations

import json
from typing import Any

import jsonschema

from dsl2koru.grammar import parse_line, to_text
from dsl2koru.pb_codec import decode_protobuf, encode_protobuf
from dsl2koru.schema_registry import schema_for_verb


def validate_payload(payload: dict[str, Any]) -> dict[str, Any]:
    verb = str(payload.get("verb", "")).upper()
    if not verb:
        raise ValueError("missing verb")
    schema = schema_for_verb(verb)
    jsonschema.validate(payload, schema)
    return payload


def parse_text(line: str, *, default_project: str | None = None) -> dict[str, Any]:
    payload = parse_line(line, default_project=default_project)
    if not payload:
        return {}
    return validate_payload(payload)


def envelope_to_bytes(payload: dict[str, Any], *, default_project: str = "", correlation_id: str = "") -> bytes:
    validated = validate_payload(payload)
    return encode_protobuf(validated, default_project=default_project, correlation_id=correlation_id)


def envelope_from_bytes(data: bytes) -> dict[str, Any]:
    payload = decode_protobuf(data)
    return validate_payload(payload)


def envelope_to_json(payload: dict[str, Any]) -> bytes:
    return json.dumps(validate_payload(payload), sort_keys=True, ensure_ascii=False).encode("utf-8")


def envelope_from_json(data: bytes) -> dict[str, Any]:
    payload = json.loads(data.decode("utf-8"))
    if not isinstance(payload, dict):
        raise ValueError("envelope must be a JSON object")
    return validate_payload(payload)


def roundtrip_text(line: str, *, default_project: str | None = None) -> str:
    payload = parse_text(line, default_project=default_project)
    wire = envelope_from_bytes(envelope_to_bytes(payload))
    return to_text(wire)
