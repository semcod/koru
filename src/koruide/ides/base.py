"""``IdeStrategy`` ABC — the single contract per IDE.

This is the **only** module other layers should reach for when they need
IDE-specific behavior.  All concrete strategies (``cursor.py``,
``vscode.py``, …) implement this interface so each IDE owns its full
lifecycle (detection, settings, plugin install, window reload, chat
interaction policy).
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(frozen=True)
class DetectionSignature:
    """Process-name patterns Koru uses to find the IDE on ``/proc``."""

    comm_patterns: tuple[str, ...]
    """Matched against ``/proc/<pid>/comm`` and the cmdline blob."""

    label: str
    """Human-readable name shown in logs/CLI."""

    exe_suffixes: tuple[str, ...] = ()
    """Optional preferred ``exe`` suffixes when picking the primary process."""


@dataclass(frozen=True)
class TerminalSignature:
    """Hints used to recognize when the running terminal is hosted by this IDE."""

    env_keys: tuple[str, ...] = ()
    """Env vars whose presence implies the IDE hosts the terminal."""

    env_value_substrings: tuple[str, ...] = ()
    """Lower-case substrings that, if found in any VS Code env value, indicate the IDE."""

    parent_comm_substrings: tuple[str, ...] = ()
    """Lower-case substrings to look for in parent-process comm/cmdline."""


@dataclass(frozen=True)
class PluginPolicy:
    """How this IDE consumes the Koru autopilot plugin (if at all)."""

    supports_vscode_extension: bool = False
    """True when the IDE can load the bundled VS Code-family VSIX."""

    requires_trusted_publisher: bool = False
    """True when the IDE enforces ``extensions.trustedPublishers``."""

    strict_plugin_ack_required: bool = False
    """True when ``DriveOrchestrator`` should demand the full strict plugin ack."""

    install_blocked_reason: str | None = None
    """Set on IDEs where the install CLI must refuse (JetBrains, Zed)."""


@dataclass(frozen=True)
class KeyboardPolicy:
    """Defaults the daemon uses when falling back to OS keyboard injection."""

    submit_key: str = "Return"
    """Key sequence used after the prompt is typed."""

    os_injector_tool_id: str | None = None
    """Profile key in ``ide-os-injector.json``. Defaults to the IDE id."""

    keyboard_fallback_default: bool = False
    """Whether OS-injector fallback is the *expected* path (e.g. JetBrains)."""


@dataclass(frozen=True)
class IdeAliases:
    """Aliases accepted by ``normalize_ide_id`` for this IDE."""

    canonical: str
    """The canonical id this strategy claims (e.g. ``"cursor"``)."""

    aliases: tuple[str, ...] = ()
    """Extra strings (lower-case, dash-normalized) that map to ``canonical``."""


class IdeStrategy(ABC):
    """Per-IDE knowledge object.

    Subclasses are **pure data + thin helpers** — no global mutable state,
    no cross-IDE branching. This is what lets us change Cursor without
    breaking VSCodium and vice-versa.
    """

    # ---- identity --------------------------------------------------------

    @property
    @abstractmethod
    def id(self) -> str:
        """Canonical Koru id, e.g. ``"cursor"``."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable label used in CLI/logs."""

    # ---- discovery -------------------------------------------------------

    @property
    @abstractmethod
    def detection(self) -> DetectionSignature:
        """How to recognize the IDE among running processes."""

    @property
    def terminal(self) -> TerminalSignature:
        """How to recognize this IDE as the host of an integrated terminal."""
        return TerminalSignature()

    @property
    def aliases(self) -> IdeAliases:
        """Aliases accepted by :func:`koruide.ide.normalize_ide_id`."""
        return IdeAliases(canonical=self.id)

    # ---- on-disk layout --------------------------------------------------

    def config_home(self) -> Path | None:
        """Per-user IDE config root (e.g. ``~/.config/Cursor``)."""
        return None

    def user_settings_path(self) -> Path | None:
        home = self.config_home()
        if home is None:
            return None
        return home / "User" / "settings.json"

    def workspace_settings_path(self, project: Path) -> Path | None:
        """Return ``<project>/.<ide>/settings.json`` (or equivalent)."""
        return None

    def state_vscdb_path(self) -> Path | None:
        home = self.config_home()
        if home is None:
            return None
        return home / "User" / "globalStorage" / "state.vscdb"

    def extensions_metadata_path(self) -> Path | None:
        """Return ``~/.<ide>/extensions/extensions.json`` if applicable."""
        return None

    # ---- plugin / chat policy --------------------------------------------

    @property
    def plugin(self) -> PluginPolicy:
        """Plugin compatibility policy."""
        return PluginPolicy()

    @property
    def keyboard(self) -> KeyboardPolicy:
        """Keyboard / OS-injector defaults."""
        return KeyboardPolicy(os_injector_tool_id=self.id)

    # ---- editor CLI / reload --------------------------------------------

    def editor_cli_candidates(self) -> tuple[str, ...]:
        """Executables to try when invoking the IDE from the command line."""
        return ()

    def window_name_hints(self) -> tuple[str, ...]:
        """Window-title substrings used by xdotool to focus the IDE window."""
        return (self.label,)

    # ---- repr ------------------------------------------------------------

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{type(self).__name__} id={self.id!r}>"


@dataclass(frozen=True)
class VscodeFamilyStrategy(IdeStrategy):
    """Common base strategy for VS Code-family IDEs (VS Code, VSCodium, Cursor, Windsurf, Antigravity)."""

    @property
    def config_folder_name(self) -> str:
        """Name of the configuration folder under XDG_CONFIG_HOME."""
        raise NotImplementedError

    @property
    def workspace_settings_folder_name(self) -> str:
        """Name of the workspace settings folder (usually .vscode, sometimes .cursor)."""
        return ".vscode"

    def config_home(self) -> Path | None:
        import os
        base = Path(
            os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config"),
        ).expanduser()
        return base / self.config_folder_name

    def workspace_settings_path(self, project: Path) -> Path | None:
        return project / self.workspace_settings_folder_name / "settings.json"

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
            os_injector_tool_id=self.id,
        )


__all__ = [
    "DetectionSignature",
    "IdeAliases",
    "IdeStrategy",
    "KeyboardPolicy",
    "PluginPolicy",
    "TerminalSignature",
    "VscodeFamilyStrategy",
]
