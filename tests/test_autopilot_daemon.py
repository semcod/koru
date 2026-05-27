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

import json
import socket
import struct
import threading
import time
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import pytest

from koru.autopilot import ide as ide_mod
from koru.autopilot.client import AutopilotClient
from koru.autopilot.daemon import AutopilotDaemon
from koru.autopilot.ide import RunningIDE
from koru.autopilot.injector import InjectionResult, InjectorError
from koru.autopilot.os_injector import OsInjectorProfile
from koru.autopilot.protocol import Message, decode, hello
from koru.observability_writer import observability_event_store_path
from koruide import daemon as koruide_daemon_mod
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.plugin_version import EXPECTED_VSCODE_PLUGIN_VERSION

# ---------------------------------------------------------------------------
# Shared test plumbing
# ---------------------------------------------------------------------------


def _patch_no_running_ides(monkeypatch: pytest.MonkeyPatch) -> None:
    """Isolate daemon tests from the host IDE / OS-injector profile."""
    from koruide import os_injector as oi_mod

    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda **_: [])
    monkeypatch.setattr(ide_mod, "detect_running_ides_cached", lambda **_: [])
    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda **_k: None)
    monkeypatch.setattr(koruide_daemon_mod, "detect_running_ides", lambda **_: [])
    monkeypatch.setattr(oi_mod, "try_load_profile", lambda _tool_id, project=None: None)
    # Also patch detect_terminal_host_ide_id to avoid terminal host detection
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)


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

    @staticmethod
    def _decode_frame(buf: bytearray) -> Message | None:
        if not buf:
            return None
        # Legacy NDJSON.
        if buf[0] == ord("{"):
            idx = buf.find(b"\n")
            if idx < 0:
                return None
            line = bytes(buf[:idx])
            del buf[: idx + 1]
            return decode(line)
        # Length-prefixed daemon reply for CLI sockets.
        if len(buf) < 4:
            return None
        frame_len = struct.unpack(">I", bytes(buf[:4]))[0]
        total = 4 + frame_len
        if len(buf) < total:
            return None
        payload = bytes(buf[4:total])
        del buf[:total]
        return decode(payload)

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
        timeout = self.sock.gettimeout()
        if timeout is not None and timeout < 6.0:
            self.sock.settimeout(6.0)
        while True:
            decoded = self._decode_frame(self.buf)
            if decoded is not None:
                return decoded
            chunk = self.sock.recv(8192)
            if not chunk:
                break
            self.buf.extend(chunk)
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
        project: Path | None = None,
        enable_project_handoff: bool = True,
        logs: list[str] | None = None,
    ) -> None:
        self.sock_path = tmp_path / "autopilot.sock"
        self.injector = injector or _StubInjector()
        self.logs = logs
        log_kw: dict[str, Any] = {}
        if logs is not None:
            log_kw["log"] = logs.append
        self.daemon = AutopilotDaemon(
            socket_path=self.sock_path,
            injector=self.injector,
            handoff=handoff,
            handoff_cooldown=handoff_cooldown,
            project=project,
            enable_project_handoff=enable_project_handoff,
            **log_kw,
        )
        self._thread: threading.Thread | None = None

    def __enter__(self) -> _DaemonHarness:
        self.start()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.stop()

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
    project: Path | None = None,
    enable_project_handoff: bool = True,
    patch_ides: bool = True,
) -> Iterator[_DaemonHarness]:
    if patch_ides:
        _patch_no_running_ides(monkeypatch)
    monkeypatch.delenv("KORU_STRICT_PLUGIN_ACK", raising=False)
    monkeypatch.delenv("KORU_STRICT_PLUGIN_VERSION", raising=False)
    monkeypatch.delenv("KORU_PLUGIN_VERSION_POLICY", raising=False)
    harness = _DaemonHarness(
        tmp_path,
        injector=injector,
        handoff=handoff,
        handoff_cooldown=handoff_cooldown,
        project=project,
        enable_project_handoff=enable_project_handoff,
    )
    harness.start()
    try:
        yield harness
    finally:
        harness.stop()


def _connect_plugin(
    sock_path: Path,
    *,
    ide: str = "vscode",
    version: str | None = None,
    pid: int = 1,
    protocol_version: int | None = 1,
    capabilities: list[str] | None = None,
) -> tuple[socket.socket, _LineReader]:
    """Connect a fake plugin client. ``version`` defaults to the
    expected VSIX version so the strict version check the daemon now
    enforces does not reject the test plugin every time the project
    bumps ``EXPECTED_PLUGIN_VERSIONS``."""
    if version is None:
        version = EXPECTED_VSCODE_PLUGIN_VERSION
    """Open a plugin connection, send ``hello``, consume the ack."""
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.settimeout(6.0)
    sock.connect(str(sock_path))
    reader = _LineReader(sock)
    sock.sendall(
        hello(
            ide=ide,
            version=version,
            pid=pid,
            id="hello",
            protocol_version=protocol_version,
            capabilities=capabilities,
        ).encode()
    )
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


