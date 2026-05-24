"""Antigravity IDE strategy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    IdeStrategy,
    KeyboardPolicy,
    PluginPolicy,
    TerminalSignature,
)
from koruide.ides.registry import register_strategy


@dataclass(frozen=True)
class AntigravityStrategy(IdeStrategy):
    @property
    def id(self) -> str:
        return "antigravity"

    @property
    def label(self) -> str:
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

    def config_home(self) -> Path | None:
        base = Path(
            os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"),
        ).expanduser()
        return base / "Antigravity"

    def workspace_settings_path(self, project: Path) -> Path | None:
        return project / ".vscode" / "settings.json"

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".antigravity" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            requires_trusted_publisher=False,
            strict_plugin_ack_required=False,
        )

    @property
    def keyboard(self) -> KeyboardPolicy:
        return KeyboardPolicy(
            submit_key="Return",
            os_injector_tool_id="antigravity",
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("antigravity",)

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Antigravity",)


register_strategy(AntigravityStrategy())

__all__ = ["AntigravityStrategy"]
