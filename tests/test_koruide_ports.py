"""Smoke tests for koru-arch-1 PoC: IDE control-plane Port abstractions.

These tests pin two properties that the strangler-fig migration relies on:

1. The existing concrete adapter (:class:`koruide.client.KoruIDEClient`)
   structurally satisfies :class:`koruide.ports.IdeChatPort` /
   :class:`IdeLifecyclePort` — so moving callers to depend on the ports
   instead of the concrete class is a non-breaking refactor.

2. A trivial in-memory fake also satisfies :class:`IdeChatPort`, proving
   the port is genuinely testable without a Unix socket.
"""

from __future__ import annotations

from collections.abc import Callable

from koruide.client import KoruIDEClient
from koruide.ports import (
    ChatMessage,
    DriveOutcome,
    IdeChatHistoryPort,
    IdeChatPort,
    IdeLifecyclePort,
)


def test_real_client_satisfies_chat_and_lifecycle_ports() -> None:
    client = KoruIDEClient()
    assert isinstance(client, IdeChatPort), "KoruIDEClient must implement IdeChatPort"
    assert isinstance(client, IdeLifecyclePort), "KoruIDEClient must implement IdeLifecyclePort"


class _FakeChatAdapter:
    def __init__(self) -> None:
        self.calls: list[tuple[str, bool, str | None, bool]] = []

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str | None = None,
        require_plugin: bool = False,
    ) -> DriveOutcome:
        self.calls.append((text, submit, ide, require_plugin))
        return DriveOutcome(ok=True, submitted=submit, paste="ok", submit="ok")


def test_fake_adapter_satisfies_chat_port() -> None:
    fake = _FakeChatAdapter()
    assert isinstance(fake, IdeChatPort)
    outcome = fake.drive("hello", submit=True, ide="cursor")
    assert outcome.ok is True
    assert outcome.submitted is True
    assert fake.calls == [("hello", True, "cursor", False)]


class _FakeHistoryAdapter:
    def __init__(self) -> None:
        self._handlers: list[Callable[[ChatMessage], None]] = []

    def subscribe(self, handler: Callable[[ChatMessage], None]) -> Callable[[], None]:
        self._handlers.append(handler)

        def unsubscribe() -> None:
            self._handlers.remove(handler)

        return unsubscribe

    def emit(self, message: ChatMessage) -> None:
        for handler in list(self._handlers):
            handler(message)


def test_fake_history_adapter_satisfies_history_port() -> None:
    fake = _FakeHistoryAdapter()
    assert isinstance(fake, IdeChatHistoryPort)

    received: list[ChatMessage] = []
    unsubscribe = fake.subscribe(received.append)
    fake.emit(ChatMessage(chat="conv-1", text="hi", summary="hi"))
    unsubscribe()
    fake.emit(ChatMessage(chat="conv-1", text="ignored"))

    assert len(received) == 1
    assert received[0].text == "hi"


def test_drive_outcome_is_immutable_dataclass() -> None:
    outcome = DriveOutcome(ok=True, submitted=False, diagnostics={"reason": "input-busy"})
    assert outcome.ok is True
    assert outcome.diagnostics == {"reason": "input-busy"}
    try:
        outcome.ok = False  # type: ignore[misc]
    except Exception:
        pass
    else:
        raise AssertionError("DriveOutcome must be frozen")