def test_ping_unknown_role_does_not_log_noise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logs: list[str] = []
    with _daemon(tmp_path, monkeypatch, patch_ides=True) as h:
        h.daemon._log = logs.append
        reply = h.client().request(Message(type="ping", id="p1"))
        assert reply.type == "ack"
        assert reply.data.get("pong") is True
    assert not any("ping from" in line and "role=unknown" in line for line in logs)


def test_is_running_true_when_daemon_alive(running_daemon) -> None:
    _, client, _ = running_daemon
    assert client.is_running() is True


def test_drive_falls_back_to_injector_when_no_plugin(running_daemon) -> None:
    _, client, injector = running_daemon
    reply = client.drive("hello there", submit=True, ide="auto")
    assert reply["ok"] is True
    assert reply["backend"] == "stub"
    assert injector.calls == [{"text": "hello there", "ide": "default", "submit": True}]


def test_drive_require_plugin_blocks_keyboard_fallback(running_daemon) -> None:
    _, client, injector = running_daemon
    reply = client.drive("hello there", submit=True, ide="windsurf", require_plugin=True)
    assert reply["ok"] is False
    assert reply["type"] == "error"
    assert "no connected autopilot plugin" in reply["message"]
    assert "keyboard fallback disabled" in reply["message"]
    assert injector.calls == []


