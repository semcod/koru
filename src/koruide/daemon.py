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

import contextlib
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
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any

from koruide.audit import AuditLog
from koruide.drive_orchestrator import DriveOrchestrator
from koruide.ide import detect_running_ides_cached as detect_running_ides
from koruide.ide import pick_target, resolve_drive_target
from koruide.injector import Injector, InjectorError
from koruide.plugin_router import PluginRouter
from koruide.protocol import (
    MAX_LINE_BYTES,
    MIN_PLUGIN_PROTOCOL_VERSION,
    Message,
    ProtocolError,
    ack,
    chat_send,
    decode,
    error,
)
from koruide.socket import default_socket_path


def _daemon_package_version() -> str | None:
    try:
        return version("koru")
    except PackageNotFoundError:
        return None


# Type alias: a HandoffBuilder takes the ended-session metadata and
# returns the text to type back into the chat (typically the koru
# markdown brief). Returning ``""`` cancels the handoff.
HandoffBuilder = Callable[[dict[str, Any]], str]


def _env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def _prefer_keyboard_drive() -> bool:
    return _env_truthy("KORU_AUTOPILOT_PREFER_KEYBOARD") or _env_truthy(
        "KORU_AUTOPILOT_VISIBLE_TYPING",
    )


def _plugin_rejection_log_interval_seconds() -> float:
    raw = os.environ.get("KORU_PLUGIN_REJECTION_LOG_INTERVAL_SECONDS", "").strip()
    if not raw:
        return 300.0
    try:
        return max(5.0, float(raw))
    except ValueError:
        return 300.0


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
    version: str | None = None
    protocol_version: int | None = None
    capabilities: list[str] = field(default_factory=list)
    # Pending CLI ack: when a CLI sends ``drive`` and we forward to a
    # plugin, we remember the CLI socket so we can reply after the
    # plugin acks.
    awaiting_plugin: tuple[_Client, str, bool, str | None, str, bool] | None = None


@dataclass(frozen=True)
class _PluginEventHandoff:
    ack_info: dict[str, Any]
    chat: str
    reason: str


# Thread-safe storage for plugin console logs (for koru doctor)
_console_logs_lock = threading.Lock()
_console_logs: list[dict[str, Any]] = []
_MAX_CONSOLE_LOGS = 1000
_STATUS_CONSOLE_LOGS_LIMIT = 80


def add_console_log(
    message: str,
    data: Any | None,
    timestamp: str,
    *,
    ide: str | None = None,
    version: str | None = None,
) -> None:
    """Store a console log entry from the plugin."""
    entry: dict[str, Any] = {
        "message": message,
        "data": data,
        "timestamp": timestamp,
    }
    if ide:
        entry["ide"] = ide
    if version:
        entry["version"] = version
    with _console_logs_lock:
        _console_logs.append(entry)
        # Keep only the most recent logs
        if len(_console_logs) > _MAX_CONSOLE_LOGS:
            _console_logs.pop(0)


def get_console_logs(*, limit: int | None = None) -> list[dict[str, Any]]:
    """Retrieve all stored console logs."""
    with _console_logs_lock:
        rows = list(_console_logs)
    if limit is None:
        return rows
    if limit <= 0:
        return []
    return rows[-limit:]


