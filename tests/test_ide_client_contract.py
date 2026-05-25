"""Contract tests for IDE client implementations.

KIDE-010: same behavioral suite for legacy adapter and koruide client facade.
"""

from __future__ import annotations

from typing import Any

import pytest

from koru.ide_client import LegacyAutopilotClientAdapter
from koruide.client import KoruIDEClient


class _TransportStub:
    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self._running = True

    def is_running(self) -> bool:
        self.calls.append(("is_running", {}))
        return self._running

    def drive(self, text: str, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(("drive", {"text": text, **kwargs}))
        return {
            "ok": True,
            "backend": "stub",
            "text": text,
            "submit": kwargs.get("submit", True),
            "ide": kwargs.get("ide", "auto"),
            "require_plugin": kwargs.get("require_plugin", False),
        }

    def status(self) -> dict[str, Any]:
        self.calls.append(("status", {}))
        return {"ok": True, "plugins": [{"ide": "vscode"}]}

    def shutdown(self) -> dict[str, Any]:
        self.calls.append(("shutdown", {}))
        return {"ok": True, "stopping": True}


def _legacy_factory(transport: _TransportStub):
    return LegacyAutopilotClientAdapter(client=transport)


def _koruide_factory(transport: _TransportStub):
    return KoruIDEClient(client=transport)


@pytest.mark.parametrize("factory", [_legacy_factory, _koruide_factory])
def test_contract_is_running(factory) -> None:
    transport = _TransportStub()
    client = factory(transport)

    assert client.is_running() is True
    assert transport.calls == [("is_running", {})]


def test_contract_drive_legacy() -> None:
    transport = _TransportStub()
    client = _legacy_factory(transport)

    out = client.drive("continue", submit=False, ide="cursor", require_plugin=True)

    assert out["ok"] is True
    assert out["backend"] == "stub"
    assert out["text"] == "continue"
    assert transport.calls == [
        (
            "drive",
            {
                "text": "continue",
                "submit": False,
                "ide": "cursor",
                "require_plugin": True,
            },
        ),
    ]


def test_contract_drive_koruide() -> None:
    transport = _TransportStub()
    client = _koruide_factory(transport)

    out = client.drive("continue", submit=False, ide="cursor", require_plugin=True)

    assert out["ok"] is True
    assert out["backend"] == "stub"
    assert out["text"] == "continue"
    assert transport.calls == [
        (
            "drive",
            {
                "text": "continue",
                "submit": False,
                "ide": "cursor",
                "require_plugin": True,
                "strategy_hint": None,
            },
        ),
    ]


@pytest.mark.parametrize("factory", [_legacy_factory, _koruide_factory])
def test_contract_status(factory) -> None:
    transport = _TransportStub()
    client = factory(transport)

    out = client.status()

    assert out["ok"] is True
    assert out["plugins"][0]["ide"] == "vscode"
    assert transport.calls == [("status", {})]


@pytest.mark.parametrize("factory", [_legacy_factory, _koruide_factory])
def test_contract_shutdown(factory) -> None:
    transport = _TransportStub()
    client = factory(transport)

    out = client.shutdown()

    assert out == {"ok": True, "stopping": True}
    assert transport.calls == [("shutdown", {})]
