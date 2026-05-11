"""End-to-end tests for the autopilot daemon over a real unix socket.

We run the daemon on a background thread, connect a real client, and
assert the round-trip behaviour. The :class:`Injector` is replaced
with a stub so no actual keyboard events are emitted.

Shared plumbing (R2):

* :class:`_LineReader`   — stateful NDJSON reader (preserves leftover
  bytes between frames; the original inline helper used to drop them).
* :class:`_DaemonHarness` — context manager that wires up the daemon
  on a background thread, exposes the socket path, and tears down
  cleanly on exit.
* :func:`_connect_plugin` — opens a socket, sends ``hello``, consumes
  the ack, and returns ``(sock, reader)`` ready to drive.
"""

from __future__ import annotations

import socket
import threading
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Iterator

import pytest

from koru.autopilot import daemon as daemon_mod
from koru.autopilot import ide as ide_mod
from koru.autopilot.client import AutopilotClient
from koru.autopilot.daemon import AutopilotDaemon
from koru.autopilot.injector import InjectionResult, InjectorError
from koru.autopilot.protocol import Message, decode, hello


# ---------------------------------------------------------------------------
# Shared test plumbing
# ---------------------------------------------------------------------------


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


class _LineReader:
    """Stateful NDJSON line reader over a blocking socket.

    Keeps any bytes that arrived after the first newline in an internal
    buffer so subsequent ``read_line()`` calls don't lose them.
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

    def read_message(self) -> Message:
        return decode(self.read_line())


class _DaemonHarness:
    """Spin up :class:`AutopilotDaemon` on a thread and tear it down.

    Use via :func:`_daemon` (context manager); :attr:`sock_path` and
    :attr:`daemon` are exposed for assertions / poking.
    """

    def __init__(
        self,
        tmp_path: Path,
        *,
        injector: _StubInjector | None = None,
        handoff=None,
        handoff_cooldown: float = 0.0,
    ) -> None:
        self.sock_path = tmp_path / "autopilot.sock"
        self.injector = injector or _StubInjector()
        self.daemon = AutopilotDaemon(
            socket_path=self.sock_path,
            injector=self.injector,
            handoff=handoff,
            handoff_cooldown=handoff_cooldown,
        )
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        self.daemon.start()
        self._thread = threading.Thread(target=self.daemon.serve_forever, daemon=True)
        self._thread.start()
        # Give the selector loop a tick to pick up the registered server.
        time.sleep(0.05)

    def stop(self) -> None:
        self.daemon.stop()
        if self._thread is not None:
            self._thread.join(timeout=2.0)

    def client(self, timeout: float = 2.0) -> AutopilotClient:
        return AutopilotClient(socket_path=self.sock_path, timeout=timeout)


@contextmanager
def _daemon(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    injector: _StubInjector | None = None,
    handoff=None,
    handoff_cooldown: float = 0.0,
) -> Iterator[_DaemonHarness]:
    _patch_no_running_ides(monkeypatch)
    harness = _DaemonHarness(
        tmp_path,
        injector=injector,
        handoff=handoff,
        handoff_cooldown=handoff_cooldown,
    )
    harness.start()
    try:
        yield harness
    finally:
        harness.stop()


def _connect_plugin(
    sock_path: Path, *, ide: str = "vscode", version: str = "0.1.0", pid: int = 1,
) -> tuple[socket.socket, _LineReader]:
    """Open a plugin connection, send ``hello``, consume the ack."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect(str(sock_path))
    reader = _LineReader(sock)
    sock.sendall(hello(ide=ide, version=version, pid=pid, id="hello").encode())
    ack = reader.read_message()
    assert ack.type == "ack"
    assert ack.data.get("role") == "plugin"
    return sock, reader


def _assert_no_more_data(sock: socket.socket, *, window: float = 0.2) -> None:
    """Verify the socket has no pending bytes within ``window`` seconds."""
    sock.settimeout(window)
    with pytest.raises(socket.timeout):
        sock.recv(1)


# ---------------------------------------------------------------------------
# Fixture for tests that just need a running daemon + client
# ---------------------------------------------------------------------------


@pytest.fixture
def running_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """Yield (daemon, client, injector) with no IDE auto-detection."""
    with _daemon(tmp_path, monkeypatch) as h:
        yield h.daemon, h.client(), h.injector


# ---------------------------------------------------------------------------
# Basic round-trip tests
# ---------------------------------------------------------------------------


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
    with _daemon(tmp_path, monkeypatch, injector=_StubInjector(fail=True)) as h:
        reply = h.client().drive("hi")
        assert reply["type"] == "error"
        assert "stub failure" in reply["message"]


def test_drive_empty_text_returns_error(running_daemon) -> None:
    _, client, _ = running_daemon
    reply = client.request(Message(type="drive", id="d1", data={"text": ""}))
    assert reply.type == "error"


def test_drive_unknown_type_returns_error(running_daemon) -> None:
    _, client, _ = running_daemon
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(2.0)
    sock.connect(str(client.socket_path))
    sock.sendall(b'{"type":"bogus","id":"x"}\n')
    msg = _LineReader(sock).read_message()
    sock.close()
    assert msg.type == "error"


