"""Routing helpers for connected IDE autopilot plugins."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol


class PluginClient(Protocol):
    role: str
    ide: str | None
    sock: Any


@dataclass(frozen=True)
class PluginStatusRow:
    ide: str | None
    fd: int
    version: str | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {"ide": self.ide, "fd": self.fd}
        if self.version:
            data["version"] = self.version
        return data


class PluginRouter:
    """Select, enumerate and deduplicate connected plugin sessions."""

    def __init__(
        self,
        clients: dict[int, PluginClient],
        *,
        drop_client: Callable[[PluginClient], None],
        log: Callable[[str], None] | None = None,
    ) -> None:
        self._clients = clients
        self._drop_client = drop_client
        self._log = log or (lambda _msg: None)

    def plugin_for(self, ide: str | None) -> PluginClient | None:
        for client in reversed(list(self._clients.values())):
            if client.role != "plugin":
                continue
            if ide in (None, "auto") or client.ide == ide:
                return client
        return None

    def drop_stale_plugins(self, current: PluginClient, ide: str) -> int:
        stale = [
            other
            for other in self._clients.values()
            if other is not current and other.role == "plugin" and other.ide == ide
        ]
        for other in stale:
            self._log(f"dropping stale plugin connection: ide={ide} fd={other.sock.fileno()}")
            self._drop_client(other)
        return len(stale)

    def status_rows(self) -> list[PluginStatusRow]:
        return [
            PluginStatusRow(
                ide=client.ide,
                fd=client.sock.fileno(),
                version=getattr(client, "version", None),
            )
            for client in self._clients.values()
            if client.role == "plugin"
        ]


__all__ = ["PluginRouter", "PluginStatusRow"]
