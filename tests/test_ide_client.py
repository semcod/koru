"""Tests for :mod:`koru.ide_client`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from koru import ide_client as ide_client_mod
from koru.autopilot import client as autopilot_client_mod
from koru.ide_client import (
    LegacyAutopilotClientAdapter,
    build_ide_client,
    build_koruide_client,
    build_legacy_ide_client,
)


def test_legacy_adapter_forwards_all_operations() -> None:
    client = MagicMock()
    client.is_running.return_value = True
    client.drive.return_value = {"ok": True, "backend": "plugin"}
    client.status.return_value = {"ok": True, "plugins": []}
    client.shutdown.return_value = {"ok": True, "stopping": True}

    adapter = LegacyAutopilotClientAdapter(client=client)

    assert adapter.is_running() is True
    assert adapter.drive("hello", submit=False, ide="vscode") == {"ok": True, "backend": "plugin"}
    assert adapter.status() == {"ok": True, "plugins": []}
    assert adapter.shutdown() == {"ok": True, "stopping": True}

    client.is_running.assert_called_once_with()
    client.drive.assert_called_once_with("hello", submit=False, ide="vscode", require_plugin=False)
    client.status.assert_called_once_with()
    client.shutdown.assert_called_once_with()


def test_build_legacy_ide_client_uses_autopilot_client(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeAutopilotClient:
        def __init__(self, *, socket_path: Path | None = None, timeout: float = 5.0) -> None:
            captured["socket_path"] = socket_path
            captured["timeout"] = timeout

        def is_running(self) -> bool:
            return False

        def drive(self, *_args, **_kwargs):
            return {"ok": True}

        def status(self):
            return {"ok": True}

        def shutdown(self):
            return {"ok": True}

    monkeypatch.setattr(autopilot_client_mod, "AutopilotClient", FakeAutopilotClient)

    socket = Path("/tmp/koru-test.sock")
    wrapped = build_legacy_ide_client(socket_path=socket, timeout=0.75)

    assert isinstance(wrapped, LegacyAutopilotClientAdapter)
    assert captured == {"socket_path": socket, "timeout": 0.75}
    assert wrapped.is_running() is False


def test_build_koruide_client_uses_koruide_package(monkeypatch) -> None:
    captured: dict[str, object] = {}

    class FakeKoruIDEClient:
        pass

    def fake_build_client(*, socket_path=None, timeout=5.0):
        captured["socket_path"] = socket_path
        captured["timeout"] = timeout
        return FakeKoruIDEClient()

    monkeypatch.setattr("koruide.client.build_client", fake_build_client)

    sock = Path("/tmp/koruide.sock")
    wrapped = build_koruide_client(socket_path=sock, timeout=0.4)

    assert isinstance(wrapped, FakeKoruIDEClient)
    assert captured == {"socket_path": sock, "timeout": 0.4}


def test_build_ide_client_defaults_to_legacy(monkeypatch) -> None:
    monkeypatch.delenv("KORU_IDE_BACKEND", raising=False)
    marker = object()
    monkeypatch.setattr(ide_client_mod, "build_legacy_ide_client", lambda **_kwargs: marker)

    out = build_ide_client()

    assert out is marker


def test_build_ide_client_can_select_koruide(monkeypatch) -> None:
    marker = object()
    monkeypatch.setattr(ide_client_mod, "build_koruide_client", lambda **_kwargs: marker)

    out = build_ide_client(backend="koruide")

    assert out is marker


def test_build_ide_client_uses_env_when_backend_not_passed(monkeypatch) -> None:
    marker = object()
    monkeypatch.setenv("KORU_IDE_BACKEND", "koruide")
    monkeypatch.setattr(ide_client_mod, "build_koruide_client", lambda **_kwargs: marker)

    out = build_ide_client()

    assert out is marker
