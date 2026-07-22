"""Hexagonal Port abstractions for the IDE control plane (koru-arch-1 PoC).

Background
----------
``src/koruide/`` already has a clean NDJSON socket protocol between the
VSCode/Cursor plugin (TypeScript adapter in ``plugins/koru-autopilot-vscode/``)
and the Python daemon. That gives us a natural hexagonal seam, but the seam
is implicit: callers depend on concrete classes like ``KoruIDEClient`` instead
of abstractions.

This module names the three ports the rest of koru actually needs:

* :class:`IdeChatPort`           — paste text into the chat input and submit
* :class:`IdeChatHistoryPort`    — observe assistant ``message.received`` events
* :class:`IdeLifecyclePort`      — daemon health / shutdown

By depending on these Protocols (PEP 544 structural typing), application code
in ``koru.autonomous_*`` and ``koru.bounded_contexts.*`` becomes testable with
fake adapters and decoupled from the socket transport. The existing
``KoruIDEClient`` already satisfies :class:`IdeChatPort` and
:class:`IdeLifecyclePort` structurally — no runtime change is required to
adopt these ports gradually (strangler fig).

Usage
-----
::

    from koruide.ports import IdeChatPort, DriveOutcome

    def autopilot_step(ide: IdeChatPort, text: str) -> DriveOutcome:
        return ide.drive(text, submit=True)

In production wire ``KoruIDEClient`` (concrete adapter). In tests inject a
``FakeIdeAdapter`` implementing the same Protocol — no socket needed.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable


@dataclass(frozen=True)
class DriveOutcome:
    """Result of a single chat drive attempt.

    Mirrors the wire-level ``ack`` payload from ``protocol.py`` so that
    application code never has to inspect raw envelopes.
    """

    ok: bool
    submitted: bool = False
    paste: str | None = None
    submit: str | None = None
    diagnostics: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class ChatMessage:
    """One assistant ``message.received`` row, IDE-agnostic."""

    chat: str
    text: str
    summary: str | None = None
    received_at: str | None = None
    extras: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class IdeChatPort(Protocol):
    """Send text to the IDE chat input.

    The primary outbound port used by ``koru.autonomous_*`` to drive the
    IDE-side LLM panel. Implementations include the production
    :class:`koruide.client.KoruIDEClient` and any in-memory fake.
    """

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str | None = None,
        require_plugin: bool = False,
    ) -> DriveOutcome: ...


@runtime_checkable
class IdeChatHistoryPort(Protocol):
    """Observe assistant messages produced by the IDE-side LLM.

    The plugin-side ``ChatHistoryWatcher`` (see ``chat-history-watcher.ts``)
    forwards ``message.received`` events to the daemon; the daemon-side
    consumer implements this port to feed
    ``koru.llm_reflect`` / saga state machines.
    """

    def subscribe(self, handler: Callable[[ChatMessage], None]) -> Callable[[], None]:
        """Register *handler*; return an unsubscribe callable."""


@runtime_checkable
class IdeLifecyclePort(Protocol):
    """Daemon liveness and orderly shutdown."""

    def is_running(self) -> bool: ...

    def shutdown(self) -> bool: ...


__all__ = [
    "ChatMessage",
    "DriveOutcome",
    "IdeChatHistoryPort",
    "IdeChatPort",
    "IdeLifecyclePort",
]
