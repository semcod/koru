"""Compatibility facade over the canonical protobuf codec."""

from dsl2koru.pb_codec import (
    decode_protobuf,
    decode_protobuf_to_text,
    dict_to_envelope,
    encode_protobuf,
    encode_result_protobuf,
    encode_text_to_protobuf,
    envelope_to_dict,
    pb_to_result,
    result_to_pb,
)

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
