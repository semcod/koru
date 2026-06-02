"""``OsStrategy`` contract.

Mirrors the :class:`koruide.ides.base.IdeStrategy` pattern: a single ABC
that captures *all* OS-level behaviour Koru needs (window focus,
keyboard injection, clipboard paste). Higher layers must not branch on
``sys.platform``, ``WAYLAND_DISPLAY``, ``shutil.which("xdotool")`` —
they ask the strategy registry which is the source of truth.
"""

from __future__ import annotations

import os
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import ClassVar


@dataclass(frozen=True)
class OsCapabilities:
    """Which OS-level tools are usable in the current session.

    Strategies populate this on demand; consumers can short-circuit
    when, e.g., neither a focus tool nor an integrated-terminal
    heuristic is available.
    """

    can_focus_window: bool = False
    can_inject_keys: bool = False
    can_paste_clipboard: bool = False
    focus_methods: tuple[str, ...] = ()
    """Identifiers of usable focus methods, e.g. ``("xdotool", "integrated_terminal")``."""
    keyboard_tool: str | None = None
    """Resolved keyboard-injection tool id (``wtype``/``xdotool``/``ydotool``/``osascript`` …)."""


@dataclass(frozen=True)
class FocusOutcome:
    """Result of ``OsStrategy.focus_window``.

    ``method`` is empty when ``ok`` is ``False`` so callers can build
    deterministic error messages (no ambiguous "unknown").
    """

    ok: bool
    method: str = ""
    detail: str = ""


@dataclass(frozen=True)
class KeySequence:
    """Portable key sequence description used by :meth:`OsStrategy.inject_keys`.

    ``modifiers`` is the set of modifier names (``ctrl``, ``shift``,
    ``alt``, ``meta``) and ``key`` is the printable / named key
    (``p``, ``Return``, ``Escape``). ``literal_text`` is mutually
    exclusive with ``key`` and is used for typing arbitrary strings.
    """

    modifiers: tuple[str, ...] = field(default_factory=tuple)
    key: str | None = None
    literal_text: str | None = None

    def __post_init__(self) -> None:
        if self.key and self.literal_text:
            raise ValueError("KeySequence: pass either key or literal_text, not both")
        if not self.key and not self.literal_text:
            raise ValueError("KeySequence: require at least one of key/literal_text")


class OsStrategy(ABC):
    """Per-OS knowledge object.

    The constructor must be argument-less so strategies can be
    instantiated and registered at import time. Subclasses are
    expected to be **frozen dataclasses** for cheap equality and to
    discourage hidden mutable state.
    """

    @property
    @abstractmethod
    def id(self) -> str:
        """Canonical identifier, e.g. ``"linux-wayland"``."""

    @property
    @abstractmethod
    def label(self) -> str:
        """Human-readable label used in operator logs."""

    @abstractmethod
    def matches_current_environment(self) -> bool:
        """``True`` when this strategy fits the running process' environment.

        Implementations consult ``sys.platform``, environment variables
        like ``WAYLAND_DISPLAY``/``DISPLAY``, or platform-specific APIs.
        The registry uses this to auto-resolve the active strategy.
        """

    @abstractmethod
    def capabilities(self) -> OsCapabilities:
        """Discover which OS tools are actually available right now."""

    @abstractmethod
    def focus_window(self, window_name_hints: tuple[str, ...]) -> FocusOutcome:
        """Bring the IDE window matching one of ``window_name_hints`` to the foreground."""

    @abstractmethod
    def inject_keys(self, sequence: KeySequence) -> bool:
        """Inject a single key sequence at the current focus."""

    # ---- shared helpers ----------------------------------------------------

    @staticmethod
    def _term_program_is_vscode_family() -> bool:
        """``TERM_PROGRAM=vscode`` is exported by Cursor/VS Code/VSCodium/Windsurf/Antigravity.

        Centralised here so individual OS strategies don't re-implement
        the integrated-terminal heuristic. The IDE axis decides whether
        to trust it for a given IDE id.
        """
        return os.environ.get("TERM_PROGRAM", "").strip().lower() == "vscode"

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"<{type(self).__name__} id={self.id!r}>"


class StaticOsIdentityMixin:
    """Provide ``id``/``label`` from class-level constants."""

    OS_ID: ClassVar[str] = ""
    OS_LABEL: ClassVar[str] = ""

    @property
    def id(self) -> str:
        return self.OS_ID

    @property
    def label(self) -> str:
        return self.OS_LABEL


__all__ = [
    "FocusOutcome",
    "KeySequence",
    "OsCapabilities",
    "OsStrategy",
    "StaticOsIdentityMixin",
]
