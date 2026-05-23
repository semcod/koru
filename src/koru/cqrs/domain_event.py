"""Domain-event helpers shared across bounded contexts."""

from __future__ import annotations

from dataclasses import asdict
from typing import Any


class DomainEvent:
    """Base helper for dataclass-backed domain events."""

    def to_payload(self) -> dict[str, Any]:
        payload = asdict(self)
        if isinstance(payload, dict):
            return payload
        return {}


__all__ = ["DomainEvent"]