"""In-process publish/subscribe event bus for domain events."""

from __future__ import annotations

import threading
from collections import defaultdict
from collections.abc import Callable

from koru.cqrs.event_store import StoredEvent

EventHandler = Callable[[StoredEvent], None]


class InProcessEventBus:
    """Simple synchronous event bus."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._handlers: dict[str, list[EventHandler]] = defaultdict(list)
        self._wildcard_handlers: list[EventHandler] = []

    def subscribe(self, handler: EventHandler, *, event_type: str | None = None) -> None:
        with self._lock:
            if event_type:
                self._handlers[event_type].append(handler)
            else:
                self._wildcard_handlers.append(handler)

    def publish(self, event: StoredEvent) -> None:
        with self._lock:
            handlers = list(self._wildcard_handlers)
            handlers.extend(self._handlers.get(event.event_type, ()))
        for handler in handlers:
            handler(event)


__all__ = ["EventHandler", "InProcessEventBus"]