def test_drive_reports_injector_failure(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    with _daemon(tmp_path, monkeypatch, injector=_StubInjector(fail=True)) as h:
        reply = h.client().drive("hi")
        assert reply["type"] == "error"
        assert "stub failure" in reply["message"]


def test_drive_uses_os_injector_when_profile_available(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koruide import os_injector as koruide_oi

    # Daemon imports koruide.os_injector at request time; isolate from host IDE env.
    monkeypatch.setenv("XDG_SESSION_TYPE", "x11")
    monkeypatch.delenv("KORU_OS_INJECTOR", raising=False)
    monkeypatch.delenv("CURSOR_AGENT", raising=False)
    monkeypatch.delenv("CURSOR_CLI", raising=False)
    monkeypatch.delenv("VSCODE_PID", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    ide_mod.clear_detect_cache()

    repo = tmp_path / "repo"
    repo.mkdir()
    fake = RunningIDE(id="cursor", label="Cursor", pid=1, exe="/opt/Cursor")

    def running(**_):
        return [fake]

    monkeypatch.setattr(ide_mod, "detect_running_ides", running)
    monkeypatch.setattr(ide_mod, "detect_running_ides_cached", running)
    monkeypatch.setattr(koruide_daemon_mod, "detect_running_ides", running)
    monkeypatch.setattr(ide_mod, "detect_focused_ide_id", lambda **_k: None)
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)
    monkeypatch.setattr(
        koruide_oi.shutil,
        "which",
        lambda name: "/bin/xdotool" if name == "xdotool" else None,
    )

    prof = OsInjectorProfile(tool_id="cursor", chat_x=2, chat_y=3)

    def fake_try_load(tool_id: str, project=None):
        assert tool_id == "cursor"
        assert project == repo
        return prof

    calls: list[dict[str, Any]] = []

    def fake_inject(*, profile, text, submit, dry_run, _log=None):
        calls.append({"text": text, "submit": submit, "dry_run": dry_run})
        return {
            "ok": True,
            "backend": "os_injector",
            "tool_id": profile.tool_id,
            "submitted": submit,
            "dry_run": dry_run,
        }

    monkeypatch.setattr(koruide_oi, "try_load_profile", fake_try_load)
    monkeypatch.setattr(koruide_oi, "inject_with_profile", fake_inject)

    with _daemon(tmp_path, monkeypatch, project=repo, patch_ides=False) as h:
        reply = h.client().drive("hello", submit=False, ide="auto")
    assert reply.get("type") == "ack", reply
    assert reply["ok"] is True
    assert reply["backend"] == "os_injector"
    assert reply["tool_id"] == "cursor"
    assert h.injector.calls == []
    assert calls == [{"text": "hello", "submit": False, "dry_run": False}]


def test_drive_os_injector_skipped_when_env_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setenv("KORU_OS_INJECTOR", "0")
    fake = RunningIDE(id="cursor", label="Cursor", pid=1, exe="/opt/Cursor")
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(koruide_daemon_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)
    monkeypatch.setattr(
        oi_mod.shutil, "which", lambda name: "/bin/xdotool" if name == "xdotool" else None
    )

    tried = {"n": 0}

    def counted_try_load(*_a, **_k):
        tried["n"] += 1
        return OsInjectorProfile(tool_id="cursor", chat_x=0, chat_y=0)


    with _daemon(tmp_path, monkeypatch, patch_ides=False) as h:
        reply = h.client().drive("x", ide="auto")
    assert reply["backend"] == "stub"
    assert tried["n"] == 0


def test_drive_os_injector_forced_without_profile_falls_back_to_keyboard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.setenv("KORU_OS_INJECTOR", "1")
    fake = RunningIDE(id="cursor", label="Cursor", pid=1, exe="/opt/Cursor")
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(koruide_daemon_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(
        oi_mod.shutil, "which", lambda name: "/bin/xdotool" if name == "xdotool" else None
    )
    monkeypatch.setattr(oi_mod, "try_load_profile", lambda *a, **k: None)

    with _daemon(tmp_path, monkeypatch, patch_ides=False) as h:
        reply = h.client().drive("y", ide="auto")
    assert reply["backend"] == "stub"
    assert h.injector.calls == [{"text": "y", "ide": "cursor", "submit": True}]


def test_drive_os_injector_failure_falls_back_to_keyboard(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from koru.autopilot import os_injector as oi_mod

    monkeypatch.delenv("KORU_AUTOPILOT_INSTANCE", raising=False)
    monkeypatch.delenv("KORU_AUTOPILOT_IDE", raising=False)
    monkeypatch.setattr(oi_mod, "try_load_profile", lambda *a, **k: None)
    fake = RunningIDE(id="cursor", label="Cursor", pid=1, exe="/opt/Cursor")
    monkeypatch.setattr(ide_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(koruide_daemon_mod, "detect_running_ides", lambda **_: [fake])
    monkeypatch.setattr(ide_mod, "detect_terminal_host_ide_id", lambda **_k: None)

    with _daemon(tmp_path, monkeypatch, patch_ides=False) as h:
        monkeypatch.setattr(
            h.daemon,
            "_try_os_injector_drive",
            lambda *_args, **_kwargs: (_ for _ in ()).throw(
                InjectorError("xdotool failed: no DISPLAY"),
            ),
        )
        reply = h.client().drive("z", ide="auto")

    assert reply["backend"] == "stub"
    assert h.injector.calls == [{"text": "z", "ide": "cursor", "submit": True}]


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
    assert info["daemon"]["pid"]
    assert info["daemon"]["python_executable"]
    assert info["daemon_metadata"]["schema"] == "koru.autopilot.daemon.v1"
    assert info["plugins"] == []


def test_daemon_writes_project_metadata_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    project = tmp_path / "project"
    project.mkdir()
    with _daemon(tmp_path, monkeypatch, project=project) as h:
        metadata_path = project / ".planfile" / ".koru" / "autopilot.daemon.json"
        assert h.daemon.metadata_path == metadata_path
        assert metadata_path.exists()
        payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        assert payload["pid"]
        assert payload["socket"] == str(h.sock_path)
        assert payload["project"] == str(project.resolve())
    assert not metadata_path.exists()


def test_status_reports_plugin_console_logs(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    koruide_daemon_mod.clear_console_logs()
    try:
        with _daemon(tmp_path, monkeypatch) as h:
            plugin, plugin_reader = _connect_plugin(
                h.sock_path,
                ide="windsurf",
                version="0.1.45",
                pid=42,
            )
            plugin.sendall(
                Message(
                    type="console_log",
                    id="console-log",
                    data={
                        "message": "WINDSURF_FASTPATH_EXECUTE_SEND_OK",
                        "data": {"attempt": 1},
                        "timestamp": "2026-05-22T12:00:00Z",
                    },
                ).encode()
            )
            plugin.sendall(
                Message(type="message.sent", id="flush", data={"chat": "default"}).encode()
            )
            assert plugin_reader.read_message().type == "ack"

            info = h.client().status()
            logs = info.get("console_logs")
            assert isinstance(logs, list)
            assert logs[-1]["message"] == "WINDSURF_FASTPATH_EXECUTE_SEND_OK"
            assert logs[-1]["data"] == {"attempt": 1}
            assert logs[-1]["ide"] == "windsurf"
            assert logs[-1]["version"] == "0.1.45"
            plugin.close()
    finally:
        koruide_daemon_mod.clear_console_logs()


def test_console_log_surfaces_live_dsl_lines(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    logs: list[str] = []
    with _daemon(tmp_path, monkeypatch) as h:
        h.daemon.log = logs.append
        plugin, plugin_reader = _connect_plugin(
            h.sock_path,
            ide="vscode",
            version="0.2.0",
            pid=42,
        )
        plugin.sendall(
            Message(
                type="console_log",
                id="console-log",
                data={
                    "message": "[DSL-LIVE] #001 act=focus_open route=plugin ok=true",
                    "timestamp": "2026-05-22T12:00:00Z",
                },
            ).encode()
        )
        plugin.sendall(
            Message(type="message.sent", id="flush", data={"chat": "default"}).encode()
        )
        assert plugin_reader.read_message().type == "ack"
        plugin.close()

    assert "[DSL] #001 act=focus_open route=plugin ok=true via=plugin ide=vscode" in logs


def test_accept_rejects_foreign_peer_uid(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """R11: enforce same-UID policy on every accept via SO_PEERCRED."""
    _patch_no_running_ides(monkeypatch)
    daemon_uid = 1000
    foreign_uid = 1001
    monkeypatch.setattr(koruide_daemon_mod.os, "getuid", lambda: daemon_uid)
    monkeypatch.setattr(koruide_daemon_mod, "_peer_uid", lambda _sock: foreign_uid)

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
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d1",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("delivered") is True
        assert cli_reply.data.get("backend") == "plugin"

        # Injector must NOT have been invoked — plugin path took over.
        assert h.injector.calls == []
        plugin.close()
        cli.close()


def test_plugin_drive_routes_alias_to_canonical_plugin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Direct daemon clients can use IDE aliases and still hit the plugin lane."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="code", pid=42)
        plugin.settimeout(6.0)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-alias",
                data={"text": "hi", "ide": "VS-Code", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        assert h.daemon._plugin_for("vscode") is not None
        assert h.daemon._plugin_for("code") is not None

        plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("backend") == "plugin"
        assert h.injector.calls == []
        plugin.close()
        cli.close()


def test_plugin_hello_rejects_missing_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _daemon(tmp_path, monkeypatch) as h:
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(h.sock_path))
        reader = _LineReader(plugin)
        plugin.sendall(hello(ide="vscode", version="0.1.11", pid=42, id="hello-old").encode())
        reply = reader.read_message()
        assert reply.type == "error"
        assert "plugin protocol missing" in reply.data.get("message", "")
        assert h.injector.calls == []
        plugin.close()


def test_strict_plugin_version_blocks_stale_plugin_with_compatible_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.15",
    )

    with _daemon(tmp_path, monkeypatch) as h:
        monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
        plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        plugin.settimeout(2.0)
        plugin.connect(str(h.sock_path))
        plugin_reader = _LineReader(plugin)
        plugin.sendall(
            hello(
                ide="vscode",
                version="0.1.14",
                pid=42,
                id="hello-stale-compatible",
                protocol_version=1,
                capabilities=["chat.submit"],
            ).encode(),
        )

        reply = plugin_reader.read_message()
        assert reply.type == "error"
        assert reply.data.get("ok") is False
        assert "version mismatch" in reply.data.get("message", "")
        plugin.close()


def test_protocol_policy_allows_stale_plugin_with_compatible_protocol(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.15",
    )

    with _daemon(tmp_path, monkeypatch) as h:
        monkeypatch.setenv("KORU_PLUGIN_VERSION_POLICY", "protocol")
        plugin, plugin_reader = _connect_plugin(
            h.sock_path,
            ide="vscode",
            version="0.1.14",
            pid=42,
            protocol_version=1,
            capabilities=["chat.submit"],
        )

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(5.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-protocol-policy",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode(),
        )
        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("plugin_protocol_compatible") is True
        assert cli_reply.data.get("plugin_version_policy") == "protocol"
        plugin.close()
        cli.close()


def test_strict_plugin_hello_rejects_stale_without_evicting_current(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(
        DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.13",
    )

    with _daemon(tmp_path, monkeypatch) as h:
        current_plugin, current_reader = _connect_plugin(
            h.sock_path,
            ide="vscode",
            version="0.1.13",
            pid=42,
        )

        stale_plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale_plugin.settimeout(2.0)
        stale_plugin.connect(str(h.sock_path))
        stale_reader = _LineReader(stale_plugin)
        stale_plugin.sendall(
            hello(ide="vscode", version="0.1.11", pid=41, id="hello-stale").encode(),
        )

        stale_reply = stale_reader.read_message()
        assert stale_reply.type == "error"
        assert "plugin protocol missing" in stale_reply.data.get("message", "")

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-current-plugin",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = current_reader.read_message()
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        current_plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("backend") == "plugin"

        current_plugin.close()
        stale_plugin.close()
        cli.close()


def test_repeated_stale_plugin_hello_rejections_are_log_throttled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setenv("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", "30")
    monkeypatch.setattr(
        DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.13",
    )
    logs: list[str] = []
    ticks = iter([10.0, 12.0, 14.0, 45.0])
    monkeypatch.setattr(koruide_daemon_mod.time, "monotonic", lambda: next(ticks))

    harness = _DaemonHarness(tmp_path)
    harness.daemon.log = logs.append
    harness.daemon._plugin_router._log = logs.append
    _patch_no_running_ides(monkeypatch)
    harness.start()
    try:
        for _idx in range(4):
            stale_plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            stale_plugin.settimeout(2.0)
            stale_plugin.connect(str(harness.sock_path))
            stale_reader = _LineReader(stale_plugin)
            stale_plugin.sendall(
                hello(ide="vscode", version="0.1.11", pid=41, id="hello-stale").encode(),
            )
            assert stale_reader.read_message().type == "error"
            stale_plugin.close()
    finally:
        harness.stop()

    rejection_logs = [line for line in logs if line.startswith("rejecting plugin connection")]
    assert len(rejection_logs) == 2
    assert "suppressed 2 repeated reconnects" in rejection_logs[1]


def test_rejected_plugin_log_default_interval_is_quiet(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", raising=False)
    logs: list[str] = []
    ticks = iter([10.0, 45.0, 315.0])
    monkeypatch.setattr(koruide_daemon_mod.time, "monotonic", lambda: next(ticks))
    daemon = AutopilotDaemon(
        socket_path=tmp_path / "autopilot.sock",
        injector=_StubInjector(),
        log=logs.append,
    )

    for _ in range(3):
        daemon._log_rejected_plugin_connection(
            ide="vscode",
            plugin_version="0.1.11",
            expected_plugin_version="0.1.14",
            message="connected autopilot plugin version mismatch",
        )

    rejection_logs = [line for line in logs if line.startswith("rejecting plugin connection")]
    assert len(rejection_logs) == 2
    assert "suppressed 1 repeated reconnects" in rejection_logs[1]


def test_rejected_plugin_log_names_actual_ide_for_reload_action(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", "5")
    logs: list[str] = []
    daemon = AutopilotDaemon(
        socket_path=tmp_path / "autopilot.sock",
        injector=_StubInjector(),
        log=logs.append,
    )

    daemon._log_rejected_plugin_connection(
        ide="vscodium",
        plugin_version="0.1.72",
        expected_plugin_version="0.1.73",
        message="connected autopilot plugin version mismatch",
    )

    reload_logs = [line for line in logs if "Developer: Reload Window" in line]
    assert reload_logs
    assert "Action: in VSCodium run `Developer: Reload Window`" in reload_logs[0]
    assert "Action: in Cursor run" not in reload_logs[0]


def test_status_reports_rejected_plugin_versions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_STRICT_PLUGIN_VERSION", "1")
    monkeypatch.setattr(
        DriveOrchestrator,
        "expected_plugin_version",
        lambda _plugin_ide: "0.1.13",
    )

    with _daemon(tmp_path, monkeypatch) as h:
        stale_plugin = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        stale_plugin.settimeout(2.0)
        stale_plugin.connect(str(h.sock_path))
        stale_reader = _LineReader(stale_plugin)
        stale_plugin.sendall(
            hello(ide="vscode", version="0.1.11", pid=41, id="hello-stale").encode(),
        )
        assert stale_reader.read_message().type == "error"
        stale_plugin.close()

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(Message(type="status", id="status").encode())

        reply = cli_reader.read_message()
        rejected = reply.data.get("rejected_plugins", [])
        assert rejected
        assert rejected[0]["ide"] == "vscode"
        assert rejected[0]["version"] == "0.1.11"
        assert rejected[0]["expected_version"] == "0.1.13"
        cli.close()


def test_message_sent_event_completes_pending_drive_without_plugin_ack(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If plugin emits message.sent but no chat.send ack, CLI drive should still complete."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)
        plugin.settimeout(6.0)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-message-sent",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="message.sent",
                data={"chat": "default", "text": "hi", "length": 2},
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("backend") == "plugin"
        assert cli_reply.data.get("event") == "message.sent"
        assert cli_reply.data.get("delivered") is True

        assert h.injector.calls == []
        plugin.close()
        cli.close()


def test_message_sent_event_does_not_complete_strict_ack_drive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Strict ACK mode waits for the full chat.send ack, not the telemetry event."""
    with _daemon(tmp_path, monkeypatch) as h:
        monkeypatch.setenv("KORU_STRICT_PLUGIN_ACK", "1")
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)
        plugin.settimeout(6.0)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-message-sent-strict",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="message.sent",
                data={"chat": "default", "text": "hi", "length": 2},
            ).encode(),
        )
        cli.settimeout(0.2)
        with pytest.raises(TimeoutError):
            cli_reader.read_message()
        cli.settimeout(6.0)


def test_vscodium_message_sent_event_completes_after_submit_unverified_ack_grace(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """VSCodium may emit ``message.sent`` shortly after an untrusted submit ack."""
    monkeypatch.setenv("KORU_STRICT_PLUGIN_ACK", "1")
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(
            h.sock_path,
            ide="vscodium",
            pid=42,
            capabilities=[
                "ide.commands",
                "chat.focus",
                "chat.paste",
                "chat.submit",
                "chat.events",
            ],
        )
        plugin.settimeout(6.0)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-vscodium-message-sent",
                data={"text": "hi", "ide": "vscodium", "submit": True, "require_plugin": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="ack",
                id="d-vscodium-message-sent",
                data={
                    "ok": True,
                    "delivered": True,
                    "opened": True,
                    "submitted": True,
                    "winning_focus_open": (
                        "workbench.action.chat.focusInput+workbench.action.chat.focusInput"
                    ),
                    "winning_paste": "editor.action.clipboardPasteAction",
                    "winning_submit": "workbench.action.chat.submit",
                    "operation_trace": [
                        {
                            "op": "submit",
                            "route": "accepted",
                            "ok": True,
                            "detail": {"requireEmptyAfterSubmit": False},
                        },
                        {"op": "submit_verify", "route": "sentinel-clipboard", "ok": True},
                    ],
                },
            ).encode(),
        )
        plugin.sendall(
            Message(
                type="message.sent",
                data={"chat": "default", "text": "hi", "length": 2},
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("event") == "message.sent"
        assert cli_reply.data.get("verification") == "event_only"
        assert cli_reply.data.get("intent_status") == "fulfilled"

        plugin.close()
        cli.close()
        cli.close()


def test_message_sent_from_other_plugin_does_not_complete_pending_drive(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only the plugin owning pending drive may complete CLI ack."""
    monkeypatch.setenv("KORU_STRICT_PLUGIN_ACK", "1")
    with _daemon(tmp_path, monkeypatch) as h:
        vscode_plugin, vscode_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)
        cursor_plugin, cursor_reader = _connect_plugin(h.sock_path, ide="cursor", pid=43)
        vscode_plugin.settimeout(6.0)
        cursor_plugin.settimeout(6.0)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(6.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-other-plugin-event",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = vscode_reader.read_message()
        assert forwarded.type == "chat.send"

        cursor_plugin.sendall(
            Message(type="message.sent", data={"chat": "default", "text": "x"}).encode(),
        )
        cursor_ack = cursor_reader.read_message()
        assert cursor_ack.type == "ack"

        cli.settimeout(0.25)
        with pytest.raises(TimeoutError):
            cli_reader.read_message()
        cli.settimeout(6.0)

        vscode_plugin.sendall(
            Message(
                type="ack",
                id=forwarded.id,
                data={
                    "ok": True,
                    "delivered": True,
                    "opened": True,
                    "submitted": True,
                    "winning_focus_open": "workbench.action.chat.open",
                    "winning_paste": "editor.action.clipboardPasteAction",
                    "winning_submit": "workbench.action.chat.submit",
                },
            ).encode(),
        )
        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("verification") == "strict"

        vscode_plugin.close()
        cursor_plugin.close()
        cli.close()


def test_cli_client_still_connected_detects_peer_eof() -> None:
    """A still-registered CLI fd can already be half-closed by the peer."""
    from koruide.daemon.handlers import _cli_client_still_connected
    from koruide.daemon.protocol import _Client

    daemon_sock, peer_sock = socket.socketpair()
    daemon_sock.setblocking(False)
    client = _Client(sock=daemon_sock, addr="fd-test", role="cli")
    daemon = type("Daemon", (), {"_clients": {daemon_sock.fileno(): client}})()

    try:
        assert _cli_client_still_connected(daemon, client) is True
        peer_sock.close()
        assert _cli_client_still_connected(daemon, client) is False
    finally:
        daemon_sock.close()


def test_newer_plugin_connection_replaces_stale_same_ide_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If the same IDE reconnects, the daemon should use the newest plugin fd."""
    with _daemon(tmp_path, monkeypatch) as h:
        stale_plugin, _stale_reader = _connect_plugin(h.sock_path, ide="vscode", pid=41)
        fresh_plugin, fresh_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)
        fresh_plugin.settimeout(5.0)

        # The new hello should evict the stale client so it no longer receives traffic.
        stale_plugin.settimeout(0.2)
        stale_read = stale_plugin.recv(1)
        assert stale_read == b""

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(5.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-fresh-plugin",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = fresh_reader.read_message()
        assert forwarded.type == "chat.send"
        assert forwarded.data["text"] == "hi"
        fresh_plugin.sendall(
            Message(type="ack", id=forwarded.id, data={"ok": True, "delivered": True}).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("backend") == "plugin"

        fresh_plugin.close()
        stale_plugin.close()
        cli.close()


def test_visible_typing_prefers_keyboard_even_when_plugin_connected(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_VISIBLE_TYPING", "1")
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-visible",
                data={"text": "visible hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("backend") == "stub"
        assert h.injector.calls == [{"text": "visible hi", "ide": "vscode", "submit": True}]
        _assert_no_more_data(plugin)
        plugin.close()
        cli.close()


def test_plugin_ack_with_shutdown_info_is_relayed(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plugin ACK metadata (including ``shutdown``) must be preserved for CLI."""
    with _daemon(tmp_path, monkeypatch, project=tmp_path) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-shutdown",
                data={"text": "hi", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="ack",
                id=forwarded.id,
                data={"ok": True, "delivered": True, "shutdown": True},
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is True
        assert cli_reply.data.get("delivered") is True
        assert cli_reply.data.get("shutdown") is True
        assert cli_reply.data.get("backend") == "plugin"

        raw_events = observability_event_store_path(tmp_path).read_text(encoding="utf-8")
        rows = [json.loads(raw) for raw in raw_events.splitlines()]
        commands = [
            row["payload"]["data"]
            for row in rows
            if row["event_type"] == "control.command"
        ]
        assert commands[0]["surface"] == "ide_chat"
        assert commands[0]["operation"] == "chat.send"
        assert commands[0]["target"] == "vscode"
        assert commands[0]["args"]["text"] == "hi"
        assert commands[0]["replayable"] is True

        assert h.injector.calls == []
        plugin.close()
        cli.close()


def test_plugin_ack_submit_failure_does_not_cross_fallback_for_plugin_ide(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Plugin-socket IDEs must not cross into keyboard fallback after plugin ack."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)

        def fake_os_fallback(_ide: str, _text: str, submit: bool):
            return {
                "ok": True,
                "backend": "os_injector",
                "submitted": submit,
            }

        monkeypatch.setattr(h.daemon, "_try_os_injector_drive", fake_os_fallback)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-submit-fail",
                data={"text": "continue", "ide": "vscode", "submit": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="ack",
                id=forwarded.id,
                data={
                    "ok": False,
                    "delivered": False,
                    "submitted": False,
                    "message": "chat opened and text injected, but submit command failed",
                },
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is False
        assert cli_reply.data.get("submitted") is False
        assert cli_reply.data.get("os_fallback") is None
        assert h.injector.calls == []

        plugin.close()
        cli.close()


def test_plugin_ack_failure_skips_os_fallback_if_require_plugin(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When require_plugin=True, daemon should skip os-injector fallback even on plugin fail."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, plugin_reader = _connect_plugin(h.sock_path, ide="vscode", pid=42)

        def fake_os_fallback(_ide: str, _text: str, submit: bool):
            return {
                "ok": True,
                "backend": "os_injector",
                "submitted": submit,
            }

        monkeypatch.setattr(h.daemon, "_try_os_injector_drive", fake_os_fallback)

        cli = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        cli.settimeout(2.0)
        cli.connect(str(h.sock_path))
        cli_reader = _LineReader(cli)
        cli.sendall(
            Message(
                type="drive",
                id="d-require-plugin",
                data={"text": "continue", "ide": "vscode", "submit": True, "require_plugin": True},
            ).encode(),
        )

        forwarded = plugin_reader.read_message()
        assert forwarded.type == "chat.send"
        plugin.sendall(
            Message(
                type="ack",
                id=forwarded.id,
                data={
                    "ok": False,
                    "delivered": False,
                    "submitted": False,
                    "message": "some plugin error",
                },
            ).encode(),
        )

        cli_reply = cli_reader.read_message()
        assert cli_reply.type == "ack"
        assert cli_reply.data.get("ok") is False
        assert cli_reply.data.get("os_fallback") is None

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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[dict] = []

    def fake_handoff(event: dict) -> str:
        captured.append(event)
        return "# next ticket\n\nrun pytest -q"

    with _daemon(tmp_path, monkeypatch, handoff=fake_handoff) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="windsurf", pid=42)
        plugin.sendall(
            Message(
                type="session.ended",
                id="ev1",
                data={"chat": "cascade", "reason": "user-stop"},
            ).encode(),
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
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """``handoff=None`` (default) → just ack, no follow-up chat.send."""
    with _daemon(tmp_path, monkeypatch) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="vscode")
        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x", "reason": ""}).encode(),
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert msg.id == "ev1"
        assert msg.data.get("event") == "session.ended"
        _assert_no_more_data(plugin)
        plugin.close()


def test_session_ended_no_project_handoff_when_disabled(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    with _daemon(
        tmp_path,
        monkeypatch,
        project=tmp_path,
        enable_project_handoff=False,
    ) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="cursor")
        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x"}).encode(),
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert msg.id == "ev1"
        assert msg.data.get("event") == "session.ended"
        assert "handoff" not in msg.data
        _assert_no_more_data(plugin)
        plugin.close()


def test_session_ended_skipped_during_cooldown(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """A session.ended right after a drive must be ignored by the handoff."""
    calls: list[dict] = []

    def fake_handoff(event: dict) -> str:
        calls.append(event)
        return "should not be typed"

    with _daemon(
        tmp_path,
        monkeypatch,
        handoff=fake_handoff,
        handoff_cooldown=10.0,
    ) as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="windsurf")

        # Simulate the daemon having just typed.
        h.daemon._last_chat_send_at = time.monotonic()

        plugin.sendall(
            Message(type="session.ended", id="ev1", data={"chat": "x"}).encode(),
        )
        msg = reader.read_message()
        assert msg.type == "ack"
        assert msg.data["handoff"] == "skipped"
        assert "cooldown" in msg.data["reason"]
        assert calls == []
        plugin.close()


def test_session_started_event_just_acks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Even with handoff enabled, session.started must NOT trigger a brief."""
    with _daemon(tmp_path, monkeypatch, handoff=lambda _e: "must not appear") as h:
        plugin, reader = _connect_plugin(h.sock_path, ide="vscode")
        plugin.sendall(
            Message(type="session.started", id="ev1", data={"chat": "x"}).encode(),
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


# ---------------------------------------------------------------------------
# Daemon log verbosity gate (R8)
# ---------------------------------------------------------------------------


def test_verbose_io_defaults_to_false(monkeypatch: pytest.MonkeyPatch) -> None:
    """Without ``KORU_AUTOPILOT_VERBOSE`` the daemon must hide per-fd events."""
    monkeypatch.delenv("KORU_AUTOPILOT_VERBOSE", raising=False)
    assert koruide_daemon_mod._verbose_io() is False


@pytest.mark.parametrize("value", ["1", "true", "yes", "on", "TRUE"])
def test_verbose_io_opt_in(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_VERBOSE", value)
    assert koruide_daemon_mod._verbose_io() is True


@pytest.mark.parametrize("value", ["0", "false", "", "off"])
def test_verbose_io_opt_out(monkeypatch: pytest.MonkeyPatch, value: str) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_VERBOSE", value)
    assert koruide_daemon_mod._verbose_io() is False


def test_connect_disconnect_silent_by_default(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Regression for ``koru auto`` log flood (``client connected: fd5`` x100).

    Dashboard / MCP / WUP probes connect to the daemon every second. The
    daemon used to log ``client connected`` + ``client disconnected`` for
    each probe, drowning the autonomous log. With the verbose gate off
    (default), no such lines should be emitted.
    """
    monkeypatch.delenv("KORU_AUTOPILOT_VERBOSE", raising=False)
    _patch_no_running_ides(monkeypatch)
    logs: list[str] = []

    with _DaemonHarness(tmp_path, logs=logs) as harness:
        for _ in range(3):
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
                s.settimeout(2.0)
                s.connect(str(harness.sock_path))
            time.sleep(0.05)
        time.sleep(0.2)

    assert not any("client connected" in line for line in logs), logs
    assert not any("client disconnected" in line for line in logs), logs


def test_connect_disconnect_logged_when_verbose(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("KORU_AUTOPILOT_VERBOSE", "1")
    _patch_no_running_ides(monkeypatch)
    logs: list[str] = []

    with _DaemonHarness(tmp_path, logs=logs) as harness:
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as s:
            s.settimeout(2.0)
            s.connect(str(harness.sock_path))
        time.sleep(0.2)

    assert any("client connected" in line for line in logs), logs
    assert any("client disconnected" in line for line in logs), logs


def test_cap_ack_info_for_cli_strips_oversized_fields() -> None:
    """STARTER-242: relay ack info must stay under the CLI wire budget."""
    from koruide.daemon.handlers import _MAX_RELAY_ACK_INFO_BYTES, _cap_ack_info_for_cli

    huge = "x" * 100_000
    info = {
        "verification": "strict",
        "winning_focus_open": "composer.showComposer",
        "diagnostics": {
            "rejected": [{"cmd": "a", "before": {"text": huge}, "after": {"text": huge}}],
        },
        "operation_trace": [{"op": "paste", "route": "x", "ok": True, "detail": {"text": huge}}],
    }
    capped = _cap_ack_info_for_cli(info)
    import json

    size = len(json.dumps(capped, separators=(",", ":")).encode("utf-8"))
    assert size <= _MAX_RELAY_ACK_INFO_BYTES
    assert "diagnostics" not in capped or capped.get("payload_trimmed")
