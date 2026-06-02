"""X11 Linux strategy.

Classical desktop environments (Xfce, MATE, classic GNOME, i3 on Xorg)
where ``xdotool`` reliably activates a window by name. ``wmctrl``
remains as a fallback because some users replace xdotool with it.
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
class X11LinuxStrategy(StaticOsIdentityMixin, OsStrategy):
    OS_ID = "linux-x11"
    OS_LABEL = "Linux / X11"

    def matches_current_environment(self) -> bool:
        import sys

        if sys.platform != "linux":
            return False
        if os.environ.get("WAYLAND_DISPLAY", "").strip():
            return False
        if os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland":
            return False
        return bool(os.environ.get("DISPLAY", "").strip())

    def capabilities(self) -> OsCapabilities:
        focus_methods: list[str] = []
        if shutil.which("xdotool"):
            focus_methods.append("xdotool")
        if shutil.which("wmctrl"):
            focus_methods.append("wmctrl")
        keyboard_tool: str | None = None
        if shutil.which("xdotool"):
            keyboard_tool = "xdotool"
        elif shutil.which("wtype"):
            keyboard_tool = "wtype"
        return OsCapabilities(
            can_focus_window=bool(focus_methods),
            can_inject_keys=keyboard_tool is not None,
            can_paste_clipboard=bool(shutil.which("xclip") or shutil.which("xsel")),
            focus_methods=tuple(focus_methods),
            keyboard_tool=keyboard_tool,
        )

    def focus_window(self, window_name_hints: tuple[str, ...]) -> FocusOutcome:
        if self._focus_via_xdotool(window_name_hints):
            return FocusOutcome(ok=True, method="xdotool")
        if self._focus_via_wmctrl(window_name_hints):
            return FocusOutcome(ok=True, method="wmctrl")
        return FocusOutcome(
            ok=False,
            detail="x11: neither xdotool nor wmctrl resolved a window matching the hints",
        )

    def inject_keys(self, sequence: KeySequence) -> bool:
        if shutil.which("xdotool"):
            return self._inject_via_xdotool(sequence)
        if shutil.which("wtype"):
            from koruos.strategies.wayland_linux import WaylandLinuxStrategy

            return WaylandLinuxStrategy().inject_keys(sequence)
        return False

    # ---- helpers ----------------------------------------------------------

    @staticmethod
    def _focus_via_xdotool(hints: tuple[str, ...]) -> bool:
        if not shutil.which("xdotool"):
            return False
        for hint in hints:
            proc = _run(["xdotool", "search", "--onlyvisible", "--name", hint])
            if proc.returncode != 0 or not proc.stdout.strip():
                proc = _run(["xdotool", "search", "--name", hint])
            if proc.returncode != 0 or not proc.stdout.strip():
                continue
            window_ids = [line.strip() for line in proc.stdout.splitlines() if line.strip()]
            if not window_ids:
                continue
            wid = window_ids[-1]
            activate = _run(["xdotool", "windowactivate", "--sync", wid])
            if activate.returncode == 0:
                time.sleep(0.2)
                return True
        return False

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
    def _inject_via_xdotool(sequence: KeySequence) -> bool:
        if sequence.literal_text is not None:
            return _run(["xdotool", "type", "--", sequence.literal_text]).returncode == 0
        if not sequence.key:
            return False
        combo = "+".join(list(sequence.modifiers) + [sequence.key])
        return _run(["xdotool", "key", "--", combo]).returncode == 0


register_os_strategy(X11LinuxStrategy())

__all__ = ["X11LinuxStrategy"]
