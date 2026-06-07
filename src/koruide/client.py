"""Synchronous socket client for `koruide` control daemon."""

from __future__ import annotations

import os
import socket
import struct
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .protocol import Message, ProtocolError, decode
from .protocol import drive as drive_msg
from .protocol import error as error_msg
from .socket import default_socket_path

_FRAME_HEADER_BYTES = 4
_MAX_FRAME_BYTES = 8 * 1024 * 1024


class KoruIDEClient:
    """Connect, send one message, read one reply, disconnect."""

    def __init__(
        self,
        *,
        client: Any | None = None,
        socket_path: Path | None = None,
        timeout: float = 5.0,
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._client = client
        self.socket_path = socket_path or default_socket_path()
        self.timeout = timeout
        self._log = log

    def _drive_timeout(self) -> float:
        """Return how long the CLI waits for a drive ack.

        Drive ACKs can legitimately arrive *much* later than simple
        ping/status because the daemon waits for the plugin to:

        1. focus the chat panel (open/show + verify with editor snapshot),
        2. run the input-busy probe (select-all + clipboardCopyAction),
        3. paste the prompt (try N candidates with verification),
        4. run submit (try N candidates),
        5. verify each submit via probe AND ``cursorDiskKV`` poll
           (the bubble-DB poll alone has a 2.5s deadline).

        With 12 attempts each, the worst-case Cursor drive can take
        15-25s. The legacy 8s cap caused ``CHAT: autopilot: failed
        (autopilot daemon unreachable: timed out, kind=ticket_prompt)``
        even when the plugin was still working — the CLI gave up, the
        late ack carried real diagnostics that nobody saw, and the
        autonomous loop logged a misleading "daemon unreachable" failure.

        The new default is **120 seconds** (covers slow VS Code-family webview
        focus/paste probes plus headroom for Wayland host-key fallbacks). The
        autonomous loop still treats a missing ack as a failed drive, but this
        avoids cutting off a plugin that is alive and still probing the IDE.

        Operators can tune via ``KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS``.
        """
        raw = os.environ.get("KORU_AUTOPILOT_DRIVE_TIMEOUT_SECONDS", "").strip()
        if raw:
            try:
                return max(self.timeout, float(raw))
            except ValueError:
                pass
        return max(self.timeout, 120.0)

    def _connect(self, *, timeout: float | None = None) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout if timeout is None else timeout)
        sock.connect(str(self.socket_path))
        return sock

    def request(self, msg: Message, *, timeout: float | None = None) -> Message:
        if self._client is not None:
            req = getattr(self._client, "request", None)
            if not callable(req):
                raise RuntimeError("injected client does not expose request(msg)")
            return req(msg)
        with self._connect(timeout=timeout) as sock:
            sock.sendall(msg.encode())
            buf = bytearray()
            while True:
                parsed = self._extract_reply(buf)
                if parsed is not None:
                    return parsed
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if len(buf) > _MAX_FRAME_BYTES:
                    raise RuntimeError("response too large")
            if not buf:
                raise RuntimeError("daemon closed connection without replying")
            try:
                return decode(bytes(buf))
            except ProtocolError as exc:
                # Daemon sometimes drops the trailing newline (e.g. plugin
                # disconnects mid-ack, or the ack payload is truncated by an
                # interleaved event). Promote this to a structured ``error``
                # reply so the autonomous loop can record a failed cycle and
                # continue instead of crashing the whole ``koru auto`` run.
                # The partial bytes are logged for postmortem.
                if self._log:
                    head = bytes(buf[:160]).decode("utf-8", errors="replace")
                    self._log(
                        f"client: response parse failed ({exc}); "
                        f"bytes={len(buf)} head={head!r}"
                    )
                return error_msg(
                    msg.id,
                    f"daemon response could not be decoded ({exc}); "
                    f"got {len(buf)} bytes without a complete NDJSON envelope",
                )

    def _extract_reply(self, buf: bytearray) -> Message | None:
        """Decode one full daemon envelope from ``buf``.

        The daemon may answer with legacy NDJSON (``{...}\n``) or a
        length-prefixed frame (4-byte big-endian length + JSON payload).
        """
        if not buf:
            return None
        # Legacy NDJSON reply path.
        if buf[0] == ord("{"):
            if b"\n" not in buf:
                return None
            line, _, rest = buf.partition(b"\n")
            del buf[: len(buf) - len(rest)]
            return decode(bytes(line))

        # Length-prefixed reply path.
        if len(buf) < _FRAME_HEADER_BYTES:
            return None
        frame_len = struct.unpack(">I", bytes(buf[:_FRAME_HEADER_BYTES]))[0]
        if frame_len <= 0 or frame_len > _MAX_FRAME_BYTES:
            raise RuntimeError(f"invalid frame length: {frame_len}")
        total = _FRAME_HEADER_BYTES + frame_len
        if len(buf) < total:
            return None
        payload = bytes(buf[_FRAME_HEADER_BYTES:total])
        del buf[:total]
        return decode(payload.decode("utf-8"))

    def is_running(self) -> bool:
        if self._client is not None:
            return bool(self._client.is_running())
        if not self.socket_path.exists():
            if self._log:
                self._log(f"client: socket missing {self.socket_path}")
            return False
        try:
            reply = self.request(Message(type="ping", id="health"))
        except (OSError, RuntimeError) as exc:
            if self._log:
                self._log(f"client: ping failed: {exc}")
            return False
        ok = bool(reply.data.get("ok", False))
        if self._log:
            self._log(f"client: ping ok={ok}")
        return ok

    def drive(
        self,
        text: str,
        *,
        submit: bool = True,
        ide: str = "auto",
        require_plugin: bool = False,
        strategy_hint: str | None = None,
    ) -> dict[str, Any]:
        if self._log:
            self._log(
                f"client: drive ide={ide} chars={len(text)} "
                f"submit={submit} require_plugin={require_plugin}"
            )
        if self._client is not None:
            return self._client.drive(
                text,
                submit=submit,
                ide=ide,
                require_plugin=require_plugin,
                strategy_hint=strategy_hint,
            )
        try:
            corr = f"cli-drive-{os.getpid()}-{time.monotonic_ns():x}"
            reply = self.request(
                drive_msg(
                    text,
                    submit=submit,
                    ide=ide,
                    require_plugin=require_plugin,
                    strategy_hint=strategy_hint,
                    id=corr,
                ),
                timeout=self._drive_timeout(),
            )
            data = reply.to_dict()
            if self._log:
                self._log(f"client: drive reply ok={data.get('ok')} backend={data.get('backend')}")
            return data
        except FileNotFoundError as exc:
            if self._log:
                self._log(f"client: drive socket missing: {exc}")
            return {
                "ok": False,
                "message": f"autopilot socket missing: {self.socket_path} ({exc})",
                "backend": None,
            }
        except (ConnectionError, OSError) as exc:
            if self._log:
                self._log(f"client: drive daemon unreachable: {exc}")
            return {
                "ok": False,
                "message": f"autopilot daemon unreachable: {exc}",
                "backend": None,
            }

    def status(self) -> dict[str, Any]:
        if self._log:
            self._log("client: status request")
        if self._client is not None:
            return self._client.status()
        reply = self.request(Message(type="status", id="cli-status"))
        data = reply.to_dict()
        if self._log:
            self._log(f"client: status reply plugins={len(data.get('plugins', []))}")
        return data

    def shutdown(self) -> dict[str, Any]:
        if self._log:
            self._log("client: shutdown request")
        if self._client is not None:
            return self._client.shutdown()
        reply = self.request(Message(type="shutdown", id="cli-shutdown"))
        data = reply.to_dict()
        if self._log:
            self._log(f"client: shutdown reply stopping={data.get('stopping')}")
        return data


# Compatibility alias for cross-package transitions.
AutopilotClient = KoruIDEClient


def build_client(*, socket_path: Path | None = None, timeout: float = 5.0) -> KoruIDEClient:
    """Construct a `koruide` client for the given socket/timeout."""

    return KoruIDEClient(socket_path=socket_path, timeout=timeout)


__all__ = ["KoruIDEClient", "AutopilotClient", "build_client"]
