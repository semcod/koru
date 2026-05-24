"""Per-IDE control strategy for autopilot routing.

This module is intentionally small and pure.  The daemon should ask it how an
IDE is controlled instead of scattering ``if ide == ...`` checks across plugin
ack, fallback and strict-verification paths.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class IdeControlStrategy:
    ide: str
    transport: str
    requires_plugin: bool
    allow_keyboard_fallback_after_plugin_ack: bool
    strict_ack_supported: bool


_PLUGIN_SOCKET_IDES = {"cursor", "vscode", "vscodium", "windsurf", "antigravity"}


_STRATEGIES: dict[str, IdeControlStrategy] = {
    "cursor": IdeControlStrategy(
        ide="cursor",
        transport="vscode-family-plugin",
        requires_plugin=True,
        allow_keyboard_fallback_after_plugin_ack=False,
        strict_ack_supported=True,
    ),
    "vscode": IdeControlStrategy(
        ide="vscode",
        transport="vscode-family-plugin",
        requires_plugin=True,
        allow_keyboard_fallback_after_plugin_ack=False,
        strict_ack_supported=True,
    ),
    "vscodium": IdeControlStrategy(
        ide="vscodium",
        transport="vscode-family-plugin",
        requires_plugin=True,
        allow_keyboard_fallback_after_plugin_ack=False,
        strict_ack_supported=True,
    ),
    "windsurf": IdeControlStrategy(
        ide="windsurf",
        transport="windsurf-native-plugin",
        requires_plugin=True,
        allow_keyboard_fallback_after_plugin_ack=False,
        strict_ack_supported=False,
    ),
    "antigravity": IdeControlStrategy(
        ide="antigravity",
        transport="antigravity-native-plugin",
        requires_plugin=True,
        allow_keyboard_fallback_after_plugin_ack=False,
        strict_ack_supported=False,
    ),
    "jetbrains": IdeControlStrategy(
        ide="jetbrains",
        transport="keyboard-os-injector",
        requires_plugin=False,
        allow_keyboard_fallback_after_plugin_ack=True,
        strict_ack_supported=False,
    ),
    "zed": IdeControlStrategy(
        ide="zed",
        transport="keyboard-os-injector",
        requires_plugin=False,
        allow_keyboard_fallback_after_plugin_ack=True,
        strict_ack_supported=False,
    ),
}


def ide_control_strategy(ide: str | None) -> IdeControlStrategy:
    key = (ide or "auto").strip().lower()
    if key in _STRATEGIES:
        return _STRATEGIES[key]
    return IdeControlStrategy(
        ide=key,
        transport="keyboard-os-injector",
        requires_plugin=False,
        allow_keyboard_fallback_after_plugin_ack=True,
        strict_ack_supported=False,
    )


def plugin_socket_ide_ids() -> frozenset[str]:
    return frozenset(_PLUGIN_SOCKET_IDES)


__all__ = ["IdeControlStrategy", "ide_control_strategy", "plugin_socket_ide_ids"]