def test_status_reports_socket_and_plugins(running_daemon) -> None:
    _, client, _ = running_daemon
    info = client.status()
    assert info["type"] == "ack"
    assert info["ok"] is True
    assert "socket" in info
    assert info["plugins"] == []


def test_accept_rejects_foreign_peer_uid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R11: enforce same-UID policy on every accept via SO_PEERCRED."""
    _patch_no_running_ides(monkeypatch)
    daemon_uid = 1000
    foreign_uid = 1001
    monkeypatch.setattr(daemon_mod.os, "getuid", lambda: daemon_uid)
    monkeypatch.setattr(daemon_mod, "_peer_uid", lambda _sock: foreign_uid)

    harness = _DaemonHarness(tmp_path)
    harness.start()
    try:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(1.0)
        sock.connect(str(harness.sock_path))

        # The daemon should close immediately on accept (before registration).
        # Depending on timing/kernel, read can be EOF or connection-reset.
        try:
            data = sock.recv(1)
            assert data == b""
        except OSError:
            pass
        finally:
            sock.close()

        time.sleep(0.05)
        assert harness.daemon._clients == {}
    finally:
        harness.stop()


# ---------------------------------------------------------------------------
# Plugin path
# ---------------------------------------------------------------------------


def test_plugin_hello_then_drive_forwards(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Plugin connects, says hello; subsequent drive is forwarded to it."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)

        # CLI sends drive in another connection.
        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive", id="d1",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode()
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode()
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("delivered") is True

        # Injector must NOT have been invoked — plugin path took over.
        assert h.injector.calls == []
        plugin.close()
        cli.close()


# ---------------------------------------------------------------------------
# Auto-handoff
# ---------------------------------------------------------------------------


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
    assert text.lstrip().startswith("#")


def test_session_ended_triggers_handoff_chat_send(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict] = []

    def fake_handoff(event: dict) -> str:
        captured.append(event)
        return "# next ticket\n\nrun pytest -q"

    with _daemon(tmp_path, monkeypatch, handoff=fake_handoff) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="windsurf", pid=42)
        plugin.sendall(
            Message(
                type="session.ended", id="ev1",
                data={"chat": "cascade", "reason": "user-stop"},
            ).encode()
        )

        # The daemon emits two frames in response: (1) the chat.send
        # carrying the brief, and (2) an ack for the session.ended.
        frame_a = reader.read_message()
        frame_b = reader.read_message()
        types = sorted([frame_a.type, frame_b.type])
        assert types == ["ack", "chat.send"]

        chat_msg = frame_a if frame_a.type == "chat.send" else frame_b
        ack_msg = frame_b if frame_a.type == "chat.send" else frame_a

        assert chat_msg.data["text"] == "# next ticket\n\nrun pytest -q"
        assert chat_msg.data["submit"] is True
        assert ack_msg.id == "ev1"
        assert ack_msg.data["handoff"] == "sent"
        assert ack_msg.data["chars"] == len("# next ticket\n\nrun pytest -q")

        assert len(captured) == 1
        assert captured[0]["chat"] == "cascade"
        assert captured[0]["reason"] == "user-stop"
        assert captured[0]["ide"] == "windsurf"

        plugin.close()


def test_session_ended_no_handoff_when_disabled(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``handoff=None`` (default) → just ack, no follow-up chat.send."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="vscode")
        plugin.sendall(
            Message(type="session.ended", id="ev1",
                    data={"chat": "x", "reason": ""}).encode()
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert msg.id == "ev1"
        assert msg.data.get("event") == "session.ended"
        _assert_no_more_data(plugin)
        plugin.close()


def test_session_ended_skipped_during_cooldown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session.ended right after a drive must be ignored by the handoff."""
    calls: list[dict] = []

    def fake_handoff(event: dict) -> str:
        calls.append(event)
        return "should not be typed"

    with _daemon(
        tmp_path, monkeypatch, handoff=fake_handoff, handoff_cooldown=10.0,
    ) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="windsurf")

        # Simulate the daemon having just typed.
        h.daemon._last_chat_send_at = time.monotonic()

        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x"}).encode()
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert msg.data["handoff"] == "skipped"
        assert "cooldown" in msg.data["reason"]
        assert calls == []
        plugin.close()


def test_session_started_event_just_acks(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with handoff enabled, session.started must NOT trigger a brief."""
    with _daemon(tmp_path, monkeypatch, handoff=lambda _e: "must not appear") as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="vscode")
        plugin.sendall(
            Message(type="session.started", id="ev1", data={"chat": "x"}).encode()
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert "handoff" not in msg.data
        _assert_no_more_data(plugin)
        plugin.close()


# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


def test_shutdown_stops_daemon(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Stop the daemon through its own socket and verify cleanup."""
    _patch_no_running_ides(monkeypatch)
    harness = _DaemonHarness(tmp_path)
    harness.start()
    try:
        reply = harness.client().shutdown()
        assert reply["ok"] is True
    finally:
        # Avoid harness.stop() double-stopping: just join the thread.
        if harness._thread is not None:
            harness._thread.join(timeout=2.0)
            assert not harness._thread.is_alive()
    assert not harness.sock_path.exists()
