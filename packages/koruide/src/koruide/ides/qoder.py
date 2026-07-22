"""Qoder IDE strategy (VS Code fork; loads the umbrella vscode VSIX)."""

from __future__ import annotations

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
class QoderStrategy(StaticIdeIdentityMixin, StaticVscodeFolderMixin, VscodeFamilyStrategy):
    IDE_ID = "qoder"
    IDE_LABEL = "Qoder"
    CONFIG_FOLDER_NAME = "Qoder"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("qoder",),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_value_substrings=("qoder",),
            parent_comm_substrings=("qoder",),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(canonical=self.id, aliases=("qoder", "qodercli"))

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".qoder" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            requires_trusted_publisher=False,
            strict_plugin_ack_required=False,
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("qoder", "qodercli")

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Qoder",)


register_strategy(QoderStrategy())

__all__ = ["QoderStrategy"]
