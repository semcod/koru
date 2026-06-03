"""Event-sourced repair audit log (append-only)."""

from __future__ import annotations

import uuid
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from typing import Any, Literal

EVENT_SCHEMA = "coru.repair.event.v1"

RepairEventType = Literal[
    "repair.session.started",
    "repair.problems.detected",
    "repair.command.dispatched",
    "repair.attempt.finished",
    "repair.session.finished",
    "repair.diagnosis.recorded",
]


@dataclass(frozen=True)
class RepairEvent:
    event_type: RepairEventType
    aggregate_id: str
    payload: dict[str, Any]
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex)
    occurred_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    schema: str = EVENT_SCHEMA

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema": self.schema,
            "event_id": self.event_id,
            "event_type": self.event_type,
            "occurred_at": self.occurred_at,
            "aggregate_id": self.aggregate_id,
            "payload": self.payload,
        }

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> RepairEvent:
        return cls(
            event_type=str(raw.get("event_type") or ""),
            aggregate_id=str(raw.get("aggregate_id") or ""),
            payload=dict(raw.get("payload") or {}),
            event_id=str(raw.get("event_id") or uuid.uuid4().hex),
            occurred_at=str(raw.get("occurred_at") or datetime.now(UTC).isoformat()),
            schema=str(raw.get("schema") or EVENT_SCHEMA),
        )


def aggregate_id_for(ide: str, instance: str) -> str:
    return f"{ide.strip().lower()}/{instance.strip()}"
