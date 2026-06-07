"""Windsurf IDE strategy."""

from __future__ import annotations

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


@dataclass(frozen=True)
class WindsurfStrategy(StaticIdeIdentityMixin, StaticVscodeFolderMixin, VscodeFamilyStrategy):
    IDE_ID = "windsurf"
    IDE_LABEL = "Windsurf"
    CONFIG_FOLDER_NAME = "Windsurf"

    @property
    def detection(self) -> DetectionSignature:
        # Windsurf now ships as "devin-desktop" (Cognition/Devin rebrand), so
        # match both the historical and current provider names.
        return DetectionSignature(
            comm_patterns=("windsurf", "devin-desktop"),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_value_substrings=("windsurf", "devin"),
            parent_comm_substrings=("windsurf", "devin-desktop"),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(canonical=self.id, aliases=("windsurf", "devin", "devin-desktop"))

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".windsurf" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            requires_trusted_publisher=False,
            strict_plugin_ack_required=False,
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("windsurf",)

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Windsurf",)


register_strategy(WindsurfStrategy())

__all__ = ["WindsurfStrategy"]
