"""Windows strategy (PowerShell + SendInput placeholder).

Koru's primary Windows path remains MCP / WSL; we register a strategy
so the registry resolves cleanly there. Future iterations can wire
``pywin32`` or ``pyautogui``.
"""

from __future__ import annotations

import sys
from dataclasses import dataclass

from koruos.strategies.base import (
    FocusOutcome,
    KeySequence,
    OsCapabilities,
    OsStrategy,
)
from koruos.strategies.registry import register_os_strategy


@dataclass(frozen=True)
class WindowsStrategy(OsStrategy):
    @property
    def id(self) -> str:
        return "windows"

    @property
    def label(self) -> str:
        return "Windows"

    def matches_current_environment(self) -> bool:
        return sys.platform.startswith("win")

    def capabilities(self) -> OsCapabilities:
        return OsCapabilities()

    def focus_window(self, window_name_hints: tuple[str, ...]) -> FocusOutcome:
        return FocusOutcome(
            ok=False,
            detail=(
                "windows: native window focus not yet implemented; use the "
                "Cursor / VS Code CLI to launch with --reuse-window or run "
                "koru from inside the IDE terminal"
            ),
        )

    def inject_keys(self, sequence: KeySequence) -> bool:
        return False


register_os_strategy(WindowsStrategy())

__all__ = ["WindowsStrategy"]
