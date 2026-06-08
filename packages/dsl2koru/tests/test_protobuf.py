"""Protobuf round-trip tests."""

from dsl2koru.codec import envelope_from_bytes, envelope_to_bytes, roundtrip_text
from dsl2koru.pb_codec import decode_protobuf_to_text, encode_text_to_protobuf


def test_protobuf_roundtrip_query_repair_history() -> None:
    line = "QUERY_REPAIR_HISTORY PROJECT . LIMIT 5"
    pb = encode_text_to_protobuf(line, default_project=".")
    again = decode_protobuf_to_text(pb)
    assert "QUERY_REPAIR_HISTORY" in again
    assert "LIMIT" in again or "5" in again


def test_codec_bytes_roundtrip() -> None:
    line = "VALIDATE_LANE IDE auto INSTANCE default"
    payload_bytes = envelope_to_bytes({"verb": "VALIDATE_LANE", "ide": "auto", "instance": "default"})
    payload = envelope_from_bytes(payload_bytes)
    assert payload["verb"] == "VALIDATE_LANE"


def test_text_roundtrip() -> None:
    line = "QUERY_LANE_STATUS IDE auto INSTANCE default"
    again = roundtrip_text(line)
    assert "QUERY_LANE_STATUS" in again
