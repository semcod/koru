from __future__ import annotations

from korumesh.envelope import Envelope, sign_envelope, verify_envelope


def test_sign_and_verify_envelope_roundtrip() -> None:
    key = b"test-mesh-key-32-bytes-long!!!!"
    envelope = sign_envelope(
        peer_from="host-a",
        peer_to="host-b",
        topic="vision/frame",
        mime="image/png",
        payload=b"\x89PNG",
        key=key,
    )
    assert isinstance(envelope, Envelope)
    assert verify_envelope(envelope, key) is True


def test_verify_envelope_rejects_tampered_payload() -> None:
    key = b"another-test-key-32-bytes!!!!!"
    envelope = sign_envelope(
        peer_from="host-a",
        peer_to="*",
        topic="delegate/task",
        mime="application/json",
        payload=b'{"id":"t1"}',
        key=key,
    )
    tampered = Envelope(
        envelope_id=envelope.envelope_id,
        peer_from=envelope.peer_from,
        peer_to=envelope.peer_to,
        topic=envelope.topic,
        mime=envelope.mime,
        payload=b'{"id":"t2"}',
        created_at=envelope.created_at,
        hmac=envelope.hmac,
    )
    assert verify_envelope(tampered, key) is False
