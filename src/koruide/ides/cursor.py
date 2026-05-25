"""Cursor IDE strategy.

This module is the **single source of truth** for everything Koru knows about
Cursor: how to detect it, where its settings/state live, that Cursor enforces
``extensions.trustedPublishers``, how to reload its window, etc.

Other layers (``koruide.ide``, ``koru.ide_adapters``, ``koru.ide_reload``)
delegate Cursor-specific decisions here. Changing Cursor behavior happens in
this file only — VSCodium, Windsurf, Antigravity, etc. cannot be affected.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    KeyboardPolicy,
    PluginPolicy,
    TerminalSignature,
    VscodeFamilyStrategy,
)
from koruide.ides.registry import register_strategy


@dataclass(frozen=True)
class CursorStrategy(VscodeFamilyStrategy):
    """Strategy for Cursor (VS Code-fork by Anysphere)."""

    @property
    def id(self) -> str:
        return "cursor"

    @property
    def label(self) -> str:
        return "Cursor"

    @property
    def config_folder_name(self) -> str:
        return "Cursor"

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

__all__ = ["CursorStrategy"]
