"""Antigravity IDE strategy."""

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
class AntigravityStrategy(VscodeFamilyStrategy):
    @property
    def id(self) -> str:
        return "antigravity"

    @property
    def label(self) -> str:
        return "Antigravity"

    @property
    def config_folder_name(self) -> str:
        return "Antigravity"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("antigravity",),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_value_substrings=("antigravity",),
            parent_comm_substrings=("antigravity",),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(
            canonical=self.id,
            aliases=("antigravity", "google-antigravity"),
        )

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".antigravity" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            requires_trusted_publisher=False,
            strict_plugin_ack_required=False,
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("antigravity",)

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Antigravity",)


register_strategy(AntigravityStrategy())

__all__ = ["AntigravityStrategy"]
