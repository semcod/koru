"""Compatibility aliases for the canonical DSL validation codec."""

from dsl2koru.codec import (
    envelope_from_bytes,
    envelope_from_json,
    envelope_to_bytes,
    envelope_to_json,
    parse_text,
    roundtrip_text,
    validate_payload,
)

__all__ = [
    "envelope_from_bytes",
    "envelope_from_json",
    "envelope_to_bytes",
    "envelope_to_json",
    "parse_text",
    "roundtrip_text",
    "validate_payload",
]
