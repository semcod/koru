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
        candidates = self._plugin_candidates(target_ide)
        project_match = self._match_project_plugin(candidates, project, target_ide)
        if project_match is not None:
            return project_match
        if self._project_mismatch_blocks_fallback(candidates, project, target_ide):
            return None
        generic_match = self._first_generic_plugin(candidates)
        if generic_match is not None:
            return generic_match
        self._log(f"plugin_for: no plugin for ide={target_ide or 'auto'}")
        return None

    def _plugin_candidates(self, target_ide: str | None) -> list[PluginClient]:
        return [
            client
            for client in reversed(list(self._clients.values()))
            if self._matches_plugin_target(client, target_ide)
        ]

    @staticmethod
    def _matches_plugin_target(client: PluginClient, target_ide: str | None) -> bool:
        return client.role == "plugin" and (
            target_ide in (None, "auto") or normalize_ide_id(client.ide) == target_ide
        )

    def _match_project_plugin(
        self,
        candidates: list[PluginClient],
        project: str | Path | None,
        target_ide: str | None,
    ) -> PluginClient | None:
        if project is None:
            return None
        matched = self._first_workspace_match(candidates, project)
        if matched is not None:
            self._log_project_match(matched)
            return matched
        return None

    def _first_workspace_match(
        self,
        candidates: list[PluginClient],
        project: str | Path,
    ) -> PluginClient | None:
        return next(
            (
                client
                for client in candidates
                if _workspace_matches_project(client.workspace_folders, project)
            ),
            None,
        )

    @staticmethod
    def _has_workspace_aware_candidates(candidates: list[PluginClient]) -> bool:
        return any(client.workspace_folders for client in candidates)

    def _project_mismatch_blocks_fallback(
        self,
        candidates: list[PluginClient],
        project: str | Path | None,
        target_ide: str | None,
    ) -> bool:
        if project is None or not self._has_workspace_aware_candidates(candidates):
            return False
        self._log_workspace_mismatches(candidates, project, target_ide)
        return True

    def _log_project_match(self, client: PluginClient) -> None:
        self._log(
            "plugin_for: matched "
            f"ide={client.ide} fd={client.sock.fileno()} "
            f"workspace={client.workspace_name or '-'} "
            f"folders={client.workspace_folders[:3] or '-'}",
        )

    def _log_workspace_mismatches(
        self,
        candidates: list[PluginClient],
        project: str | Path,
        target_ide: str | None,
    ) -> None:
        for client in candidates:
            if client.workspace_folders:
                self._log(
                    "plugin_for: skip workspace mismatch "
                    f"ide={client.ide} fd={client.sock.fileno()} "
                    f"project={project} folders={client.workspace_folders[:3]}",
                )
        self._log(f"plugin_for: no workspace-matching plugin for ide={target_ide or 'auto'}")

    def _first_generic_plugin(self, candidates: list[PluginClient]) -> PluginClient | None:
        for client in candidates:
            self._log_generic_match(client)
            return client
        return None

    def _log_generic_match(self, client: PluginClient) -> None:
        workspace_note = (
            f" workspace={client.workspace_name or '-'} folders={client.workspace_folders[:3]}"
            if client.workspace_folders
            else " workspace=unknown"
        )
        self._log(f"plugin_for: matched ide={client.ide} fd={client.sock.fileno()}{workspace_note}")

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
