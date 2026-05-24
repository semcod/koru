"""JetBrains IDE family strategy (PyCharm, IDEA, WebStorm, …)."""

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

_JETBRAINS_INSTALL_BLOCKED = (
    "jetbrains plugin install is not supported via `koru autopilot install-plugin`; "
    "use the JetBrains plugin scaffold or OS-injector keyboard path"
)


@dataclass(frozen=True)
class JetbrainsStrategy(IdeStrategy):
    @property
    def id(self) -> str:
        return "jetbrains"

    @property
    def label(self) -> str:
        return "JetBrains IDE"

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(
            comm_patterns=(
                "idea",
                "pycharm",
                "webstorm",
                "phpstorm",
                "goland",
                "clion",
                "rubymine",
            ),
            label=self.label,
        )

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(
            canonical=self.id,
            aliases=(
                "pycharm",
                "idea",
                "intellij",
                "jetbrains",
                "webstorm",
                "phpstorm",
                "goland",
                "clion",
                "rubymine",
            ),
        )

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=False,
            install_blocked_reason=_JETBRAINS_INSTALL_BLOCKED,
        )

    @property
    def keyboard(self) -> KeyboardPolicy:
        return KeyboardPolicy(
            submit_key="ctrl+Return",
            os_injector_tool_id="jetbrains",
            keyboard_fallback_default=True,
        )


register_strategy(JetbrainsStrategy())

__all__ = ["JetbrainsStrategy"]
