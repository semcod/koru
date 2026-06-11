"""dsl2coru — CORU control DSL with JSON Schema + protobuf wire codec."""

from dsl2coru.bus import dispatch, dispatch_text, execute_dsl, execute_dsl_line
from dsl2coru.codec import (
    envelope_from_bytes,
    envelope_from_json,
    envelope_to_bytes,
    envelope_to_json,
    parse_text,
    roundtrip_text,
    validate_payload,
)
from dsl2coru.parser import parse_line
from dsl2coru.pb_codec import decode_protobuf, encode_protobuf, encode_result_protobuf
from dsl2coru.result import DslResult
from dsl2coru.schema_registry import all_verbs, validate_schemas
from dsl2coru.serializer import to_text

__all__ = [
    "DslResult",
    "all_verbs",
    "decode_protobuf",
    "dispatch",
    "dispatch_text",
    "encode_protobuf",
    "encode_result_protobuf",
    "envelope_from_bytes",
    "envelope_from_json",
    "envelope_to_bytes",
    "envelope_to_json",
    "execute_dsl",
    "execute_dsl_line",
    "parse_line",
    "parse_text",
    "roundtrip_text",
    "to_text",
    "validate_payload",
    "validate_schemas",
]