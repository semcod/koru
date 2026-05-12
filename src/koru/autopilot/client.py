"""Tiny synchronous client for talking to the autopilot daemon.

Used by the ``koru autopilot drive`` / ``status`` / ``shutdown``
subcommands. One request, one response, then close.
"""

from __future__ import annotations

import socket
from pathlib import Path
from typing import Any

from . import default_socket_path
from .protocol import MAX_LINE_BYTES, Message, decode, drive as drive_msg


class AutopilotClient:
    """Connect, send one message, read one reply, disconnect."""

    def __init__(
        self,
        *,
        socket_path: Path | None = None,
        timeout: float = 5.0,
    ) -> None:
        self.socket_path = socket_path or default_socket_path()
        self.timeout = timeout

    # ----- low-level -----------------------------------------------------

    def _connect(self) -> socket.socket:
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        sock.settimeout(self.timeout)
        sock.connect(str(self.socket_path))
        return sock

    def request(self, msg: Message) -> Message:
        """Send ``msg`` and return the daemon's reply (one envelope)."""
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

    # ----- high-level convenience ---------------------------------------

    def is_running(self) -> bool:
        """Quick health check: is the daemon answering on its socket?"""
        if not self.socket_path.exists():
            return False
        try:
            reply = self.request(Message(type="ping", id="health"))
        except (OSError, RuntimeError):
            return False
        return bool(reply.data.get("ok", False))

    def drive(self, text: str, *, submit: bool = True, ide: str = "auto") -> dict[str, Any]:
        try:
            reply = self.request(drive_msg(text, submit=submit, ide=ide, id="cli-drive"))
            return reply.to_dict()
        except FileNotFoundError as exc:
            return {
                "ok": False,
                "message": f"autopilot socket missing: {self.socket_path} ({exc})",
                "backend": None,
            }
        except (ConnectionError, OSError) as exc:
            return {
                "ok": False,
                "message": f"autopilot daemon unreachable: {exc}",
                "backend": None,
            }

    def status(self) -> dict[str, Any]:
        reply = self.request(Message(type="status", id="cli-status"))
        return reply.to_dict()

    def shutdown(self) -> dict[str, Any]:
        reply = self.request(Message(type="shutdown", id="cli-shutdown"))
        return reply.to_dict()


__all__ = ["AutopilotClient"]
