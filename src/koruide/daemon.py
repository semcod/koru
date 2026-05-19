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
2. Otherwise → optional X11 :mod:`os_injector` profile, then
   :class:`Injector` (keyboard sim).
3. Always log the event so the user can audit what was typed.

The daemon is intentionally single-threaded and selector-based. We
don't need throughput; we need predictability and a tiny footprint.
"""

from __future__ import annotations

import errno
import functools
import json
import os
import selectors
import socket
import stat
import struct
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from koruide.audit import AuditLog
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import pick_target, resolve_drive_target
from koruide.injector import Injector, InjectorError
from koruide.protocol import (
    MAX_LINE_BYTES,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    error,
)
from koruide.socket import default_socket_path

# Type alias: a HandoffBuilder takes the ended-session metadata and
# returns the text to type back into the chat (typically the koru
# markdown brief). Returning ``""`` cancels the handoff.
HandoffBuilder = Callable[[dict[str, Any]], str]


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _prefer_keyboard_drive() -> bool:
    return _env_truthy("KORU_AUTOPILOT_PREFER_KEYBOARD") or _env_truthy(
        "KORU_AUTOPILOT_VISIBLE_TYPING"
    )


@functools.lru_cache(maxsize=1)
def _load_context_module() -> tuple[Callable[..., dict[str, Any]], Callable[[dict[str, Any]], str]]:
    """Import ``koru.context`` exactly once (R4).

    Lazy + cached: the first ``session.ended`` pays the import cost; all
    subsequent handoffs reuse the same module references. Also keeps
    ``koruide`` importable for ``doctor`` / ``ide-list`` smoke tests
    that should not need the planfile stack.
    """
    from koru.context import build_context, render_markdown_handoff

    return build_context, render_markdown_handoff


def _default_handoff(project: Path) -> HandoffBuilder:
    """Build the canonical koru brief for ``project`` on demand."""

    def _build(_event: dict[str, Any]) -> str:
        build_context, render_markdown_handoff = _load_context_module()
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
    awaiting_plugin: tuple[_Client, str, bool, str | None, str] | None = None


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
        audit: AuditLog | None = None,
    ) -> None:
        self.socket_path = socket_path or default_socket_path()
        self.injector = injector or Injector()
        self.project = project
        self.log = log or (lambda _msg: None)
        # Optional persistent audit log (P2.7). ``None`` keeps the
        # current behaviour (logging only via ``self.log``).
        self.audit = audit or AuditLog(enabled=False)
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
        self._handlers = self._build_handler_table()

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
        self.audit.record(
            "daemon_started",
            socket=str(path),
            handoff=self.handoff is not None,
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
        handler = self._handlers.get(msg.type)
        if handler is None:
            self._send(client, error(msg.id, f"unhandled type {msg.type!r}").encode())
            return
        try:
            handler(client, msg)
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
        raw_ide = msg.data.get("ide") if isinstance(msg.data.get("ide"), str) else None
        ide_pref = raw_ide if raw_ide not in (None, "auto") else None
        submit = bool(msg.data.get("submit", True))
        require_plugin = bool(msg.data.get("require_plugin", False))
        plugin = self._plugin_for(ide_pref)
        if plugin is not None and not _prefer_keyboard_drive():
            self._drive_via_plugin(client, msg, plugin, text, submit)
            return
        if require_plugin:
            label = ide_pref or "auto"
            message = (
                f"no connected autopilot plugin for ide={label}; "
                "keyboard fallback disabled for this request. "
                "Reload the IDE window or run the `koru: Connect autopilot daemon` command "
                "so the extension connects to this socket."
            )
            self._send(client, error(msg.id, message).encode())
            self.log(f"drive blocked: {message}")
            self.audit.record(
                "drive",
                ide=label,
                backend="plugin_required",
                chars=len(text),
                submit=submit,
                ok=False,
                error=message,
            )
            return
        self._drive_via_keyboard(client, msg, ide_pref, text, submit)

    def _drive_via_plugin(
        self,
        client: _Client,
        msg: Message,
        plugin: _Client,
        text: str,
        submit: bool,
    ) -> None:
        """Forward a drive request to a connected plugin for that IDE."""
        corr = msg.id or f"drive-{time.monotonic_ns():x}"
        plugin.awaiting_plugin = (client, corr, submit, plugin.ide, text)
        self._send(plugin, chat_send(text, submit=submit, id=corr).encode())
        self._last_chat_send_at = time.monotonic()
        preview = text.replace("\n", " ")[:100]
        self.log(
            f"drive → plugin/{plugin.ide}: wklejam do czatu ({len(text)} zn, "
            f"submit={submit}) «{preview}»"
        )
        self.audit.record(
            "drive",
            ide=plugin.ide,
            backend="plugin",
            chars=len(text),
            submit=submit,
            ok=True,
        )

    def _try_os_injector_drive(self, target_id: str, text: str, submit: bool) -> dict[str, Any] | None:
        """Run :mod:`os_injector` when configured; ``None`` means use keyboard."""
        from koruide import os_injector as oi

        try:
            return oi.try_drive_with_profile(
                tool_id=target_id,
                text=text,
                submit=submit,
                project=self.project,
                cli_dry_run=False,
            )
        except oi.OsInjectorError as exc:
            raise InjectorError(str(exc)) from exc

    def _drive_via_keyboard(
        self,
        client: _Client,
        msg: Message,
        ide_pref: str | None,
        text: str,
        submit: bool,
    ) -> None:
        """Fallback: OS injector profile (X11) or :class:`Injector` keyboard sim."""
        ide_arg = ide_pref if ide_pref else "auto"
        target_id, profile_id, selection = resolve_drive_target(
            ide_arg,
            None,
            project=self.project,
        )
        if ide_arg == "auto":
            self.log(f"drive auto-selected {profile_id} ({selection})")
        preview = text.replace("\n", " ")[:100]
        target = pick_target(detect_running_ides(), prefer=ide_pref)
        try:
            os_res = self._try_os_injector_drive(profile_id, text, submit)
            if os_res is not None:
                self.log(
                    f"drive → os_injector/{profile_id}: klik ({os_res.get('chat_x')}, "
                    f"{os_res.get('chat_y')}) + {os_res.get('input_method', 'type')} "
                    f"«{preview}»"
                )
                info: dict[str, Any] = {
                    "backend": str(os_res.get("backend", "os_injector")),
                    "submitted": bool(os_res.get("submitted", submit)),
                }
                if os_res.get("dry_run"):
                    info["dry_run"] = True
                tid = os_res.get("tool_id")
                if isinstance(tid, str):
                    info["tool_id"] = tid
                if target is not None:
                    info["ide"] = target.to_dict()
                self._send(client, ack(msg.id or "", info=info).encode())
                self.log(
                    f"drive → {target_id} via {info['backend']} ({len(text)} chars, submit={submit})"
                )
                self.audit.record(
                    "drive",
                    ide=target_id,
                    backend=str(info["backend"]),
                    chars=len(text),
                    submit=submit,
                    ok=True,
                )
                return

            self.log(
                f"drive → keyboard/{target_id}: {self.injector.select_backend()} "
                f"({len(text)} zn) «{preview}»"
            )
            result = self.injector.type_text(text, ide=target_id, submit=submit)
        except InjectorError as exc:
            self._send(client, error(msg.id, str(exc)).encode())
            self.log(f"drive failed: {exc}")
            self.audit.record(
                "drive",
                ide=target_id,
                backend="keyboard",
                chars=len(text),
                submit=submit,
                ok=False,
                error=str(exc),
            )
            return
        info = {"backend": result.backend, "submitted": result.submitted}
        if target is not None:
            info["ide"] = target.to_dict()
        self._send(client, ack(msg.id or "", info=info).encode())
        self.log(f"drive → {target_id} via {result.backend} ({len(text)} chars, submit={submit})")
        self.audit.record(
            "drive",
            ide=target_id,
            backend=result.backend,
            chars=len(text),
            submit=submit,
            ok=True,
        )

    def _handle_hello(self, client: _Client, msg: Message) -> None:
        ide = msg.data.get("ide")
        if not isinstance(ide, str) or not ide:
            self._send(client, error(msg.id, "hello requires 'ide'").encode())
            return
        client.role = "plugin"
        client.ide = ide
        version = msg.data.get("version")
        self.log(f"plugin connected: ide={ide} version={version!r}")
        self._send(client, ack(msg.id or "", info={"role": "plugin"}).encode())
        self.audit.record(
            "plugin_connected",
            ide=ide,
            version=version if isinstance(version, str) else None,
        )

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
        cli_client, corr, submit_requested, plugin_ide, original_text = pending
        if msg.id != corr:
            return
        client.awaiting_plugin = None
        info = {k: v for k, v in msg.data.items() if k != "ok"}
        plugin_ok = bool(msg.data.get("ok", True))
        focus_error = "chat input is not focused/open" in str(info.get("message", "")).lower()
        submit_failed = (
            submit_requested and info.get("submitted") is False
        )
        undelivered = info.get("delivered") is False
        if (not plugin_ok) and focus_error and plugin_ide:
            try:
                os_res = self._try_os_injector_drive(plugin_ide, original_text, submit_requested)
            except InjectorError as exc:
                info["os_fallback"] = "failed"
                info["os_fallback_error"] = str(exc)
            else:
                if os_res is not None:
                    relay = ack(
                        corr,
                        ok=True,
                        info={
                            "backend": os_res.get("backend", "os_injector"),
                            "ok": True,
                            "delivered": True,
                            "opened": True,
                            "submitted": bool(os_res.get("submitted", submit_requested)),
                            "os_fallback": "used",
                        },
                    )
                    self._send(cli_client, relay.encode())
                    return
        if ((not plugin_ok) or submit_failed or undelivered) and plugin_ide:
            try:
                os_res = self._try_os_injector_drive(plugin_ide, original_text, submit_requested)
            except InjectorError as exc:
                info["os_fallback"] = "failed"
                info["os_fallback_error"] = str(exc)
            else:
                if os_res is not None:
                    relay = ack(
                        corr,
                        ok=True,
                        info={
                            "backend": os_res.get("backend", "os_injector"),
                            "ok": True,
                            "delivered": True,
                            "opened": True,
                            "submitted": bool(os_res.get("submitted", submit_requested)),
                            "os_fallback": "used",
                        },
                    )
                    self._send(cli_client, relay.encode())
                    return
        # IDE plugins typically send ``delivered`` without ``backend``; CLI
        # summaries (e.g. ``koru autonomous``) expect a stable backend label.
        if info.get("delivered") is True and "backend" not in info:
            info["backend"] = "plugin"
        relay = ack(corr, ok=plugin_ok, info=info)
        self._send(cli_client, relay.encode())

    def _event_path(self) -> Path:
        """Path to the NDJSON event file shared with autonomous."""
        return Path(os.environ.get("XDG_RUNTIME_DIR", "/tmp")) / "koru-autopilot-events.ndjson"

    def _append_event(self, client: _Client, msg: Message) -> None:
        """Persist plugin event to the shared NDJSON file."""
        try:
            path = self._event_path()
            payload = {
                "ts": time.time(),
                "type": msg.type,
                "ide": client.ide,
            }
            payload.update(msg.data)
            with path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(payload, separators=(",", ":")) + "\n")
        except OSError:
            pass

    def _handle_plugin_event(self, client: _Client, msg: Message) -> None:
        chat = msg.data.get("chat") or "default"
        reason = msg.data.get("reason") or ""
        self.log(f"event {msg.type} ide={client.ide} chat={chat} reason={reason!r}")
        # Persist every plugin event so autonomous can react.
        self._append_event(client, msg)
        self.audit.record(
            "plugin_event",
            type=msg.type,
            ide=client.ide,
            **msg.data,
        )
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
        self.audit.record(
            "handoff",
            ide=client.ide,
            chat=chat,
            reason=reason or None,
            chars=len(text),
            ok=True,
        )

    def _handle_shutdown(self, client: _Client, msg: Message) -> None:
        self._send(client, ack(msg.id or "shutdown", info={"stopping": True}).encode())
        self.log("shutdown requested via socket")
        self.audit.record("shutdown", source="socket")
        self.stop()

    def _handle_ping(self, client: _Client, msg: Message) -> None:
        self._send(client, ack(msg.id or "ping", info={"pong": True}).encode())

    def _build_handler_table(self) -> dict[str, Callable[[_Client, Message], None]]:
        """Return the per-instance dispatch table.

        Bound methods are already closures over ``self``, so dispatch
        is one dict lookup + one call — no thin wrapper functions.
        """
        return {
            "drive": self._handle_drive,
            "hello": self._handle_hello,
            "status": self._handle_status,
            "ack": self._handle_ack,
            "session.started": self._handle_plugin_event,
            "session.ended": self._handle_plugin_event,
            "message.sent": self._handle_plugin_event,
            "message.received": self._handle_plugin_event,
            "status.error": self._handle_plugin_event,
            "shutdown": self._handle_shutdown,
            "ping": self._handle_ping,
        }


__all__ = ["AutopilotDaemon"]
