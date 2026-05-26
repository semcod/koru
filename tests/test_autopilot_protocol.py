"""Unit tests for the autopilot wire protocol."""

from __future__ import annotations

import json

import pytest

from koru.autopilot.protocol import (
    MAX_LINE_BYTES,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    drive,
    error,
    hello,
    session_ended,
    session_started,
)


def test_encode_round_trip_minimal() -> None:
    msg = Message(type="ping", id="p1")
    line = msg.encode()
    assert line.endswith(b"\n")
    parsed = decode(line)
    assert parsed.type == "ping"
    assert parsed.id == "p1"
    assert parsed.data == {}


def test_encode_strips_reserved_keys_from_data() -> None:
    msg = Message(type="drive", id="d1", data={"text": "hi", "id": "evil", "type": "evil"})
    payload = json.loads(msg.encode())
    assert payload["type"] == "drive"
    assert payload["id"] == "d1"
    assert payload["text"] == "hi"


def test_decode_rejects_unknown_type() -> None:
    with pytest.raises(ProtocolError, match="unknown message type"):
        decode(b'{"type":"nope","id":"x"}\n')


def test_decode_rejects_malformed_json() -> None:
    with pytest.raises(ProtocolError, match="invalid json"):
        decode(b"not json\n")


def test_decode_rejects_oversized_line() -> None:
    huge = b'{"type":"ping","x":"' + b"a" * (MAX_LINE_BYTES + 16) + b'"}\n'
    with pytest.raises(ProtocolError, match="line too large"):
        decode(huge)


def test_decode_rejects_non_object_top_level() -> None:
    with pytest.raises(ProtocolError, match="top-level"):
        decode(b"[1,2,3]\n")


def test_decode_requires_type_field() -> None:
    with pytest.raises(ProtocolError, match="missing 'type'"):
        decode(b'{"id":"x"}\n')


def test_decode_id_must_be_string_when_present() -> None:
    with pytest.raises(ProtocolError, match="'id' must be a string"):
        decode(b'{"type":"ping","id":42}\n')


def test_decode_extra_fields_land_in_data() -> None:
    msg = decode(b'{"type":"chat.send","id":"r1","text":"hi","submit":false}\n')
    assert msg.type == "chat.send"
    assert msg.id == "r1"
    assert msg.data == {"text": "hi", "submit": False}


def test_builders_produce_valid_envelopes() -> None:
    for built in [
        hello(
            ide="vscode",
            version="0.1",
            pid=42,
            id="h",
            protocol_version=1,
            capabilities=["chat.submit"],
        ),
        chat_send("text", submit=True, id="c"),
        drive("text", submit=False, ide="windsurf", id="d"),
        ack("r1", info={"backend": "xdotool"}),
        error("r1", "boom"),
        session_started(chat="cascade", id="s1"),
        session_ended(chat="cascade", reason="user-stop", id="s2"),
    ]:
        reparsed = decode(built.encode())
        assert reparsed.type == built.type
        assert reparsed.id == built.id


def test_ack_default_ok_true() -> None:
    msg = ack("r1")
    assert msg.data == {"ok": True}


def test_error_carries_message() -> None:
    msg = error("r1", "boom")
    assert msg.data["message"] == "boom"
    assert msg.data["ok"] is False


# ---- R12: per-type field schema cap ----


def test_decode_drops_unknown_fields_for_strict_type() -> None:
    """``hello`` accepts known handshake fields; anything else is dropped."""
    raw = (
        b'{"type":"hello","id":"h","ide":"vscode","version":"0.1","pid":1,'
        b'"buildSha":"abc123","protocolVersion":1,"capabilities":["chat.submit"],'
        b'"__proto__":"evil","arbitrary":"stuff"}\n'
    )
    msg = decode(raw)
    assert msg.data == {
        "ide": "vscode",
        "version": "0.1",
        "buildSha": "abc123",
        "pid": 1,
        "protocolVersion": 1,
        "capabilities": ["chat.submit"],
    }
    assert "__proto__" not in msg.data
    assert "arbitrary" not in msg.data


def test_decode_drops_unknown_fields_on_chat_send() -> None:
    raw = b'{"type":"chat.send","id":"c","text":"hi","submit":true,"side":"evil"}\n'
    msg = decode(raw)
    assert msg.data == {"text": "hi", "submit": True}


def test_decode_drops_all_extras_on_zero_field_type() -> None:
    """``ping`` and ``status`` declare an empty allowed set."""
    msg = decode(b'{"type":"ping","id":"p","payload":"junk"}\n')
    assert msg.data == {}


def test_decode_keeps_arbitrary_extras_for_ack() -> None:
    """``ack`` legitimately carries info blocks; pass-through (no cap)."""
    raw = b'{"type":"ack","id":"r","ok":true,"backend":"stub","ide":{"id":"vscode"}}\n'
    msg = decode(raw)
    assert msg.data["ok"] is True
    assert msg.data["backend"] == "stub"
    assert msg.data["ide"] == {"id": "vscode"}


def test_decode_keeps_arbitrary_extras_for_error() -> None:
    msg = decode(b'{"type":"error","id":"r","ok":false,"message":"x","trace":"..."}\n')
    assert msg.data["ok"] is False
    assert msg.data["message"] == "x"
    assert msg.data["trace"] == "..."


def test_drive_with_unknown_ide_field_value_passes_known_fields() -> None:
    """The schema caps WHICH fields are accepted, not which VALUES."""
    raw = b'{"type":"drive","id":"d","text":"hi","ide":"jetbrains","submit":false,"x":1}\n'
    msg = decode(raw)
    assert msg.data == {"text": "hi", "ide": "jetbrains", "submit": False}
