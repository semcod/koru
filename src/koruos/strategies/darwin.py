"""macOS strategy.

The intended implementation uses ``osascript`` for window activation
(``tell application "Cursor" to activate``) and ``cliclick`` /
AppleScript ``keystroke`` for keyboard injection. We ship a minimal
version today; concrete behaviour can grow as macOS users adopt Koru.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass

from koruos.strategies.base import (
    FocusOutcome,
    KeySequence,
    OsCapabilities,
    OsStrategy,
    StaticOsIdentityMixin,
)
from koruos.strategies.registry import register_os_strategy


def _run(argv: list[str], *, timeout: float = 10.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


@dataclass(frozen=True)
class DarwinStrategy(StaticOsIdentityMixin, OsStrategy):
    OS_ID = "darwin"
    OS_LABEL = "macOS"

    def matches_current_environment(self) -> bool:
        return sys.platform == "darwin"

    def capabilities(self) -> OsCapabilities:
        osascript = shutil.which("osascript")
        focus_methods = ("osascript",) if osascript else ()
        keyboard_tool: str | None = None
        if shutil.which("cliclick"):
            keyboard_tool = "cliclick"
        elif osascript:
            keyboard_tool = "osascript"
        return OsCapabilities(
            can_focus_window=bool(osascript),
            can_inject_keys=keyboard_tool is not None,
            can_paste_clipboard=bool(shutil.which("pbpaste")),
            focus_methods=focus_methods,
            keyboard_tool=keyboard_tool,
        )

    def focus_window(self, window_name_hints: tuple[str, ...]) -> FocusOutcome:
        if not shutil.which("osascript"):
            return FocusOutcome(ok=False, detail="darwin: osascript not on PATH")
        for hint in window_name_hints:
            script = f'tell application "{hint}" to activate'
            if _run(["osascript", "-e", script]).returncode == 0:
                return FocusOutcome(ok=True, method="osascript")
        return FocusOutcome(
            ok=False,
            detail="darwin: no application activated for the given hints",
        )

    def inject_keys(self, sequence: KeySequence) -> bool:
        # Concrete AppleScript keystroke implementation is deferred until a
        # macOS user requests it; we surface that explicitly rather than
        # silently no-op'ing so callers can pick a different path.
        return False


register_os_strategy(DarwinStrategy())

__all__ = ["DarwinStrategy"]
