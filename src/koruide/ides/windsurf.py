"""Windsurf IDE strategy."""

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
class WindsurfStrategy(VscodeFamilyStrategy):
    @property
    def id(self) -> str:
        return "windsurf"

    @property
    def label(self) -> str:
        return "Windsurf"

    @property
    def config_folder_name(self) -> str:
        return "Windsurf"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("windsurf",),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_value_substrings=("windsurf",),
            parent_comm_substrings=("windsurf",),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(canonical=self.id, aliases=("windsurf",))

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
