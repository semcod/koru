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
``ydotool`` (requires systemd-uinput) — except on GNOME/mutter, where
``wtype``'s virtual-keyboard-v1 path is routinely broken for modifier
chords. There ``ydotool`` (uinput-based, fully scancode-driven) is
required. Toggleable via :envvar:`KORU_OS_PREFER_YDOTOOL`.
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


# Linux input event scancodes used by ydotool. Only the subset we
# actually emit from the autopilot reload paths (Ctrl/Shift/Alt
# modifiers + alphanumeric + a few editor keys).
_YDOTOOL_KEY_CODES: dict[str, int] = {
    "ctrl": 29,
    "ctrl_l": 29,
    "ctrl_r": 97,
    "shift": 42,
    "shift_l": 42,
    "shift_r": 54,
    "alt": 56,
    "alt_l": 56,
    "alt_r": 100,
    "super": 125,
    "meta": 125,
    "win": 125,
    "return": 28,
    "enter": 28,
    "tab": 15,
    "esc": 1,
    "escape": 1,
    "space": 57,
    "backspace": 14,
    "delete": 111,
    "up": 103,
    "down": 108,
    "left": 105,
    "right": 106,
    "home": 102,
    "end": 107,
    "page_up": 104,
    "page_down": 109,
    "f1": 59,
    "f2": 60,
    "f3": 61,
    "f4": 62,
    "f5": 63,
    "f6": 64,
    "f7": 65,
    "f8": 66,
    "f9": 67,
    "f10": 68,
    "f11": 87,
    "f12": 88,
}
_YDOTOOL_LETTER_BASE = {
    "a": 30, "b": 48, "c": 46, "d": 32, "e": 18, "f": 33, "g": 34, "h": 35,
    "i": 23, "j": 36, "k": 37, "l": 38, "m": 50, "n": 49, "o": 24, "p": 25,
    "q": 16, "r": 19, "s": 31, "t": 20, "u": 22, "v": 47, "w": 17, "x": 45,
    "y": 21, "z": 44,
}
_YDOTOOL_DIGIT_BASE = {
    "1": 2, "2": 3, "3": 4, "4": 5, "5": 6,
    "6": 7, "7": 8, "8": 9, "9": 10, "0": 11,
}


def _scan_for_key(key: str | None) -> int | None:
    if not key:
        return None
    lowered = key.lower()
    if lowered in _YDOTOOL_KEY_CODES:
        return _YDOTOOL_KEY_CODES[lowered]
    if lowered in _YDOTOOL_LETTER_BASE:
        return _YDOTOOL_LETTER_BASE[lowered]
    if lowered in _YDOTOOL_DIGIT_BASE:
        return _YDOTOOL_DIGIT_BASE[lowered]
    return None


def _gnome_compositor() -> bool:
    """Heuristic: GNOME/mutter is the most common environment where
    ``wtype`` fails for modifier chords. The reload path then needs to
    short-circuit to ``ydotool`` even when ``wtype`` is on PATH."""

    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in desktop or "unity" in desktop:
        return True
    if os.environ.get("GNOME_DESKTOP_SESSION_ID"):
        return True
    return False


def _prefer_ydotool() -> bool:
    raw = os.environ.get("KORU_OS_PREFER_YDOTOOL", "").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        return True
    if raw in {"0", "false", "no", "off"}:
        return False
    return _gnome_compositor()


@dataclass(frozen=True)
class WaylandLinuxStrategy(StaticOsIdentityMixin, OsStrategy):
    OS_ID = "linux-wayland"
    OS_LABEL = "Linux / Wayland"

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
        has_wtype = bool(shutil.which("wtype"))
        has_ydotool = bool(shutil.which("ydotool"))
        prefer_ydotool = _prefer_ydotool()
        if prefer_ydotool and has_ydotool and self._inject_via_ydotool(sequence):
            return True
        if has_wtype and self._inject_via_wtype(sequence):
            return True
        if has_ydotool and not prefer_ydotool and self._inject_via_ydotool(sequence):
            return True
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
        proc = _run(argv)
        if proc.returncode != 0:
            return False
        stderr = (proc.stderr or "").lower()
        # GNOME/mutter often prints this but still exits 0, leaving the
        # caller to think the chord went through when it did not.
        if "virtual-keyboard-v1" in stderr or "doesn't support" in stderr:
            return False
        return True

    @staticmethod
    def _inject_via_ydotool(sequence: KeySequence) -> bool:
        if sequence.literal_text is not None:
            return _run(["ydotool", "type", "--", sequence.literal_text]).returncode == 0
        codes: list[int] = []
        for modifier in sequence.modifiers:
            scan = _scan_for_key(modifier)
            if scan is None:
                return False
            codes.append(scan)
        primary = _scan_for_key(sequence.key)
        if primary is None:
            return False
        # ydotool ``key`` syntax: ``<scancode>:<state>`` (1=press, 0=release).
        # Press modifiers (low → high), press primary, release primary,
        # release modifiers (high → low).
        argv: list[str] = ["ydotool", "key"]
        for code in codes:
            argv.append(f"{code}:1")
        argv.append(f"{primary}:1")
        argv.append(f"{primary}:0")
        for code in reversed(codes):
            argv.append(f"{code}:0")
        return _run(argv).returncode == 0


register_os_strategy(WaylandLinuxStrategy())

__all__ = ["WaylandLinuxStrategy"]
