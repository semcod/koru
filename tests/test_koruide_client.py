"""Tests for :mod:`koruide.client`."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

from koruide.client import KoruIDEClient, build_client


def test_koruide_client_forwards_all_operations() -> None:
    transport = MagicMock()
    transport.is_running.return_value = True
    transport.drive.return_value = {"ok": True, "backend": "plugin"}
    transport.status.return_value = {"ok": True, "plugins": []}
    transport.shutdown.return_value = {"ok": True, "stopping": True}

    client = KoruIDEClient(client=transport)

    assert client.is_running() is True
    assert client.drive("hello", submit=False, ide="cursor", require_plugin=True) == {
        "ok": True,
        "backend": "plugin",
    }
    assert client.status() == {"ok": True, "plugins": []}
    assert client.shutdown() == {"ok": True, "stopping": True}

    transport.is_running.assert_called_once_with()
    transport.drive.assert_called_once_with(
        "hello",
        submit=False,
        ide="cursor",
        require_plugin=True,
    )
    transport.status.assert_called_once_with()
    transport.shutdown.assert_called_once_with()


def test_build_client_sets_socket_path_and_timeout() -> None:
    sock = Path("/tmp/koruide-test.sock")
    wrapped = build_client(socket_path=sock, timeout=0.25)

    assert isinstance(wrapped, KoruIDEClient)
    assert wrapped.socket_path == sock
    assert wrapped.timeout == 0.25


def test_injected_client_without_request_raises_on_request_path() -> None:
    class TransportNoRequest:
        def is_running(self) -> bool:
            return True

        def drive(self, *_args, **_kwargs):
            return {"ok": True}

        def status(self):
            return {"ok": True}

        def shutdown(self):
            return {"ok": True}

    transport = TransportNoRequest()

    client = KoruIDEClient(client=transport)

    assert client.is_running() is True
    try:
        client.request(MagicMock())
    except RuntimeError as exc:
        assert "request" in str(exc)
    else:
        raise AssertionError("expected RuntimeError for missing request(msg)")


def test_drive_missing_socket_returns_ok_false(tmp_path: Path) -> None:
    missing = tmp_path / "no-such.sock"
    client = KoruIDEClient(socket_path=missing, timeout=0.2)

    reply = client.drive("hello", ide="vscode")

    assert reply.get("ok") is False
    assert "missing" in (reply.get("message") or "").lower()
