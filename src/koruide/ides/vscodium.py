"""VSCodium IDE strategy."""

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
)
from koruide.ides.registry import register_strategy


@dataclass(frozen=True)
class VscodiumStrategy(IdeStrategy):
    @property
    def id(self) -> str:
        return "vscodium"

    @property
    def label(self) -> str:
        return "VSCodium"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("codium", "vscodium", "code-oss"),
            label=self.label,
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(
            canonical=self.id,
            aliases=("codium", "vscodium", "code-oss", "code oss"),
        )

    def config_home(self) -> Path | None:
        base = Path(
            os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"),
        ).expanduser()
        return base / "VSCodium"

    def workspace_settings_path(self, project: Path) -> Path | None:
        return project / ".vscode" / "settings.json"

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".vscode-oss" / "extensions" / "extensions.json"

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=True,
            requires_trusted_publisher=True,
            strict_plugin_ack_required=True,
        )

    @property
    def keyboard(self) -> KeyboardPolicy:
        return KeyboardPolicy(
            submit_key="Return",
            os_injector_tool_id="vscodium",
        )

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("codium", "vscodium")

    def window_name_hints(self) -> tuple[str, ...]:
        return ("VSCodium",)


register_strategy(VscodiumStrategy())

__all__ = ["VscodiumStrategy"]
