"""Unix-socket daemon that brokers between IDE plugins and koru clients.

Connections come from two roles:

* **Plugins** open one long-lived connection, send ``hello``, and
  then push lifecycle events (``session.started`` / ``session.ended``).
  The daemon can also send them ``chat.send`` to inject text via the
  IDE's own API (preferred path).
* **CLI clients** open a short-lived connection per command, send a
  single message (``drive`` / ``status`` / ``shutdown``), read one
  response, and disconnect.

When ``drive`` arrives:

1. If a plugin is connected for the requested IDE → forward as
   ``chat.send`` and relay the plugin's ack.
2. Otherwise → fall back to :class:`Injector` (keyboard sim).
3. Always log the event so the user can audit what was typed.

The daemon is intentionally single-threaded and selector-based. We
don't need throughput; we need predictability and a tiny footprint.
"""

from __future__ import annotations

import errno
import os
import selectors
import socket
import stat
import struct
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from . import default_socket_path
from .ide import detect_running_ides, pick_target
from .injector import Injector, InjectorError
from .protocol import (
    MAX_LINE_BYTES,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    error,
)

# Type alias: a HandoffBuilder takes the ended-session metadata and
# returns the text to type back into the chat (typically the koru
# markdown brief). Returning ``""`` cancels the handoff.
HandoffBuilder = Callable[[dict[str, Any]], str]


def _default_handoff(project: Path) -> HandoffBuilder:
    """Build the canonical koru brief for ``project`` on demand.

    Imported lazily to keep ``koru.autopilot`` importable without
    pulling in the heavy ``context`` module during ``koru autopilot
    doctor`` / ``ide-list`` smoke tests.
    """

    def _build(_event: dict[str, Any]) -> str:
        from ..context import build_context, render_markdown_handoff

        try:
            ctx = build_context(project=project)
        except Exception as exc:  # pragma: no cover — defensive
            return f"koru autopilot: failed to build brief: {exc}"
        return render_markdown_handoff(ctx)

    return _build


# SO_PEERCRED returns ``struct ucred { pid_t; uid_t; gid_t; }`` — three
# 32-bit little-endian ints on Linux.
_UCRED_STRUCT = struct.Struct("3i")


def _peer_uid(sock: socket.socket) -> int | None:
    try:
        raw = sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, _UCRED_STRUCT.size)
    except (OSError, AttributeError):
        return None
    try:
        _pid, uid, _gid = _UCRED_STRUCT.unpack(raw)
    except struct.error:
        return None
    return uid


@dataclass
class _Client:
    """In-memory state for one connected socket."""

    sock: socket.socket
    addr: str
    buf: bytearray = field(default_factory=bytearray)
    role: str = "unknown"  # "plugin" | "cli" | "unknown"
    ide: str | None = None  # set when role == "plugin"
    # Pending CLI ack: when a CLI sends ``drive`` and we forward to a
    # plugin, we remember the CLI socket so we can reply after the
    # plugin acks.
    awaiting_plugin: tuple["_Client", str] | None = None


