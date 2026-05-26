from __future__ import annotations

import os
import socket
import struct
from dataclasses import dataclass, field
from importlib.metadata import PackageNotFoundError, version
from typing import Any

# SO_PEERCRED returns ``struct ucred { pid_t; uid_t; gid_t; }`` — three
# 32-bit little-endian ints on Linux.
_UCRED_STRUCT = struct.Struct("3i")


def _daemon_package_version() -> str | None:
    try:
        return version("koru")
    except PackageNotFoundError:
        return None


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
    build_sha: str | None = None
    protocol_version: int | None = None
    capabilities: list[str] = field(default_factory=list)
    command_catalog: dict[str, list[str]] | None = None
    workspace_name: str | None = None
    workspace_folders: list[str] = field(default_factory=list)
    # Pending CLI ack: when a CLI sends ``drive`` and we forward to a
    # plugin, we remember the CLI socket so we can reply after the
    # plugin acks.
    awaiting_plugin: tuple[_Client, str, bool, str | None, str, bool] | None = None
    awaiting_plugin_info: dict[str, Any] | None = None
    awaiting_plugin_timer: Any | None = None


@dataclass(frozen=True)
class _PluginEventHandoff:
    ack_info: dict[str, Any]
    chat: str
    reason: str
