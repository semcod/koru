"""Compatibility facade over the canonical protobuf codec."""

from dsl2koru.pb_codec import (
    decode_protobuf,
    dict_to_envelope,
    encode_protobuf,
    encode_result_protobuf,
    envelope_to_dict,
    pb_to_result,
    result_to_pb,
)

from dsl2coru.grammar import parse_line, to_text


def encode_text_to_protobuf(line: str, *, default_file: str = "", correlation_id: str = "") -> bytes:
    payload = parse_line(line, default_file=default_file or None)
    if not payload:
        raise ValueError("empty command")
    return encode_protobuf(payload, default_file=default_file, correlation_id=correlation_id)


def decode_protobuf_to_text(data: bytes) -> str:
    return to_text(decode_protobuf(data))


__all__ = [
    "decode_protobuf",
    "decode_protobuf_to_text",
    "dict_to_envelope",
    "encode_protobuf",
    "encode_result_protobuf",
    "encode_text_to_protobuf",
    "envelope_to_dict",
    "pb_to_result",
    "result_to_pb",
]
