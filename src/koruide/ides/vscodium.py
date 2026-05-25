"""VSCodium IDE strategy."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    KeyboardPolicy,
    PluginPolicy,
    VscodeFamilyStrategy,
)
from koruide.ides.registry import register_strategy


@dataclass(frozen=True)
class VscodiumStrategy(VscodeFamilyStrategy):
    @property
    def id(self) -> str:
        return "vscodium"

    @property
    def label(self) -> str:
        return "VSCodium"

    @property
    def config_folder_name(self) -> str:
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

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".vscode-oss" / "extensions" / "extensions.json"

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("codium", "vscodium")

    def window_name_hints(self) -> tuple[str, ...]:
        return ("VSCodium",)


register_strategy(VscodiumStrategy())

__all__ = ["VscodiumStrategy"]
