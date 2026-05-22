"""Binary envelope with HMAC authentication for mesh peers."""

from __future__ import annotations

import hashlib
import hmac
import json
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any


@dataclass(frozen=True)
class Envelope:
    envelope_id: str
    peer_from: str
    peer_to: str
    topic: str
    mime: str
    payload: bytes
    created_at: str
    hmac: str

    def header_dict(self) -> dict[str, Any]:
        return {
            "envelope_id": self.envelope_id,
            "peer_from": self.peer_from,
            "peer_to": self.peer_to,
            "topic": self.topic,
            "mime": self.mime,
            "created_at": self.created_at,
        }


def _canonical_header(header: dict[str, Any]) -> bytes:
    return json.dumps(header, sort_keys=True, separators=(",", ":")).encode("utf-8")


def sign_envelope(
    *,
    peer_from: str,
    peer_to: str,
    topic: str,
    mime: str,
    payload: bytes,
    key: bytes,
    envelope_id: str | None = None,
    created_at: str | None = None,
) -> Envelope:
    created = created_at or datetime.now(UTC).isoformat()
    digest = hashlib.sha256(payload).hexdigest()[:16]
    env_id = envelope_id or f"{peer_from}:{topic}:{digest}"
    header = {
        "envelope_id": env_id,
        "peer_from": peer_from,
        "peer_to": peer_to,
        "topic": topic,
        "mime": mime,
        "created_at": created,
    }
    mac = hmac.new(key, _canonical_header(header) + payload, hashlib.sha256).hexdigest()
    return Envelope(
        envelope_id=env_id,
        peer_from=peer_from,
        peer_to=peer_to,
        topic=topic,
        mime=mime,
        payload=payload,
        created_at=created,
        hmac=mac,
    )


def verify_envelope(envelope: Envelope, key: bytes) -> bool:
    signed = sign_envelope(
        peer_from=envelope.peer_from,
        peer_to=envelope.peer_to,
        topic=envelope.topic,
        mime=envelope.mime,
        payload=envelope.payload,
        key=key,
        envelope_id=envelope.envelope_id,
        created_at=envelope.created_at,
    )
    return hmac.compare_digest(signed.hmac, envelope.hmac)
