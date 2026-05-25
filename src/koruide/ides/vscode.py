"""Microsoft VS Code IDE strategy."""

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
class VscodeStrategy(VscodeFamilyStrategy):
    @property
    def id(self) -> str:
        return "vscode"

    @property
    def label(self) -> str:
        return "VS Code"

    @property
    def config_folder_name(self) -> str:
        return "Code"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("code", "code-insiders"),
            label=self.label,
        )

    @property
    def terminal(self) -> TerminalSignature:
        return TerminalSignature(
            env_keys=(
                "VSCODE_IPC_HOOK",
                "VSCODE_PID",
                "VSCODE_CWD",
                "TERM_PROGRAM",
            ),
            env_value_substrings=("visual studio code", "vscode"),
            parent_comm_substrings=("code", "code-insiders"),
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(
            canonical=self.id,
            aliases=("code", "code-insiders", "vs-code", "visual-studio-code"),
        )

    def extensions_metadata_path(self) -> Path | None:
        return Path.home() / ".vscode" / "extensions" / "extensions.json"

    def editor_cli_candidates(self) -> tuple[str, ...]:
        return ("code", "code-insiders")

    def window_name_hints(self) -> tuple[str, ...]:
        return ("Visual Studio Code",)


register_strategy(VscodeStrategy())

__all__ = ["VscodeStrategy"]
