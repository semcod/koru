"""Routing helpers for connected IDE autopilot plugins."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Protocol

from koruide.ide import normalize_ide_id


class PluginClient(Protocol):
    role: str
    ide: str | None
    protocol_version: int | None
    capabilities: list[str]
    build_sha: str | None
    workspace_name: str | None
    workspace_folders: list[str]
    sock: Any
    awaiting_plugin: Any | None


@dataclass(frozen=True)
class PluginStatusRow:
    ide: str | None
    fd: int
    version: str | None = None
    build_sha: str | None = None
    protocol_version: int | None = None
    capabilities: list[str] | None = None
    workspace_name: str | None = None
    workspace_folders: list[str] | None = None

    def to_dict(self) -> dict[str, Any]:
        data = {"ide": self.ide, "fd": self.fd}
        if self.version:
            data["version"] = self.version
        if self.build_sha:
            data["buildSha"] = self.build_sha
        if self.protocol_version is not None:
            data["protocolVersion"] = self.protocol_version
        if self.capabilities:
            data["capabilities"] = self.capabilities
        if self.workspace_name:
            data["workspaceName"] = self.workspace_name
        if self.workspace_folders:
            data["workspaceFolders"] = self.workspace_folders
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

    def plugin_for(self, ide: str | None, *, project: str | Path | None = None) -> PluginClient | None:
        target_ide = normalize_ide_id(ide)
        candidates = [
            client
            for client in reversed(list(self._clients.values()))
            if client.role == "plugin"
            and (target_ide in (None, "auto") or normalize_ide_id(client.ide) == target_ide)
        ]
        if project is not None:
            for client in candidates:
                if _workspace_matches_project(client.workspace_folders, project):
                    self._log(
                        "plugin_for: matched "
                        f"ide={client.ide} fd={client.sock.fileno()} "
                        f"workspace={client.workspace_name or '-'} "
                        f"folders={client.workspace_folders[:3] or '-'}",
                    )
                    return client
            workspace_aware = [client for client in candidates if client.workspace_folders]
            if workspace_aware:
                for client in workspace_aware:
                    self._log(
                        "plugin_for: skip workspace mismatch "
                        f"ide={client.ide} fd={client.sock.fileno()} "
                        f"project={project} folders={client.workspace_folders[:3]}",
                    )
                self._log(f"plugin_for: no workspace-matching plugin for ide={target_ide or 'auto'}")
                return None
        for client in candidates:
            workspace_note = (
                f" workspace={client.workspace_name or '-'} folders={client.workspace_folders[:3]}"
                if client.workspace_folders
                else " workspace=unknown"
            )
            self._log(f"plugin_for: matched ide={client.ide} fd={client.sock.fileno()}{workspace_note}")
            return client
        self._log(f"plugin_for: no plugin for ide={target_ide or 'auto'}")
        return None

    def drop_stale_plugins(self, current: PluginClient, ide: str) -> int:
        target_ide = normalize_ide_id(ide)
        current_has_workspace = bool(current.workspace_folders)
        stale = [
            other
            for other in self._clients.values()
            if other is not current
            and other.role == "plugin"
            and normalize_ide_id(other.ide) == target_ide
            and other.awaiting_plugin is None
            and (
                not other.workspace_folders
                or (
                    current_has_workspace
                    and _workspace_sets_overlap(current.workspace_folders, other.workspace_folders)
                )
            )
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
                build_sha=getattr(client, "build_sha", None),
                protocol_version=getattr(client, "protocol_version", None),
                capabilities=getattr(client, "capabilities", None),
                workspace_name=getattr(client, "workspace_name", None),
                workspace_folders=getattr(client, "workspace_folders", None),
            )
            for client in self._clients.values()
            if client.role == "plugin"
        ]


def _workspace_matches_project(workspace_folders: list[str], project: str | Path) -> bool:
    if not workspace_folders:
        return False
    try:
        project_path = Path(project).expanduser().resolve()
    except OSError:
        project_path = Path(project).expanduser().absolute()
    for raw_folder in workspace_folders:
        try:
            folder = Path(raw_folder).expanduser().resolve()
        except OSError:
            folder = Path(raw_folder).expanduser().absolute()
        try:
            if project_path == folder or project_path.is_relative_to(folder):
                return True
        except ValueError:
            continue
    return False


def _workspace_sets_overlap(left: list[str], right: list[str]) -> bool:
    for folder in left:
        if _workspace_matches_project(right, folder):
            return True
    for folder in right:
        if _workspace_matches_project(left, folder):
            return True
    return False


__all__ = ["PluginRouter", "PluginStatusRow"]