class AutopilotDaemon:
    """Selector-based unix-socket broker.

    Parameters
    ----------
    socket_path:
        Where to bind. Defaults to :func:`default_socket_path`.
    injector:
        Optional pre-built :class:`Injector`. Defaults to a fresh one.
    log:
        Sink for human-readable events. Defaults to a no-op; the CLI
        wires this to ``print``.
    """

    def __init__(
        self,
        *,
        socket_path: Path | None = None,
        injector: Injector | None = None,
        log: Callable[[str], None] | None = None,
        handoff: HandoffBuilder | None = None,
        project: Path | None = None,
        handoff_cooldown: float = 2.0,
    ) -> None:
        self.socket_path = socket_path or default_socket_path()
        self.injector = injector or Injector()
        self.log = log or (lambda _msg: None)
        # Handoff is opt-in: callers must either pass ``project`` (to get
        # the default koru-brief builder) or a custom ``handoff`` callable.
        # Tests use the callable form; the CLI wires ``project`` from
        # ``--project``.
        if handoff is not None:
            self.handoff: HandoffBuilder | None = handoff
        elif project is not None:
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

    # ----- lifecycle -----------------------------------------------------

    def start(self) -> None:
        """Bind the socket and register it with the selector."""
        path = self.socket_path
        if path.exists():
            # Clean up stale sockets from a previous crashed daemon.
            try:
                path.unlink()
            except OSError as exc:
                raise RuntimeError(f"cannot remove stale socket {path}: {exc}") from exc
        srv = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        srv.setblocking(False)
        srv.bind(str(path))
        # 0600 — owner only. Defence in depth on top of SO_PEERCRED.
        os.chmod(path, stat.S_IRUSR | stat.S_IWUSR)
        srv.listen(16)
        self._server = srv
        self._sel.register(srv, selectors.EVENT_READ, data="server")
        self.log(f"koru autopilot daemon: listening on {path}")

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
            try:
                self._sel.unregister(self._server)
            except KeyError:
                pass
            try:
                self._server.close()
            except OSError:
                pass
            self._server = None
        try:
            self.socket_path.unlink()
        except OSError:
            pass
        self.log("koru autopilot daemon: stopped")

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
        # Enforce same-UID policy.
        peer_uid = _peer_uid(conn)
        if peer_uid is not None and peer_uid != os.getuid():
            self.log(f"reject peer uid={peer_uid} (daemon uid={os.getuid()})")
            conn.close()
            return
        conn.setblocking(False)
        client = _Client(sock=conn, addr=f"fd{conn.fileno()}")
        self._clients[conn.fileno()] = client
        self._sel.register(conn, selectors.EVENT_READ, data=client)

    def _on_readable(self, client: _Client) -> None:
        try:
            chunk = client.sock.recv(4096)
        except OSError as exc:
            self.log(f"recv error from {client.addr}: {exc}")
            self._drop(client)
            return
        if not chunk:
            self._drop(client)
            return
        client.buf.extend(chunk)
        if len(client.buf) > MAX_LINE_BYTES:
            self._send(client, error(None, "line too large").encode())
            self._drop(client)
            return
        # Process every complete line currently in the buffer.
        while b"\n" in client.buf:
            line, _, rest = client.buf.partition(b"\n")
            client.buf = bytearray(rest)
            if not line.strip():
                continue
            try:
                msg = decode(line)
            except ProtocolError as exc:
                self._send(client, error(None, str(exc)).encode())
                continue
            self._dispatch(client, msg)

    # ----- dispatch ------------------------------------------------------

    def _dispatch(self, client: _Client, msg: Message) -> None:
        handler = _HANDLERS.get(msg.type)
        if handler is None:
            self._send(client, error(msg.id, f"unhandled type {msg.type!r}").encode())
            return
        try:
            handler(self, client, msg)
        except Exception as exc:  # pragma: no cover — defensive
            self.log(f"handler {msg.type} raised: {exc}")
            self._send(client, error(msg.id, f"internal error: {exc}").encode())

    def _send(self, client: _Client, payload: bytes) -> None:
        try:
            client.sock.sendall(payload)
        except OSError as exc:
            self.log(f"send to {client.addr} failed: {exc}")
            self._drop(client)

    def _drop(self, client: _Client) -> None:
        fd = client.sock.fileno()
        if fd in self._clients:
            del self._clients[fd]
        try:
            self._sel.unregister(client.sock)
        except (KeyError, ValueError):
            pass
        try:
            client.sock.close()
        except OSError:
            pass

    # ----- helpers used by handlers --------------------------------------

    def _plugin_for(self, ide: str | None) -> _Client | None:
        for client in self._clients.values():
            if client.role != "plugin":
                continue
            if ide in (None, "auto") or client.ide == ide:
                return client
        return None

    def _handle_drive(self, client: _Client, msg: Message) -> None:
        text = msg.data.get("text")
        if not isinstance(text, str) or not text:
            self._send(client, error(msg.id, "missing 'text'").encode())
            return
        ide_pref = msg.data.get("ide") if isinstance(msg.data.get("ide"), str) else None
        submit = bool(msg.data.get("submit", True))
        # 1. Try the plugin path.
        plugin = self._plugin_for(ide_pref if ide_pref not in (None, "auto") else None)
        if plugin is not None:
            corr = msg.id or f"drive-{time.monotonic_ns():x}"
            plugin.awaiting_plugin = (client, corr)
            forwarded = chat_send(text, submit=submit, id=corr).encode()
            self._send(plugin, forwarded)
            self._last_chat_send_at = time.monotonic()
            self.log(f"drive → plugin/{plugin.ide} ({len(text)} chars)")
            return
        # 2. Keyboard-simulation fallback.
        detected = detect_running_ides()
        target = pick_target(detected, prefer=ide_pref if ide_pref not in (None, "auto") else None)
        target_id = target.id if target else "default"
        try:
            result = self.injector.type_text(text, ide=target_id, submit=submit)
        except InjectorError as exc:
            self._send(client, error(msg.id, str(exc)).encode())
            self.log(f"drive failed: {exc}")
            return
        info: dict[str, Any] = {"backend": result.backend, "submitted": result.submitted}
        if target is not None:
            info["ide"] = target.to_dict()
        self._send(client, ack(msg.id or "", info=info).encode())
        self.log(
            f"drive → {target_id} via {result.backend} "
            f"({len(text)} chars, submit={submit})"
        )

    def _handle_hello(self, client: _Client, msg: Message) -> None:
        ide = msg.data.get("ide")
        if not isinstance(ide, str) or not ide:
            self._send(client, error(msg.id, "hello requires 'ide'").encode())
            return
        client.role = "plugin"
        client.ide = ide
        self.log(f"plugin connected: ide={ide} version={msg.data.get('version')!r}")
        self._send(client, ack(msg.id or "", info={"role": "plugin"}).encode())

    def _handle_status(self, client: _Client, msg: Message) -> None:
        plugins = [
            {"ide": c.ide, "fd": c.sock.fileno()}
            for c in self._clients.values()
            if c.role == "plugin"
        ]
        info = {
            "socket": str(self.socket_path),
            "plugins": plugins,
            "backends": [b.to_dict() for b in self.injector.probe()],
            "selected_backend": self.injector.select_backend(),
            "ides": [i.to_dict() for i in detect_running_ides()],
        }
        self._send(client, ack(msg.id or "", info=info).encode())

    def _handle_ack(self, client: _Client, msg: Message) -> None:
        # Plugin responded to a forwarded ``chat.send``. Relay to the
        # waiting CLI.
        pending = client.awaiting_plugin
        if pending is None:
            return
        cli_client, corr = pending
        if msg.id != corr:
            return
        client.awaiting_plugin = None
        relay = ack(
            corr,
            ok=bool(msg.data.get("ok", True)),
            info={k: v for k, v in msg.data.items() if k != "ok"},
        )
        self._send(cli_client, relay.encode())

    def _handle_session_event(self, client: _Client, msg: Message) -> None:
        chat = msg.data.get("chat") or "default"
        reason = msg.data.get("reason") or ""
        self.log(f"event {msg.type} ide={client.ide} chat={chat} reason={reason!r}")
        # Always ack the event first so the plugin doesn't time out.
        ack_info: dict[str, Any] = {"event": msg.type}
        if msg.type != "session.ended" or self.handoff is None:
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            return
        # Cooldown: ignore session.ended right after we just typed
        # something — otherwise we'd loop forever if the LLM finishes
        # a turn immediately after our injection.
        elapsed = time.monotonic() - self._last_chat_send_at
        if elapsed < self.handoff_cooldown:
            ack_info["handoff"] = "skipped"
            ack_info["reason"] = f"cooldown ({elapsed:.2f}s < {self.handoff_cooldown:.2f}s)"
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            return
        try:
            text = self.handoff({"chat": chat, "reason": reason, "ide": client.ide})
        except Exception as exc:  # pragma: no cover — defensive
            ack_info["handoff"] = "error"
            ack_info["reason"] = str(exc)
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            self.log(f"handoff failed: {exc}")
            return
        if not text:
            ack_info["handoff"] = "skipped"
            ack_info["reason"] = "handoff returned empty text"
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            return
        # Forward the brief as chat.send on the same plugin connection.
        corr = f"handoff-{time.monotonic_ns():x}"
        forwarded = chat_send(text, submit=True, id=corr).encode()
        self._send(client, forwarded)
        self._last_chat_send_at = time.monotonic()
        ack_info["handoff"] = "sent"
        ack_info["chars"] = len(text)
        self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
        self.log(f"handoff → plugin/{client.ide} ({len(text)} chars)")

    def _handle_shutdown(self, client: _Client, msg: Message) -> None:
        self._send(client, ack(msg.id or "shutdown", info={"stopping": True}).encode())
        self.log("shutdown requested via socket")
        self.stop()

    def _handle_ping(self, client: _Client, msg: Message) -> None:
        self._send(client, ack(msg.id or "ping", info={"pong": True}).encode())


def _h_drive(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_drive(c, m)
def _h_hello(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_hello(c, m)
def _h_status(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_status(c, m)
def _h_ack(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_ack(c, m)
def _h_sess(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_session_event(c, m)
def _h_shut(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_shutdown(c, m)
def _h_ping(d: AutopilotDaemon, c: _Client, m: Message) -> None: d._handle_ping(c, m)


_HANDLERS: dict[str, Callable[[AutopilotDaemon, _Client, Message], None]] = {
    "drive": _h_drive,
    "hello": _h_hello,
    "status": _h_status,
    "ack": _h_ack,
    "session.started": _h_sess,
    "session.ended": _h_sess,
    "shutdown": _h_shut,
    "ping": _h_ping,
}


__all__ = ["AutopilotDaemon"]
