"""Fallback strategy synthesized from the legacy tables.

Until every IDE has its own dedicated module, ``koruide.ide`` keeps the
historical ``_IDE_SIGNATURES`` / ``_IDE_ALIASES`` dicts as the source of
truth. This module wraps that data into an :class:`IdeStrategy` so the
new contract can be relied upon today, even for IDEs that have not been
extracted yet (vscode, vscodium, windsurf, antigravity, jetbrains, zed).
"""

from __future__ import annotations

from dataclasses import dataclass

from koruide.ides.base import (
    DetectionSignature,
    IdeAliases,
    IdeStrategy,
    KeyboardPolicy,
    PluginPolicy,
)


@dataclass(frozen=True)
class _LegacyFallback(IdeStrategy):
    """Adapter wrapping the legacy ``_IDE_SIGNATURES`` data for one IDE."""

    _id: str
    _label: str
    _comm: tuple[str, ...]
    _aliases: tuple[str, ...] = ()
    _supports_vscode_plugin: bool = False
    _requires_trusted_publisher: bool = False
    _strict_plugin_ack_required: bool = False
    _install_blocked_reason: str | None = None
    _submit_key: str = "Return"
    _keyboard_fallback_default: bool = False

    @property
    def id(self) -> str:
        return self._id

    @property
    def label(self) -> str:
        return self._label

    @property
    def detection(self) -> DetectionSignature:
        return DetectionSignature(comm_patterns=self._comm, label=self._label)

    @property
    def aliases(self) -> IdeAliases:
        return IdeAliases(canonical=self._id, aliases=self._aliases)

    @property
    def plugin(self) -> PluginPolicy:
        return PluginPolicy(
            supports_vscode_extension=self._supports_vscode_plugin,
            requires_trusted_publisher=self._requires_trusted_publisher,
            strict_plugin_ack_required=self._strict_plugin_ack_required,
            install_blocked_reason=self._install_blocked_reason,
        )

    @property
    def keyboard(self) -> KeyboardPolicy:
        return KeyboardPolicy(
            submit_key=self._submit_key,
            os_injector_tool_id=self._id,
            keyboard_fallback_default=self._keyboard_fallback_default,
        )


def build_fallback_strategy(
    *,
    ide_id: str,
    label: str,
    comm_patterns: tuple[str, ...],
    aliases: tuple[str, ...] = (),
    supports_vscode_extension: bool = False,
    requires_trusted_publisher: bool = False,
    strict_plugin_ack_required: bool = False,
    install_blocked_reason: str | None = None,
    submit_key: str = "Return",
    keyboard_fallback_default: bool = False,
) -> IdeStrategy:
    """Construct a no-frills strategy for IDEs not yet extracted to their own module."""
    return _LegacyFallback(
        _id=ide_id,
        _label=label,
        _comm=comm_patterns,
        _aliases=aliases,
        _supports_vscode_plugin=supports_vscode_extension,
        _requires_trusted_publisher=requires_trusted_publisher,
        _strict_plugin_ack_required=strict_plugin_ack_required,
        _install_blocked_reason=install_blocked_reason,
        _submit_key=submit_key,
        _keyboard_fallback_default=keyboard_fallback_default,
    )


__all__ = ["build_fallback_strategy"]
