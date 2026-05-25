"""Wayland Linux strategy.

Wayland deliberately denies an arbitrary client from focusing another
client's window. That is why ``xdotool windowactivate`` is a no-op
here. We therefore order our focus tools:

1. ``wmctrl`` — works when the compositor exposes EWMH (KDE/Plasma,
   Sway with XWayland clients).
2. ``ydotool`` — works system-wide if the user has the daemon
   running, but only injects events, it cannot raise windows.
3. *Integrated terminal heuristic* — when ``koru auto`` is launched
   from inside the IDE's integrated terminal (``TERM_PROGRAM=vscode``),
   the IDE window already has focus and we can drive ``wtype`` against
   the current foreground app without an explicit raise.

Keyboard injection prefers ``wtype`` (native Wayland) over
``ydotool`` (requires systemd-uinput).
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass

from koruos.strategies.base import (
    FocusOutcome,
    KeySequence,
    OsCapabilities,
    OsStrategy,
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
class WaylandLinuxStrategy(OsStrategy):
    @property
    def id(self) -> str:
        return "linux-wayland"

    @property
    def label(self) -> str:
        return "Linux / Wayland"

    def matches_current_environment(self) -> bool:
        import sys

        if sys.platform != "linux":
            return False
        if os.environ.get("WAYLAND_DISPLAY", "").strip():
            return True
        return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"

    def capabilities(self) -> OsCapabilities:
        focus_methods: list[str] = []
        if shutil.which("wmctrl"):
            focus_methods.append("wmctrl")
        if self._term_program_is_vscode_family():
            focus_methods.append("integrated_terminal")
        keyboard_tool: str | None = None
        if shutil.which("wtype"):
            keyboard_tool = "wtype"
        elif shutil.which("ydotool"):
            keyboard_tool = "ydotool"
        return OsCapabilities(
            can_focus_window=bool(focus_methods),
            can_inject_keys=keyboard_tool is not None,
            can_paste_clipboard=bool(shutil.which("wl-copy")),
            focus_methods=tuple(focus_methods),
            keyboard_tool=keyboard_tool,
        )

    def focus_window(self, window_name_hints: tuple[str, ...]) -> FocusOutcome:
        if self._focus_via_wmctrl(window_name_hints):
            return FocusOutcome(ok=True, method="wmctrl")
        if self._term_program_is_vscode_family():
            return FocusOutcome(
                ok=True,
                method="integrated_terminal",
                detail="TERM_PROGRAM=vscode — IDE window already has focus",
            )
        return FocusOutcome(
            ok=False,
            detail=(
                "wayland: no usable focus tool. Install wmctrl (with XWayland "
                "support), set up ydotool, or launch `koru auto` from inside "
                "the IDE's integrated terminal so TERM_PROGRAM=vscode is set."
            ),
        )

    def inject_keys(self, sequence: KeySequence) -> bool:
        if shutil.which("wtype"):
            return self._inject_via_wtype(sequence)
        if shutil.which("ydotool"):
            return self._inject_via_ydotool(sequence)
        return False

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _focus_via_wmctrl(hints: tuple[str, ...]) -> bool:
        if not shutil.which("wmctrl"):
            return False
        for hint in hints:
            proc = _run(["wmctrl", "-a", hint])
            if proc.returncode == 0:
                time.sleep(0.2)
                return True
        return False

    @staticmethod
    def _inject_via_wtype(sequence: KeySequence) -> bool:
        argv: list[str] = ["wtype"]
        if sequence.literal_text is not None:
            argv.extend(["-t", sequence.literal_text])
        else:
            for modifier in sequence.modifiers:
                argv.extend(["-M", modifier])
            key = sequence.key or ""
            if len(key) == 1:
                argv.extend(["-p", key])
            else:
                argv.extend(["-k", key])
        return _run(argv).returncode == 0

    @staticmethod
    def _inject_via_ydotool(sequence: KeySequence) -> bool:
        if sequence.literal_text is not None:
            return _run(["ydotool", "type", sequence.literal_text]).returncode == 0
        return False


register_os_strategy(WaylandLinuxStrategy())

__all__ = ["WaylandLinuxStrategy"]
