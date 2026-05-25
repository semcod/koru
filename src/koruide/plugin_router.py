"""Routing helpers for connected IDE autopilot plugins."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Protocol

from koruide.ide import normalize_ide_id


class PluginClient(Protocol):
    role: str
    ide: str | None
    protocol_version: int | None
    capabilities: list[str]
    sock: Any
    awaiting_plugin: Any | None


@dataclass(frozen=True)
class PluginStatusRow:
    ide: str | None
    fd: int
    version: str | None = None
    protocol_version: int | None = None
    capabilities: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {"ide": self.ide, "fd": self.fd}
        if self.version:
            data["version"] = self.version
        if self.protocol_version is not None:
            data["protocolVersion"] = self.protocol_version
        if self.capabilities:
            data["capabilities"] = self.capabilities
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
        target_ide = normalize_ide_id(ide)
        for client in reversed(list(self._clients.values())):
            if client.role != "plugin":
                continue
            client_ide = normalize_ide_id(client.ide)
            if target_ide in (None, "auto") or client_ide == target_ide:
                self._log(f"plugin_for: matched ide={client.ide} fd={client.sock.fileno()}")
                return client
        self._log(f"plugin_for: no plugin for ide={target_ide or 'auto'}")
        return None

    def drop_stale_plugins(self, current: PluginClient, ide: str) -> int:
        target_ide = normalize_ide_id(ide)
        stale = [
            other
            for other in self._clients.values()
            if other is not current
            and other.role == "plugin"
            and normalize_ide_id(other.ide) == target_ide
            and other.awaiting_plugin is None
        ]
        for other in stale:
            self._log(f"dropping stale plugin connection: ide={target_ide} fd={other.sock.fileno()}")
            self._drop_client(other)
        return len(stale)

    def status_rows(self) -> list[PluginStatusRow]:
        return [
            PluginStatusRow(
                ide=client.ide,
                fd=client.sock.fileno(),
                version=getattr(client, "version", None),
                protocol_version=getattr(client, "protocol_version", None),
                capabilities=getattr(client, "capabilities", None),
            )
            for client in self._clients.values()
            if client.role == "plugin"
        ]


__all__ = ["PluginRouter", "PluginStatusRow"]
