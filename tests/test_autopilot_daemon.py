"""End-to-end tests for the autopilot daemon over a real unix socket.

We run the daemon on a background thread, connect a real client, and
assert the round-trip behaviour. The :class:`Injector` is replaced
with a stub so no actual keyboard events are emitted.
"""

from __future__ import annotations

import socket
import threading
import time
from pathlib import Path
from typing import Any

import pytest

from koru.autopilot import daemon as daemon_mod
from koru.autopilot import ide as ide_mod
from koru.autopilot.client import AutopilotClient
from koru.autopilot.daemon import AutopilotDaemon
from koru.autopilot.injector import InjectionResult, InjectorError
from koru.autopilot.protocol import Message, decode, hello


def _patch_no_running_ides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make IDE detection a no-op for both the ide module and daemon import."""
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda **_: [])
    monkeypatch.setattr(daemon_mod, "detect_running_ides", lambda **_: [])


class _StubInjector:
    """Replaces :class:`koru.autopilot.injector.Injector` for tests."""

    def __init__(self, *, fail: bool = False) -> None:
        self.fail = fail
        self.calls: list[dict[str, Any]] = []

    def type_text(
        self,
        text: str,
        *,
        ide: str = "default",
        submit: bool = True,
        dry_run: bool = False,
    ) -> InjectionResult:
        self.calls.append({"text": text, "ide": ide, "submit": submit})
        if self.fail:
            raise InjectorError("stub failure")
        return InjectionResult(backend="stub", submitted=submit)

    def probe(self) -> list:
        return []

    def select_backend(self) -> str:
        return "stub"


@pytest.fixture
def running_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Yield (daemon, client, injector) with no IDE auto-detection."""
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    injector = _StubInjector()
    daemon = AutopilotDaemon(socket_path=sock_path, injector=injector)
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    # Wait briefly for the loop to pick up the registered server.
    time.sleep(0.05)
    client = AutopilotClient(socket_path=sock_path, timeout=2.0)
    try:
        yield daemon, client, injector
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_ping_round_trip(running_daemon) -> None:
    _, client, _ = running_daemon
    reply = client.request(Message(type="ping", id="p1"))
    assert reply.type == "ack"
    assert reply.id == "p1"
    assert reply.data.get("pong") is True


def test_is_running_true_when_daemon_alive(running_daemon) -> None:
    _, client, _ = running_daemon
    assert client.is_running() is True


def test_drive_falls_back_to_injector_when_no_plugin(running_daemon) -> None:
    _, client, injector = running_daemon
    reply = client.drive("hello there", submit=True, ide="auto")
    assert reply["ok"] is True
    assert reply["backend"] == "stub"
    assert injector.calls == [{"text": "hello there", "ide": "default", "submit": True}]


def test_drive_reports_injector_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    daemon = AutopilotDaemon(socket_path=sock_path, injector=_StubInjector(fail=True))
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    client = AutopilotClient(socket_path=sock_path, timeout=2.0)
    try:
        reply = client.drive("hi")
        assert reply["type"] == "error"
        assert "stub failure" in reply["message"]
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_drive_empty_text_returns_error(running_daemon) -> None:
    _, client, _ = running_daemon
    reply = client.request(Message(type="drive", id="d1", data={"text": ""}))
    assert reply.type == "error"


def test_drive_unknown_type_returns_error(running_daemon) -> None:
    _, client, _ = running_daemon
    # Send raw bytes for an unknown but well-formed envelope: the
    # validator should reject it before dispatch.
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect(str(client.socket_path))
    sock.sendall(b'{"type":"bogus","id":"x"}\n')
    buf = b""
    while b"\n" not in buf:
        chunk = sock.recv(4096)
        if not chunk:
            break
        buf += chunk
    sock.close()
    line, _, _ = buf.partition(b"\n")
    msg = decode(line)
    assert msg.type == "error"


def test_status_reports_socket_and_plugins(running_daemon) -> None:
    _, client, _ = running_daemon
    info = client.status()
    assert info["type"] == "ack"
    assert info["ok"] is True
    assert "socket" in info
    assert info["plugins"] == []


