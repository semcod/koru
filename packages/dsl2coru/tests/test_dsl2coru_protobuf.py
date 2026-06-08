"""Protobuf round-trip tests."""

from dsl2coru.codec import envelope_from_bytes, envelope_to_bytes, roundtrip_text
from dsl2coru.pb_codec import decode_protobuf_to_text, encode_text_to_protobuf


def test_protobuf_roundtrip_status() -> None:
    line = "STATUS --probe"
    pb = encode_text_to_protobuf(line)
    again = decode_protobuf_to_text(pb)
    assert "STATUS" in again


def test_codec_bytes_roundtrip_auto() -> None:
    payload_bytes = envelope_to_bytes({"verb": "AUTO", "shell": "bash"})
    payload = envelope_from_bytes(payload_bytes)
    assert payload["verb"] == "AUTO"
    assert payload["shell"] == "bash"


def test_text_roundtrip_query() -> None:
    line = "QUERY status"
    again = roundtrip_text(line)
    assert "QUERY" in again
