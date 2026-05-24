"""Zed editor strategy."""

from __future__ import annotations

from dataclasses import dataclass

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    IdeStrategy,
    KeyboardPolicy,
    PluginPolicy,
)
from koruide.ides.registry import register_strategy

_ZED_INSTALL_BLOCKED = (
    "zed does not support the VS Code VSIX plugin; use OS-injector keyboard path"
)


@dataclass(frozen=True)
class ZedStrategy(IdeStrategy):
    @property
    def id(self) -> str:
        return "zed"

    @property
    def label(self) -> str:
        return "Zed"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=("zed",),
            label=self.label,
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(
            canonical=self.id,
            aliases=("zed", "zed-editor", "zed-preview"),
        )

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=False,
            install_blocked_reason=_ZED_INSTALL_BLOCKED,
        )

    @property
    def keyboard(self) -> KeyboardPolicy:
        return KeyboardPolicy(
            submit_key="Return",
            os_injector_tool_id="zed",
            keyboard_fallback_default=True,
        )


register_strategy(ZedStrategy())

__all__ = ["ZedStrategy"]
