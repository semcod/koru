"""dsl2koru — Koru control DSL with JSON Schema + protobuf wire codec."""

from dsl2koru.bus import dispatch, execute_dsl, execute_dsl_line
from dsl2koru.codec import (
    envelope_from_bytes,
    envelope_from_json,
    envelope_to_bytes,
    envelope_to_json,
    parse_text,
    roundtrip_text,
    validate_payload,
)
from dsl2koru.pb_codec import decode_protobuf, encode_protobuf, encode_result_protobuf
from dsl2koru.result import DslResult
from dsl2koru.schema_registry import all_verbs, validate_schemas

__all__ = [
    "DslResult",
    "all_verbs",
    "decode_protobuf",
    "dispatch",
    "encode_protobuf",
    "encode_result_protobuf",
    "envelope_from_bytes",
    "envelope_from_json",
    "envelope_to_bytes",
    "envelope_to_json",
    "execute_dsl",
    "execute_dsl_line",
    "parse_text",
    "roundtrip_text",
    "validate_payload",
    "validate_schemas",
]
