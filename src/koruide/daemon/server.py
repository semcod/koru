from __future__ import annotations

import contextlib
import errno
import os
import selectors
import socket
import stat
import struct
import threading
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any, cast

from koruide.audit import AuditLog
from koruide.daemon.handlers import _default_handoff
from koruide.daemon.metadata import (
    build_daemon_metadata,
    daemon_metadata_path,
    remove_daemon_metadata,
    write_daemon_metadata,
)
from koruide.daemon.protocol import _Client, _peer_uid
from koruide.injector import Injector
from koruide.command_catalog_store import CommandCatalogStore
from koruide.command_telemetry import CommandTelemetry
from koruide.plugin_router import PluginRouter
from koruide.protocol import (
    MAX_LINE_BYTES,
    Message,
    ProtocolError,
    decode,
    error,
)
from koruide.socket import default_socket_path

# Type alias
HandoffBuilder = Callable[[dict[str, Any]], str]
_FRAME_HEADER = struct.Struct(">I")


from koru.env_flags import env_truthy as _env_truthy


def _verbose_io() -> bool:
    return _env_truthy("KORU_AUTOPILOT_VERBOSE")


class AutopilotDaemon:
    """Selector-based unix-socket broker."""

    def __init__(
        self,
        *,
        socket_path: Path | None = None,
        injector: Injector | None = None,
        log: Callable[[str], None] | None = None,
        handoff: HandoffBuilder | None = None,
        project: Path | None = None,
        enable_project_handoff: bool = True,
        handoff_cooldown: float = 2.0,
        audit: AuditLog | None = None,
    ) -> None:
        self.socket_path = socket_path or default_socket_path()
        self.injector = injector or Injector()
        self.project = project
        self.started_at = time.time()
        self.metadata_path = daemon_metadata_path(project, self.socket_path)
        self.log = log or (lambda _msg: None)
        self.audit = audit or AuditLog(enabled=False)
        if handoff is not None:
            self.handoff: HandoffBuilder | None = handoff
        elif project is not None and enable_project_handoff:
            self.handoff = _default_handoff(project)
        else:
            self.handoff = None
        self.handoff_cooldown = handoff_cooldown
        self._last_chat_send_at: float = 0.0
        self._sel = selectors.DefaultSelector()
        self._server: socket.socket | None = None
        self._clients: dict[int, _Client] = {}
        self._stop = threading.Event()
        self._lock = threading.Lock()
        self._plugin_router = PluginRouter(
            cast(dict[int, Any], self._clients),
            drop_client=cast(Callable[[Any], None], self._drop),
            log=self.log,
        )
        self._handlers = self._build_handler_table()
        self._plugin_rejection_log_state: dict[
            tuple[str, str | None, str | None], tuple[float, int]
        ] = {}
        self._plugin_rejections: list[dict[str, Any]] = []
        self._command_catalog_store = CommandCatalogStore(project)
        self._command_telemetry = CommandTelemetry(project)
        self._recent_dsl: list[str] = []

    # ----- lifecycle -----------------------------------------------------

    def start(self) -> None:
        """Bind the socket and register it with the selector."""
        path = self.socket_path
        if path.exists():
            try:
                path.unlink()
            except OSError as exc:
                raise RuntimeError(f"cannot remove stale socket {path}: {exc}") from exc
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.setblocking(False)
        srv.bind(str(path))
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        srv.listen(16)
        self._server = srv
        self._sel.register(srv, selectors.EVENT_READ, data="server")
        metadata = self.daemon_metadata()
        write_daemon_metadata(metadata, self.metadata_path)
        self.log(
            "koru autopilot daemon: listening on "
            f"{path} pid={metadata.get('pid')} version={metadata.get('version') or '-'} "
            f"sha={metadata.get('git_sha') or '-'} python={metadata.get('python_executable')}"
        )
        self.audit.record(
            "daemon_started",
            socket=str(path),
            handoff=self.handoff is not None,
        )

    def daemon_metadata(self) -> dict[str, Any]:
        return build_daemon_metadata(
            socket_path=self.socket_path,
            project=self.project,
            started_at=self.started_at,
        )

    def serve_forever(self) -> None:
        """Block until :meth:`stop` is called."""
        if self._server is None:
            self.start()
        try:
            while not self._stop.is_set():
                events = self._sel.select(timeout=0.5)
                for key, _mask in events:
                    if key.data == "server":
                        self._accept()
                    else:
                        self._on_readable(key.data)
        finally:
            self._shutdown()

    def stop(self) -> None:
        self._stop.set()

    def _shutdown(self) -> None:
        for client in list(self._clients.values()):
            self._drop(client)
        if self._server is not None:
            with contextlib.suppress(KeyError):
                self._sel.unregister(self._server)
            with contextlib.suppress(OSError):
                self._server.close()
            self._server = None
        with contextlib.suppress(OSError):
            self.socket_path.unlink()
        remove_daemon_metadata(self.metadata_path, pid=os.getpid())
        self.log("koru autopilot daemon: stopped")
        self.audit.record("daemon_stopped")
        self.audit.close()

    # ----- selector callbacks --------------------------------------------

    def _accept(self) -> None:
        assert self._server is not None
        try:
            conn, _ = self._server.accept()
        except OSError as exc:
            if exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK):
                return
            self.log(f"accept failed: {exc}")
            return
        peer_uid = _peer_uid(conn)
        if peer_uid is not None and peer_uid != os.getuid():
            self.log(f"reject peer uid={peer_uid} (daemon uid={os.getuid()})")
            conn.close()
            return
        conn.setblocking(False)
        client = _Client(sock=conn, addr=f"fd{conn.fileno()}")
        self._clients[conn.fileno()] = client
        self._sel.register(conn, selectors.EVENT_READ, data=client)
        if _verbose_io():
            self.log(f"client connected: {client.addr}")

    def _on_readable(self, client: _Client) -> None:
        try:
            chunk = client.sock.recv(4096)
        except OSError as exc:
            self.log(f"recv error from {client.addr}: {exc}")
            self._drop(client)
            return
        if not chunk:
            if _verbose_io():
                self.log(f"client disconnected: {client.addr}")
            self._drop(client)
            return
        client.buf.extend(chunk)
        if len(client.buf) > MAX_LINE_BYTES:
            self._send(client, error(None, "line too large").encode())
            self._drop(client)
            return
        while b"\n" in client.buf:
            line, _, rest = client.buf.partition(b"\n")
            client.buf = bytearray(rest)
            if not line.strip():
                continue
            try:
                msg = decode(bytes(line))
            except ProtocolError as exc:
                self._send(client, error(None, str(exc)).encode())
                continue
            self._dispatch(client, msg)

    # ----- dispatch ------------------------------------------------------

    def _dispatch(self, client: _Client, msg: Message) -> None:
        handler = self._handlers.get(msg.type)
        if handler is None:
            self._send(client, error(msg.id, f"unhandled type {msg.type!r}").encode())
            return
        try:
            handler(self, client, msg)
        except Exception as exc:  # pragma: no cover — defensive
            self.log(f"handler {msg.type} raised: {exc}")
            self._send(client, error(msg.id, f"internal error: {exc}").encode())

    def _send(self, client: _Client, payload: bytes) -> bool:
        # STARTER-242 telemetry: surface oversized envelopes before sendall.
        # The truncated-NDJSON crash on cycle #632 was a ~170 KB ack arriving
        # at the CLI without a trailing newline; logging the size here
        # narrows the suspect (plugin ack? OS-fallback relay? handoff?) and
        # gives us a concrete budget to enforce later.
        if len(payload) > 32 * 1024:
            head = payload[:120].decode("utf-8", errors="replace")
            self.log(
                f"send to {client.addr} oversized: bytes={len(payload)} "
                f"head={head!r}",
            )
        wire_payload = payload
        if client.role == "cli":
            wire_payload = _FRAME_HEADER.pack(len(payload)) + payload
        try:
            client.sock.sendall(wire_payload)
        except BrokenPipeError:
            if _verbose_io():
                self.log(f"send to {client.addr} skipped: peer already gone")
            self._drop(client)
            return False
        except OSError as exc:
            self.log(f"send to {client.addr} failed: {exc}")
            self._drop(client)
            return False
        return True

    def _drop(self, client: _Client) -> None:
        if client.role == "cli":
            for plugin in self._clients.values():
                pending = plugin.awaiting_plugin
                if pending is not None and pending[0] is client:
                    timer = getattr(plugin, "awaiting_plugin_timer", None)
                    if timer is not None:
                        with contextlib.suppress(Exception):
                            timer.cancel()
                    plugin.awaiting_plugin_timer = None
                    plugin.awaiting_plugin_info = None
                    plugin.awaiting_plugin = None
                    self.log(
                        "drive → plugin ack pending when CLI client disconnected; "
                        "treating future ack as late ack"
                    )
        fd = client.sock.fileno()
        if fd in self._clients:
            del self._clients[fd]
        with contextlib.suppress(KeyError, ValueError):
            self._sel.unregister(client.sock)
        with contextlib.suppress(OSError):
            client.sock.close()

    def _plugin_for(self, ide: str | None) -> _Client | None:
        return cast(_Client | None, self._plugin_router.plugin_for(ide, project=self.project))

    # ----- back-compat method proxies -----------------------------------
    #
    # The handlers below were methods on the monolithic ``AutopilotDaemon``
    # before the daemon package split. Tests (``test_autopilot_daemon.py``)
    # legitimately monkey-patch them on the instance — e.g.
    # ``monkeypatch.setattr(daemon, "_try_os_injector_drive", fake)`` — and
    # call ``daemon._log_rejected_plugin_connection(...)`` directly. Keeping
    # them as thin instance proxies lets the underlying logic stay in
    # :mod:`koruide.daemon.handlers` (top-level functions) without breaking
    # any tests or out-of-tree callers that still expect the legacy surface.

    def _try_os_injector_drive(
        self,
        target_id: str,
        text: str,
        submit: bool,
    ) -> dict[str, Any] | None:
        from koruide.daemon.handlers import _try_os_injector_drive as _impl
        return _impl(self, target_id, text, submit)

    def _log_rejected_plugin_connection(
        self,
        *,
        ide: str,
        plugin_version: str | None,
        expected_plugin_version: Any,
        message: str,
        plugin_build_sha: str | None = None,
        expected_plugin_build_sha: Any = None,
    ) -> None:
        from koruide.daemon.handlers import _log_rejected_plugin_connection as _impl
        _impl(
            self,
            ide=ide,
            plugin_version=plugin_version,
            expected_plugin_version=expected_plugin_version,
            plugin_build_sha=plugin_build_sha,
            expected_plugin_build_sha=expected_plugin_build_sha,
            message=message,
        )

    def _build_handler_table(
        self,
    ) -> dict[str, Callable[[AutopilotDaemon, _Client, Message], None]]:
        from koruide.daemon.handlers import (
            handle_ack,
            handle_console_log,
            handle_drive,
            handle_hello,
            handle_ping,
            handle_plugin_event,
            handle_shutdown,
            handle_status,
        )
        return {
            "drive": handle_drive,
            "hello": handle_hello,
            "status": handle_status,
            "ack": handle_ack,
            "session.started": handle_plugin_event,
            "session.ended": handle_plugin_event,
            "message.sent": handle_plugin_event,
            "message.received": handle_plugin_event,
            "chat.opened": handle_plugin_event,
            "status.error": handle_plugin_event,
            "shutdown": handle_shutdown,
            "ping": handle_ping,
            "console_log": handle_console_log,
        }
