"""Batch container for deployment events."""

from __future__ import annotations

import json
import time
import uuid
from dataclasses import dataclass, field
from typing import Any

from koru.deployment_events.models import DeploymentEvent


@dataclass
class DeploymentEventBatch:
    """Batch of events for efficient transmission."""

    events: list[DeploymentEvent] = field(default_factory=list)
    batch_id: str = field(default_factory=lambda: str(uuid.uuid4()))
    batch_timestamp: float = field(default_factory=time.time)

    def add_event(self, event: DeploymentEvent) -> None:
        """Add event to batch."""
        self.events.append(event)

    def to_dict(self) -> dict[str, Any]:
        """Convert batch to dictionary."""
        return {
            "batch_id": self.batch_id,
            "batch_timestamp": self.batch_timestamp,
            "events": [event.to_dict() for event in self.events],
        }

    def to_json(self) -> str:
        """Convert batch to JSON string."""
        return json.dumps(self.to_dict(), indent=2)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> DeploymentEventBatch:
        """Create batch from dictionary."""
        events = [DeploymentEvent.from_dict(e) for e in data.get("events", [])]
        return cls(
            batch_id=data.get("batch_id", str(uuid.uuid4())),
            batch_timestamp=data.get("batch_timestamp", time.time()),
            events=events,
        )

    @classmethod
    def from_json(cls, json_str: str) -> DeploymentEventBatch:
        """Create batch from JSON string."""
        return cls.from_dict(json.loads(json_str))


__all__ = ["DeploymentEventBatch"]