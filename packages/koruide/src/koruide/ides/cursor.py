"""Cursor IDE strategy.

This module is the **single source of truth** for everything Koru knows about
Cursor: how to detect it, where its settings/state live, that Cursor enforces
``extensions.trustedPublishers``, how to reload its window, etc.

Other layers (``koruide.ide``, ``koru.ide_adapters``, ``koru.ide_reload``)
delegate Cursor-specific decisions here. Changing Cursor behavior happens in
this file only — VSCodium, Windsurf, Antigravity, etc. cannot be affected.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    PluginPolicy,
    StaticIdeIdentityMixin,
    StaticVscodeFolderMixin,
    TerminalSignature,
    VscodeFamilyStrategy,
)
from koruide.ides.registry import register_strategy

# Classic Cursor --user-data-dir used by c2004 ``launch-cursor-classic-c2004.sh``.
# Agents/glass keeps state under ~/.config/Cursor and never loads the Koru VSIX.
DEFAULT_CURSOR_CLASSIC_USER_DATA = Path("/tmp/cursor-classic-c2004-userdata")
_CURSOR_USER_DATA_ENV_KEYS = (
    "CURSOR_CLASSIC_USER_DATA_DIR",
    "KORU_CURSOR_USER_DATA_DIR",
)


def _user_data_from_koru_settings(project: Path) -> Path | None:
    """Read ``ides.cursor.user_data_dir`` (or flat ``cursor_user_data_dir``) from ``.koru/config.json``."""
    path = project / ".koru" / "config.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    flat = data.get("cursor_user_data_dir")
    if isinstance(flat, str) and flat.strip():
        return Path(flat.strip()).expanduser()
    ides = data.get("ides")
    if isinstance(ides, dict):
        cursor = ides.get("cursor")
        if isinstance(cursor, dict):
            raw = cursor.get("user_data_dir")
            if isinstance(raw, str) and raw.strip():
                return Path(raw.strip()).expanduser()
    return None


def resolve_cursor_user_data_dirs(*, project: Path | None = None) -> list[Path]:
    """Ordered existing Cursor ``--user-data-dir`` candidates (classic before Agents).

    Sources (first wins for :meth:`CursorStrategy.config_home`):
    1. ``CURSOR_CLASSIC_USER_DATA_DIR`` / ``KORU_CURSOR_USER_DATA_DIR``
    2. Project ``.koru/config.json`` (``ides.cursor.user_data_dir``)
    3. Default ``/tmp/cursor-classic-c2004-userdata`` when that directory exists
    """
    ordered: list[Path] = []
    seen: set[str] = set()

    def _add(candidate: Path | None) -> None:
        if candidate is None:
            return
        expanded = candidate.expanduser()
        key = str(expanded.resolve()) if expanded.exists() else str(expanded)
        if key in seen:
            return
        seen.add(key)
        ordered.append(expanded)

    for env_key in _CURSOR_USER_DATA_ENV_KEYS:
        raw = (os.environ.get(env_key) or "").strip()
        if raw:
            _add(Path(raw))

    projects: list[Path] = []
    if project is not None:
        projects.append(project.expanduser())
    env_project = (os.environ.get("KORU_PROJECT") or "").strip()
    if env_project:
        projects.append(Path(env_project).expanduser())
    projects.append(Path.cwd())
    for proj in projects:
        _add(_user_data_from_koru_settings(proj))

    _add(DEFAULT_CURSOR_CLASSIC_USER_DATA)
    return [path for path in ordered if path.is_dir()]


@dataclass(frozen=True)
class CursorStrategy(StaticIdeIdentityMixin, StaticVscodeFolderMixin, VscodeFamilyStrategy):
    """Strategy for Cursor (VS Code-fork by Anysphere)."""

    IDE_ID = "cursor"
    IDE_LABEL = "Cursor"
    CONFIG_FOLDER_NAME = "Cursor"

    @property
    def workspace_settings_folder_name(self) -> str:
        return ".cursor"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("cursor",),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_keys=("CURSOR_AGENT", "CURSOR_CLI"),
            env_value_substrings=("cursor",),
            parent_comm_substrings=("cursor",),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(canonical=self.id, aliases=("cursor",))

    def config_home(self) -> Path | None:
        # Prefer classic --user-data-dir when known so doctor/settings/vscdb
        # match the VSIX-capable workbench, not Agents/glass under ~/.config/Cursor.
        classic = resolve_cursor_user_data_dirs()
        if classic:
            return classic[0]
        return super().config_home()

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".cursor" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            # Cursor 3.5+ enforces extensions.trustedPublishers via state.vscdb.
            # Without "semcod" trusted, the VSIX installs but never activates.
            requires_trusted_publisher=True,
            # Cursor's plugin verification protocol differs from upstream VS Code
            # (it uses composer.sendToAgent and host-clipboard:wl-copy paths) —
            # the strict ack contract from DriveOrchestrator is *not* required.
            strict_plugin_ack_required=False,
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("cursor",)

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Cursor",)


register_strategy(CursorStrategy())

__all__ = [
    "CursorStrategy",
    "DEFAULT_CURSOR_CLASSIC_USER_DATA",
    "resolve_cursor_user_data_dirs",
]