def clear_console_logs() -> None:
    """Clear all stored console logs."""
    with _console_logs_lock:
        _console_logs.clear()


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
        self._plugin_router = PluginRouter(self._clients, drop_client=self._drop, log=self.log)
        self._handlers = self._build_handler_table()
        self._plugin_rejection_log_state: dict[
            tuple[str, str | None, str | None], tuple[float, int]
        ] = {}
        self._plugin_rejections: list[dict[str, Any]] = []

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
            with contextlib.suppress(KeyError):
                self._sel.unregister(self._server)
            with contextlib.suppress(OSError):
                self._server.close()
            self._server = None
        with contextlib.suppress(OSError):
            self.socket_path.unlink()
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
        self.log(f"client connected: {client.addr}")

    def _on_readable(self, client: _Client) -> None:
        try:
            chunk = client.sock.recv(4096)
        except OSError as exc:
            self.log(f"recv error from {client.addr}: {exc}")
            self._drop(client)
            return
        if not chunk:
            self.log(f"client disconnected: {client.addr}")
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
        with contextlib.suppress(KeyError, ValueError):
            self._sel.unregister(client.sock)
        with contextlib.suppress(OSError):
            client.sock.close()

    # ----- helpers used by handlers --------------------------------------

    def _plugin_for(self, ide: str | None) -> _Client | None:
        return self._plugin_router.plugin_for(ide)

    def _handle_drive(self, client: _Client, msg: Message) -> None:
        text = msg.data.get("text")
        if not isinstance(text, str) or not text:
            self._send(client, error(msg.id, "missing 'text'").encode())
            return
        raw_ide = msg.data.get("ide") if isinstance(msg.data.get("ide"), str) else None
        ide_pref = raw_ide if raw_ide not in (None, "auto") else None
        submit = bool(msg.data.get("submit", True))
        require_plugin = bool(msg.data.get("require_plugin", False))
        self.log(f"drive request: ide={raw_ide or 'auto'}, chars={len(text)}, submit={submit}, require_plugin={require_plugin}")
        plugin = self._plugin_for(ide_pref)
        if plugin is not None:
            self.log(f"drive: found plugin for ide={plugin.ide} (version={plugin.version}, protocol={plugin.protocol_version})")
        else:
            self.log(f"drive: no plugin found for ide={ide_pref}")
        if plugin is not None and not _prefer_keyboard_drive():
            self.log(f"drive: routing via plugin (ide={plugin.ide})")
            self._drive_via_plugin(client, msg, plugin, text, submit, require_plugin)
            return
        if require_plugin:
            label = ide_pref or "auto"
            message = DriveOrchestrator.plugin_required_message(ide_pref)
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
        self.log(f"drive: routing via keyboard/os_injector fallback")
        self._drive_via_keyboard(client, msg, ide_pref, text, submit)

    def _drive_via_plugin(
        self,
        client: _Client,
        msg: Message,
        plugin: _Client,
        text: str,
        submit: bool,
        require_plugin: bool,
    ) -> None:
        """Forward a drive request to a connected plugin for that IDE."""
        self.log(f"drive_via_plugin: ide={plugin.ide}, version={plugin.version}, protocol={plugin.protocol_version}, capabilities={plugin.capabilities}")
        corr = msg.id or f"drive-{time.monotonic_ns():x}"
        version_info = DriveOrchestrator.plugin_version_info(
            plugin_ide=plugin.ide,
            connected_version=plugin.version,
            protocol_version=plugin.protocol_version,
            capabilities=plugin.capabilities,
        )
        self.log(f"drive_via_plugin: version_info={version_info}")
        if version_info.get("plugin_version_mismatch"):
            summary = DriveOrchestrator.plugin_ack_summary(version_info)
            self.log(f"drive plugin version drift: {summary}")
            self.audit.record(
                "plugin_version_mismatch",
                ide=plugin.ide,
                plugin_version=version_info.get("plugin_version"),
                expected_plugin_version=version_info.get("expected_plugin_version"),
                policy=version_info.get("plugin_version_policy"),
            )
        if DriveOrchestrator.should_block_plugin_version(version_info):
            message = DriveOrchestrator.plugin_version_block_message(version_info)
            self._send(client, error(msg.id, message).encode())
            self.log(f"drive blocked: {message}")
            self.audit.record(
                "drive",
                ide=plugin.ide,
                backend="plugin",
                chars=len(text),
                submit=submit,
                ok=False,
                error=message,
                plugin_version=version_info.get("plugin_version"),
                expected_plugin_version=version_info.get("expected_plugin_version"),
            )
            return
        plugin.awaiting_plugin = (client, corr, submit, plugin.ide, text, require_plugin)
        self._send(plugin, chat_send(text, submit=submit, id=corr).encode())
        self._last_chat_send_at = time.monotonic()
        preview = text.replace("\n", " ")[:100]
        self.log(
            f"drive → plugin/{plugin.ide}: wklejam do czatu ({len(text)} zn, "
            f"submit={submit}) «{preview}»",
        )
        self.audit.record(
            "drive",
            ide=plugin.ide,
            backend="plugin",
            chars=len(text),
            submit=submit,
            ok=True,
        )

    def _try_os_injector_drive(
        self, target_id: str, text: str, submit: bool
    ) -> dict[str, Any] | None:
        """Run :mod:`os_injector` when configured; ``None`` means use keyboard."""
        self.log(f"try_os_injector_drive: target_id={target_id}, chars={len(text)}, submit={submit}")
        from koruide import os_injector as oi

        try:
            result = oi.try_drive_with_profile(
                tool_id=target_id,
                text=text,
                submit=submit,
                project=self.project,
                cli_dry_run=False,
                _log=self.log,
            )
            if result:
                self.log(f"try_os_injector_drive: SUCCESS backend={result.get('backend')}, chat_coords=({result.get('chat_x')}, {result.get('chat_y')}), input_method={result.get('input_method')}")
            return result
        except oi.OsInjectorError as exc:
            self.log(f"try_os_injector_drive: FAILED: {exc}")
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
        self.log(f"drive_via_keyboard: ide_arg={ide_arg}, chars={len(text)}, submit={submit}")
        target_id, profile_id, selection = resolve_drive_target(
            ide_arg,
            None,
            project=self.project,
            _log=self.log,
        )
        self.log(f"drive_via_keyboard: resolved target_id={target_id}, profile_id={profile_id}, selection={selection}")
        if ide_arg == "auto":
            self.log(f"drive auto-selected {profile_id} ({selection})")
        preview = text.replace("\n", " ")[:100]
        target = pick_target(detect_running_ides(), prefer=ide_pref)
        try:
            os_res = self._try_os_injector_drive(profile_id, text, submit)
        except InjectorError as exc:
            os_res = None
            self.log(f"drive → os_injector/{profile_id} failed; trying keyboard fallback: {exc}")
        if os_res is not None:
            self.log(
                f"drive → os_injector/{profile_id}: klik ({os_res.get('chat_x')}, "
                f"{os_res.get('chat_y')}) + {os_res.get('input_method', 'type')} "
                f"«{preview}»",
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
                f"drive → {target_id} via {info['backend']}"
                f" ({len(text)} chars, submit={submit})",
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

        backend = self.injector.select_backend()
        self.log(
            f"drive → keyboard/{target_id}: {backend or 'no-backend'} "
            f"({len(text)} zn) «{preview}»",
        )
        try:
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

    def _extract_hello_metadata(self, msg: Message) -> tuple[str | None, str | None, int | None, list[str]]:
        """Extract and validate hello message metadata."""
        ide = msg.data.get("ide")
        version = msg.data.get("version")
        plugin_version = version if isinstance(version, str) else None
        protocol_raw = msg.data.get("protocolVersion")
        protocol_version = protocol_raw if isinstance(protocol_raw, int) else None
        capabilities_raw = msg.data.get("capabilities")
        capabilities = (
            [item for item in capabilities_raw if isinstance(item, str)]
            if isinstance(capabilities_raw, list)
            else []
        )
        return ide, plugin_version, protocol_version, capabilities

    def _handle_plugin_version_check(
        self,
        client: _Client,
        msg: Message,
        ide: str,
        plugin_version: str | None,
        protocol_version: int | None,
        capabilities: list[str],
    ) -> bool:
        """Check plugin version and return True if accepted, False if rejected."""
        version_info = DriveOrchestrator.plugin_version_info(
            plugin_ide=ide,
            connected_version=plugin_version,
            protocol_version=protocol_version,
            capabilities=capabilities,
        )
        if DriveOrchestrator.should_block_plugin_version(version_info):
            message = DriveOrchestrator.plugin_version_block_message(version_info)
            self._send(client, error(msg.id, message).encode())
            self._log_rejected_plugin_connection(
                ide=ide,
                plugin_version=plugin_version,
                expected_plugin_version=version_info.get("expected_plugin_version"),
                message=message,
            )
            self.audit.record(
                "plugin_rejected",
                ide=ide,
                version=plugin_version,
                expected_plugin_version=version_info.get("expected_plugin_version"),
                error=message,
            )
            self._drop(client)
            return False
        return True

    def _configure_plugin_client(
        self,
        client: _Client,
        ide: str,
        plugin_version: str | None,
        protocol_version: int | None,
        capabilities: list[str],
    ) -> None:
        """Configure client as a plugin with provided metadata."""
        client.role = "plugin"
        client.ide = ide
        client.version = plugin_version
        client.protocol_version = protocol_version
        client.capabilities = capabilities
        self._plugin_router.drop_stale_plugins(client, ide)

    def _log_plugin_hello_accepted(
        self,
        ide: str,
        plugin_version: str | None,
        protocol_version: int | None,
        capabilities: list[str],
        version_info: dict[str, Any],
        matching_cmds: Any,
    ) -> None:
        """Log successful plugin hello acceptance."""
        command_count = len(matching_cmds) if isinstance(matching_cmds, list) else "-"
        self.log(
            "plugin hello accepted: "
            f"ide={ide} version={plugin_version or '-'} "
            f"expected={version_info.get('expected_plugin_version') or '-'} "
            f"policy={version_info.get('plugin_version_policy') or 'warn'} "
            f"protocol={protocol_version or '-'} min_protocol={MIN_PLUGIN_PROTOCOL_VERSION} "
            f"capabilities={len(capabilities)} matching_commands={command_count}",
        )

    def _handle_hello(self, client: _Client, msg: Message) -> None:
        ide, plugin_version, protocol_version, capabilities = self._extract_hello_metadata(msg)
        if not isinstance(ide, str) or not ide:
            self._send(client, error(msg.id, "hello requires 'ide'").encode())
            return

        if not self._handle_plugin_version_check(
            client, msg, ide, plugin_version, protocol_version, capabilities
        ):
            return

        version_info = DriveOrchestrator.plugin_version_info(
            plugin_ide=ide,
            connected_version=plugin_version,
            protocol_version=protocol_version,
            capabilities=capabilities,
        )

        self._configure_plugin_client(client, ide, plugin_version, protocol_version, capabilities)
        matching_cmds = msg.data.get("matchingCommands")
        self._log_plugin_hello_accepted(
            ide, plugin_version, protocol_version, capabilities, version_info, matching_cmds
        )
        self._send(client, ack(msg.id or "", info={"role": "plugin"}).encode())
        self.audit.record(
            "plugin_connected",
            ide=ide,
            version=plugin_version,
        )

    def _log_rejected_plugin_connection(
        self,
        *,
        ide: str,
        plugin_version: str | None,
        expected_plugin_version: Any,
        message: str,
    ) -> None:
        expected = expected_plugin_version if isinstance(expected_plugin_version, str) else None
        key = (ide, plugin_version, expected)
        now = time.monotonic()
        last, suppressed = self._plugin_rejection_log_state.get(key, (0.0, 0))
        if last and now - last < _plugin_rejection_log_interval_seconds():
            self._plugin_rejection_log_state[key] = (last, suppressed + 1)
            return
        suffix = f" (suppressed {suppressed} repeated reconnects)" if suppressed else ""
        self.log(f"rejecting plugin connection: ide={ide} {message}{suffix}")
        self._plugin_rejection_log_state[key] = (now, 0)
        self._plugin_rejections.append(
            {
                "ide": ide,
                "version": plugin_version,
                "expected_version": expected,
                "message": message,
                "suppressed": suppressed,
                "at": time.time(),
            }
        )
        if len(self._plugin_rejections) > 20:
            del self._plugin_rejections[:-20]

    def _handle_status(self, client: _Client, msg: Message) -> None:
        self.log(f"status request from {client.addr} role={client.role}")
        if client.role == "unknown":
            client.role = "cli"
        plugins = [row.to_dict() for row in self._plugin_router.status_rows()]
        daemon_version = _daemon_package_version()
        info = {
            "socket": str(self.socket_path),
            "daemon_pid": os.getpid(),
            "daemon_version": daemon_version,
            "daemon": {
                "pid": os.getpid(),
                "version": daemon_version,
            },
            "plugins": plugins,
            "rejected_plugins": list(self._plugin_rejections),
            "console_logs": get_console_logs(limit=_STATUS_CONSOLE_LOGS_LIMIT),
            "backends": [b.to_dict() for b in self.injector.probe()],
            "selected_backend": self.injector.select_backend(),
            "ides": [i.to_dict() for i in detect_running_ides()],
        }
        self._send(client, ack(msg.id or "", info=info).encode())

    def _plugin_ack_needs_os_fallback(
        self,
        *,
        plugin_ok: bool,
        info: dict[str, Any],
        submit_requested: bool,
        plugin_ide: str | None,
        require_plugin: bool,
    ) -> bool:
        return DriveOrchestrator.should_try_os_fallback(
            plugin_ok=plugin_ok,
            info=info,
            submit_requested=submit_requested,
            plugin_ide=plugin_ide,
            require_plugin=require_plugin,
        )

    def _relay_os_fallback_ack(
        self,
        cli_client: _Client,
        corr: str,
        plugin_ide: str,
        original_text: str,
        submit_requested: bool,
        info: dict[str, Any],
    ) -> bool:
        try:
            os_res = self._try_os_injector_drive(plugin_ide, original_text, submit_requested)
        except InjectorError as exc:
            info["os_fallback"] = "failed"
            info["os_fallback_error"] = str(exc)
            return False
        if os_res is None:
            return False
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
        return True

    def _relay_message_sent_ack(self, client: _Client, msg: Message) -> bool:
        """Use ``message.sent`` event as fallback completion for pending ``drive``.

        Some plugin builds can emit lifecycle event ``message.sent`` reliably
        but miss/skip the explicit ``ack`` for the original ``chat.send``.
        When that happens, we still want the waiting CLI request to complete
        successfully instead of timing out.
        """

        pending = client.awaiting_plugin
        if pending is None:
            return False
        cli_client, corr, submit_requested, plugin_ide, _original_text, _require_plugin = pending
        if DriveOrchestrator.strict_plugin_ack_required():
            self.log(
                "drive → plugin event observed before strict ack; "
                "waiting for full plugin ack"
            )
            return False
        client.awaiting_plugin = None
        info = DriveOrchestrator.build_message_sent_info(
            submit_requested=submit_requested,
            plugin_ide=plugin_ide,
            event_data=msg.data,
        )
        info.update(
            DriveOrchestrator.plugin_version_info(
                plugin_ide=plugin_ide,
                connected_version=client.version,
                protocol_version=client.protocol_version,
                capabilities=client.capabilities,
            ),
        )
        self.log(
            "drive → plugin event completion: "
            + DriveOrchestrator.plugin_ack_summary(info)
        )
        self._send(cli_client, ack(corr, ok=True, info=info).encode())
        return True

    def _handle_ack(self, client: _Client, msg: Message) -> None:
        # Plugin responded to a forwarded ``chat.send``. Relay to the
        # waiting CLI.
        pending = client.awaiting_plugin
        if pending is None:
            return
        cli_client, corr, submit_requested, plugin_ide, original_text, require_plugin = pending
        if msg.id != corr:
            return
        client.awaiting_plugin = None
        info = {k: v for k, v in msg.data.items() if k != "ok"}
        plugin_ok = bool(msg.data.get("ok", True))
        info = DriveOrchestrator.annotate_plugin_ack(
            info=info,
            plugin_ok=plugin_ok,
            submit_requested=submit_requested,
        )
        info.update(
            DriveOrchestrator.plugin_version_info(
                plugin_ide=plugin_ide,
                connected_version=client.version,
                protocol_version=client.protocol_version,
                capabilities=client.capabilities,
            ),
        )
        if DriveOrchestrator.should_fail_strict_plugin_ack(
            info=info,
            plugin_ok=plugin_ok,
            submit_requested=submit_requested,
            plugin_ide=plugin_ide,
        ):
            plugin_ok = False
            info["message"] = (
                "strict plugin verification failed: expected full VS Code plugin "
                "ack with winning_focus_open / winning_paste / winning_submit"
            )
        if self._plugin_ack_needs_os_fallback(
            plugin_ok=plugin_ok,
            info=info,
            submit_requested=submit_requested,
            plugin_ide=plugin_ide,
            require_plugin=require_plugin,
        ) and self._relay_os_fallback_ack(
            cli_client,
            corr,
            plugin_ide,
            original_text,
            submit_requested,
            info,
        ):
            return
        # IDE plugins typically send ``delivered`` without ``backend``; CLI
        # summaries (e.g. ``koru autonomous``) expect a stable backend label.
        if info.get("delivered") is True and "backend" not in info:
            info["backend"] = "plugin"
        self.log("drive → plugin ack: " + DriveOrchestrator.plugin_ack_summary(info))
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

    def _plugin_event_should_handoff(self, msg: Message) -> bool:
        return msg.type == "session.ended" and self.handoff is not None

    def _ack_plugin_event_without_handoff(
        self,
        client: _Client,
        msg: Message,
        ack_info: dict[str, Any],
    ) -> None:
        self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
        if msg.type == "message.sent":
            self._relay_message_sent_ack(client, msg)

    def _handle_plugin_event_basic(
        self,
        client: _Client,
        msg: Message,
    ) -> _PluginEventHandoff | None:
        """Handle basic plugin event logging and acknowledgment."""
        chat = msg.data.get("chat") or "default"
        reason = msg.data.get("reason") or ""
        self.log(f"event {msg.type} ide={client.ide} chat={chat} reason={reason!r}")
        self._append_event(client, msg)
        self.audit.record(
            "plugin_event",
            type=msg.type,
            ide=client.ide,
            **msg.data,
        )
        ack_info: dict[str, Any] = {"event": msg.type}
        if not self._plugin_event_should_handoff(msg):
            self._ack_plugin_event_without_handoff(client, msg, ack_info)
            return None
        return _PluginEventHandoff(ack_info=ack_info, chat=chat, reason=reason)

    def _check_handoff_cooldown(self, ack_info: dict[str, Any]) -> bool:
        """Check if handoff cooldown period has passed."""
        elapsed = time.monotonic() - self._last_chat_send_at
        if elapsed < self.handoff_cooldown:
            ack_info["handoff"] = "skipped"
            ack_info["reason"] = f"cooldown ({elapsed:.2f}s < {self.handoff_cooldown:.2f}s)"
            return False
        return True

    def _execute_handoff(
        self,
        client: _Client,
        msg: Message,
        chat: str,
        reason: str,
        ack_info: dict[str, Any],
    ) -> str | None:
        """Execute handoff and return text if successful."""
        try:
            text = self.handoff({"chat": chat, "reason": reason, "ide": client.ide})
        except Exception as exc:
            ack_info["handoff"] = "error"
            ack_info["reason"] = str(exc)
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            self.log(f"handoff failed: {exc}")
            return None
        if not text:
            ack_info["handoff"] = "skipped"
            ack_info["reason"] = "handoff returned empty text"
            self._send(client, ack(msg.id or "session-event", info=ack_info).encode())
            return None
        return text

    def _forward_handoff_to_plugin(
        self,
        client: _Client,
        msg: Message,
        text: str,
        chat: str,
        reason: str,
        ack_info: dict[str, Any],
    ) -> None:
        """Forward handoff text to plugin and log."""
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

    def _handle_plugin_event(self, client: _Client, msg: Message) -> None:
        handoff = self._handle_plugin_event_basic(client, msg)
        if handoff is None:
            return

        if not self._check_handoff_cooldown(handoff.ack_info):
            self._send(client, ack(msg.id or "session-event", info=handoff.ack_info).encode())
            return

        text = self._execute_handoff(
            client,
            msg,
            handoff.chat,
            handoff.reason,
            handoff.ack_info,
        )
        if text is None:
            return

        self._forward_handoff_to_plugin(
            client,
            msg,
            text,
            handoff.chat,
            handoff.reason,
            handoff.ack_info,
        )

    def _handle_shutdown(self, client: _Client, msg: Message) -> None:
        if client.role == "unknown":
            client.role = "cli"
        self._send(client, ack(msg.id or "shutdown", info={"stopping": True}).encode())
        self.log(
            "shutdown requested via socket "
            f"role={client.role} ide={client.ide or '-'} "
            f"version={client.version or '-'} addr={client.addr}"
        )
        self.audit.record("shutdown", source="socket")
        self.stop()

    def _handle_ping(self, client: _Client, msg: Message) -> None:
        self.log(f"ping from {client.addr} role={client.role}")
        if client.role == "unknown":
            client.role = "cli"
        self._send(client, ack(msg.id or "ping", info={"pong": True}).encode())

    def _handle_console_log(self, client: _Client, msg: Message) -> None:
        """Handle console log messages from the plugin for koru doctor."""
        message = msg.data.get("message") if isinstance(msg.data, dict) else None
        data = msg.data.get("data") if isinstance(msg.data, dict) else None
        timestamp = msg.data.get("timestamp") if isinstance(msg.data, dict) else None
        if isinstance(message, str) and isinstance(timestamp, str):
            entry_ide = msg.data.get("ide") if isinstance(msg.data, dict) else None
            entry_version = msg.data.get("version") if isinstance(msg.data, dict) else None
            add_console_log(
                message,
                data,
                timestamp,
                ide=str(entry_ide or client.ide or "").strip() or None,
                version=str(entry_version or client.version or "").strip() or None,
            )
        # Silent success - no ack needed for log messages

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
            "console_log": self._handle_console_log,
        }


__all__ = ["AutopilotDaemon"]
