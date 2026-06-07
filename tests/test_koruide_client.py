"""Tests for :mod:`koruide.client`."""

from __future__ import annotations

import socket
import struct
import threading
from pathlib import Path
from unittest.mock import MagicMock

from koruide.client import KoruIDEClient, build_client
from koruide.protocol import Message


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
        strategy_hint=None,
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


def test_request_returns_structured_error_on_truncated_response(tmp_path: Path) -> None:
    """Daemon sometimes drops trailing newline (multiplexed events, plugin
    disconnect mid-ack, 170k JSON without ``\\n``). The client must NOT
    crash the autonomous loop — it should surface a graceful ``error``
    reply so the cycle can record ``autopilot=failed`` and keep running.
    """
    sock_path = tmp_path / "trunc.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    server.settimeout(3.0)

    def serve() -> None:
        conn, _ = server.accept()
        try:
            conn.recv(4096)
            # Send a truncated JSON envelope with NO trailing newline,
            # then close the connection. Mirrors the production failure.
            conn.sendall(b'{"type":"ack","id":"req-1","ok":true,"info":{"text":"abc')
        finally:
            conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    captured_logs: list[str] = []
    client = KoruIDEClient(
        socket_path=sock_path, timeout=2.0, log=captured_logs.append
    )
    reply = client.request(Message(type="ping", id="req-1"))

    t.join(timeout=3.0)
    server.close()
    sock_path.unlink(missing_ok=True)

    assert reply.type == "error", "truncated response must surface as error reply"
    assert reply.id == "req-1", "correlation id is preserved on graceful error"
    assert reply.data.get("ok") is False
    message = str(reply.data.get("message", ""))
    assert "decoded" in message or "envelope" in message
    assert any("response parse failed" in entry for entry in captured_logs), (
        "diagnostic line with partial bytes must be logged for postmortem"
    )


def test_drive_uses_extended_timeout(monkeypatch) -> None:
    captured: dict[str, object] = {}
    client = KoruIDEClient(socket_path=Path("/tmp/koruide.sock"), timeout=0.25)

    def fake_request(msg, *, timeout=None):
        captured["msg_type"] = msg.type
        captured["timeout"] = timeout
        reply = MagicMock()
        reply.to_dict.return_value = {"ok": True, "backend": "plugin"}
        return reply

    monkeypatch.setenv("KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS", "9")
    client.request = fake_request  # type: ignore[method-assign]

    reply = client.drive("hello", ide="vscode")

    assert reply["ok"] is True
    assert captured == {"msg_type": "drive", "timeout": 9.0}


def test_drive_generates_unique_correlation_ids() -> None:
    captured: list[str | None] = []
    client = KoruIDEClient(socket_path=Path("/tmp/koruide.sock"), timeout=0.25)

    def fake_request(msg, *, timeout=None):
        captured.append(msg.id)
        reply = MagicMock()
        reply.to_dict.return_value = {"ok": True, "backend": "plugin"}
        return reply

    client.request = fake_request  # type: ignore[method-assign]

    client.drive("hello", ide="vscode")
    client.drive("hello again", ide="vscode")

    assert len(captured) == 2
    assert captured[0] != captured[1]
    assert all(str(corr).startswith("cli-drive-") for corr in captured)


def test_request_decodes_length_prefixed_large_ack(tmp_path: Path) -> None:
    """Client must decode framed ACK payloads larger than NDJSON line budget."""
    sock_path = tmp_path / "framed-large.sock"
    server = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    server.bind(str(sock_path))
    server.listen(1)
    server.settimeout(3.0)

    huge = "x" * (1024 * 1024 + 256)
    payload = (
        "{"
        '"type":"ack",'
        '"id":"req-big",'
        '"ok":true,'
        '"backend":"plugin",'
        f'"note":"{huge}"'
        "}"
    ).encode()

    def serve() -> None:
        conn, _ = server.accept()
        try:
            conn.recv(4096)
            conn.sendall(struct.pack(">I", len(payload)) + payload)
        finally:
            conn.close()

    t = threading.Thread(target=serve, daemon=True)
    t.start()

    client = KoruIDEClient(socket_path=sock_path, timeout=2.0)
    reply = client.request(Message(type="ping", id="req-big"))

    t.join(timeout=3.0)
    server.close()
    sock_path.unlink(missing_ok=True)

    assert reply.type == "ack"
    assert reply.id == "req-big"
    assert reply.data.get("ok") is True
    assert reply.data.get("backend") == "plugin"
    assert len(str(reply.data.get("note") or "")) > 1024 * 1024
