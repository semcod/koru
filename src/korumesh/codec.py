"""JSON wire codec for :class:`~korumesh.envelope.Envelope`."""

from __future__ import annotations

import base64
import json
from typing import Any

from korumesh.envelope import Envelope


def envelope_to_wire(envelope: Envelope) -> str:
    payload = {
        "envelope_id": envelope.envelope_id,
        "peer_from": envelope.peer_from,
        "peer_to": envelope.peer_to,
        "topic": envelope.topic,
        "mime": envelope.mime,
        "payload_b64": base64.b64encode(envelope.payload).decode("ascii"),
        "created_at": envelope.created_at,
        "hmac": envelope.hmac,
    }
    return json.dumps(payload, separators=(",", ":"), sort_keys=True)


def envelope_from_wire(text: str) -> Envelope:
    data: dict[str, Any] = json.loads(text)
    return Envelope(
        envelope_id=str(data["envelope_id"]),
        peer_from=str(data["peer_from"]),
        peer_to=str(data["peer_to"]),
        topic=str(data["topic"]),
        mime=str(data["mime"]),
        payload=base64.b64decode(str(data["payload_b64"])),
        created_at=str(data["created_at"]),
        hmac=str(data["hmac"]),
    )
