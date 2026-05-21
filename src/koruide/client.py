"""Synchronous socket client for `koruide` control daemon."""

from __future__ import annotations

import socket
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .protocol import MAX_LINE_BYTES, Message, decode
from .protocol import drive as drive_msg
from .socket import default_socket_path


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

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(str(self.socket_path))
        return sock

    def request(self, msg: Message) -> Message:
        if self._client is not None:
            req = getattr(self._client, "request", None)
            if not callable(req):
                raise RuntimeError("injected client does not expose request(msg)")
            return req(msg)
        with self._connect() as sock:
            sock.sendall(msg.encode())
            buf = bytearray()
            while b"\n" not in buf:
                chunk = sock.recv(4096)
                if not chunk:
                    break
                buf.extend(chunk)
                if len(buf) > MAX_LINE_BYTES:
                    raise RuntimeError("response too large")
            line, _, _ = buf.partition(b"\n")
            if not line:
                raise RuntimeError("daemon closed connection without replying")
            return decode(line)

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
            )
        try:
            reply = self.request(
                drive_msg(
                    text,
                    submit=submit,
                    ide=ide,
                    require_plugin=require_plugin,
                    id="cli-drive",
                ),
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