def test_plugin_hello_then_drive_forwards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plugin connects, says hello; subsequent drive is forwarded to it."""
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    injector = _StubInjector()
    daemon = AutopilotDaemon(socket_path=sock_path, injector=injector)
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    try:
        # Plugin connection — long-lived.
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(sock_path))
        plugin.sendall(hello(ide="vscode", version="0.1.0", pid=42, id="h").encode())

        def _read_line(sock: socket.socket) -> bytes:
            buf = b""
            while b"\n" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf += chunk
            line, _, _ = buf.partition(b"\n")
            return line

        ack_hello = decode(_read_line(plugin))
        assert ack_hello.type == "ack"
        assert ack_hello.data.get("role") == "plugin"

        # CLI sends drive in another connection. Server should forward
        # chat.send to the plugin and then relay the plugin's ack.
        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(sock_path))
        cli.sendall(
            Message(type="drive", id="d1",
                    data={"text": "hi", "ide": "vscode", "submit": True}).encode()
        )

        # Plugin receives chat.send.
        forwarded = decode(_read_line(plugin))
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode()
        )

        cli_reply = decode(_read_line(cli))
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("delivered") is True

        # Injector must NOT have been invoked — plugin path took over.
        assert injector.calls == []
        plugin.close()
        cli.close()
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_default_handoff_builds_brief_for_uninitialised_project(tmp_path: Path) -> None:
    """_default_handoff wires build_context + render_markdown_handoff.

    For an uninitialised project the brief should at least mention the
    setup section koru emits — we don't pin the exact wording.
    """
    from koru.autopilot.daemon import _default_handoff

    builder = _default_handoff(tmp_path)
    text = builder({"chat": "default", "reason": "", "ide": "vscode"})
    assert isinstance(text, str)
    assert text.strip()
    # Sanity: the markdown brief always opens with a markdown heading.
    assert text.lstrip().startswith("#")


class _LineReader:
    """Tiny stateful NDJSON line reader over a blocking socket.

    The plain ``_read_line`` helper used to discard everything after
    the first newline of each ``recv``, which broke any test that
    expected two frames in quick succession (they often arrive in a
    single recv). This wrapper keeps the leftover between calls.
    """

    def __init__(self, sock: socket.socket) -> None:
        self.sock = sock
        self.buf = bytearray()

    def read_line(self) -> bytes:
        while b"\n" not in self.buf:
            chunk = self.sock.recv(8192)
            if not chunk:
                break
            self.buf.extend(chunk)
        idx = self.buf.find(b"\n")
        if idx < 0:
            line = bytes(self.buf)
            self.buf.clear()
            return line
        line = bytes(self.buf[:idx])
        del self.buf[: idx + 1]
        return line


def _read_line(sock: socket.socket) -> bytes:
    """Read a single NDJSON line from a fresh socket (no carry-over).

    Use :class:`_LineReader` for any test that reads multiple frames
    from the same connection.
    """
    reader = _LineReader(sock)
    return reader.read_line()


def _start_daemon_with_handoff(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    handoff,
    handoff_cooldown: float = 0.0,
):
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    daemon = AutopilotDaemon(
        socket_path=sock_path,
        injector=_StubInjector(),
        handoff=handoff,
        handoff_cooldown=handoff_cooldown,
    )
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    return daemon, thread, sock_path


def test_session_ended_triggers_handoff_chat_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    captured: list[dict] = []

    def fake_handoff(event: dict) -> str:
        captured.append(event)
        return "# next ticket\n\nrun pytest -q"

    daemon, thread, sock_path = _start_daemon_with_handoff(
        tmp_path, monkeypatch, handoff=fake_handoff, handoff_cooldown=0.0,
    )
    try:
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(sock_path))
        reader = _LineReader(plugin)
        plugin.sendall(hello(ide="windsurf", version="0.1.0", pid=42, id="h").encode())
        ack_hello = decode(reader.read_line())
        assert ack_hello.type == "ack"

        plugin.sendall(
            Message(
                type="session.ended",
                id="ev1",
                data={"chat": "cascade", "reason": "user-stop"},
            ).encode()
        )

        # The daemon emits two frames in response: (1) the chat.send
        # carrying the brief, and (2) an ack for the session.ended.
        frame_a = decode(reader.read_line())
        frame_b = decode(reader.read_line())
        types = sorted([frame_a.type, frame_b.type])
        assert types == ["ack", "chat.send"]

        chat_msg = frame_a if frame_a.type == "chat.send" else frame_b
        ack_msg = frame_b if frame_a.type == "chat.send" else frame_a

        assert chat_msg.data["text"] == "# next ticket\n\nrun pytest -q"
        assert chat_msg.data["submit"] is True
        assert ack_msg.id == "ev1"
        assert ack_msg.data["handoff"] == "sent"
        assert ack_msg.data["chars"] == len("# next ticket\n\nrun pytest -q")

        # Handoff was invoked exactly once with the event metadata.
        assert len(captured) == 1
        assert captured[0]["chat"] == "cascade"
        assert captured[0]["reason"] == "user-stop"
        assert captured[0]["ide"] == "windsurf"

        plugin.close()
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_session_ended_no_handoff_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # ``handoff=None`` (the default) — daemon must just ack and not
    # send anything else, even on session.ended.
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    daemon = AutopilotDaemon(socket_path=sock_path, injector=_StubInjector())
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    try:
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(sock_path))
        plugin.sendall(hello(ide="vscode", version="0.1", pid=1, id="h").encode())
        _read_line(plugin)  # ack hello

        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x", "reason": ""}).encode()
        )
        first = decode(_read_line(plugin))
        assert first.type == "ack"
        assert first.id == "ev1"
        assert first.data.get("event") == "session.ended"
        # No chat.send must follow — verify the socket has no more
        # data within a short window.
        plugin.settimeout(0.2)
        with pytest.raises(socket.timeout):
            plugin.recv(1)
        plugin.close()
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_session_ended_skipped_during_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Force a cooldown that's long enough that an immediate session.ended
    # following our own drive must be skipped.
    calls: list[dict] = []

    def fake_handoff(event: dict) -> str:
        calls.append(event)
        return "should not be typed"

    daemon, thread, sock_path = _start_daemon_with_handoff(
        tmp_path, monkeypatch, handoff=fake_handoff, handoff_cooldown=10.0,
    )
    try:
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(sock_path))
        plugin.sendall(hello(ide="windsurf", version="0.1", pid=1, id="h").encode())
        _read_line(plugin)

        # Simulate the daemon having just typed: set the timestamp
        # via the public attribute (we documented this is the cooldown
        # source of truth).
        daemon._last_chat_send_at = time.monotonic()

        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x"}).encode()
        )
        first = decode(_read_line(plugin))
        assert first.type == "ack"
        assert first.data["handoff"] == "skipped"
        assert "cooldown" in first.data["reason"]
        assert calls == []  # handoff builder must NOT have been called
        plugin.close()
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_session_started_event_just_acks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Even with handoff enabled, session.started must NOT trigger a brief.
    daemon, thread, sock_path = _start_daemon_with_handoff(
        tmp_path, monkeypatch, handoff=lambda _e: "must not appear",
    )
    try:
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(sock_path))
        plugin.sendall(hello(ide="vscode", version="0.1", pid=1, id="h").encode())
        _read_line(plugin)

        plugin.sendall(
            Message(type="session.started", id="ev1", data={"chat": "x"}).encode()
        )
        first = decode(_read_line(plugin))
        assert first.type == "ack"
        # No "handoff" key on a session.started ack.
        assert "handoff" not in first.data
        plugin.settimeout(0.2)
        with pytest.raises(socket.timeout):
            plugin.recv(1)
        plugin.close()
    finally:
        daemon.stop()
        thread.join(timeout=2.0)


def test_shutdown_stops_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_no_running_ides(monkeypatch)
    sock_path = tmp_path / "autopilot.sock"
    daemon = AutopilotDaemon(socket_path=sock_path, injector=_StubInjector())
    daemon.start()
    thread = threading.Thread(target=daemon.serve_forever, daemon=True)
    thread.start()
    time.sleep(0.05)
    client = AutopilotClient(socket_path=sock_path, timeout=2.0)
    reply = client.shutdown()
    assert reply["ok"] is True
    thread.join(timeout=2.0)
    assert not thread.is_alive()
    assert not sock_path.exists()
