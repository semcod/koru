"""Keyboard / clipboard injection backends for autopilot.

The :class:`Injector` is a tiny strategy picker. It detects which
tools are available on the system (xdotool / wtype / ydotool /
wl-copy / xclip) and exposes a single :meth:`Injector.type_text`
method that does the right thing.

We deliberately keep this synchronous and stdlib-only: ``subprocess``
+ ``shutil.which`` are enough. The :class:`Injector` can be
instantiated with explicit ``backends`` for testing.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from dataclasses import dataclass, field
from typing import Callable

from .config import cached_config


def _submit_key_for(ide: str) -> str:
    """Resolve the submit shortcut for ``ide``.

    Looks up the user's ``~/.config/koru/autopilot.toml`` first (R7);
    falls back to the built-in defaults defined in
    :mod:`koru.autopilot.config`. JetBrains uses ``ctrl+Return``; VS
    Code, Windsurf, Cursor and Zed all submit on a plain ``Return``.
    """
    return cached_config().submit_key_for(ide)


def _which(name: str) -> str | None:
    return shutil.which(name)


def _session_type() -> str:
    """Return ``"wayland"``, ``"x11"`` or ``""`` based on env."""
    sess = os.environ.get("XDG_SESSION_TYPE", "").lower()
    if sess in ("wayland", "x11"):
        return sess
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return ""


@dataclass
class BackendStatus:
    """Result of probing a single backend."""

    name: str
    available: bool
    reason: str = ""

    def to_dict(self) -> dict[str, object]:
        return {"name": self.name, "available": self.available, "reason": self.reason}


@dataclass
class InjectionResult:
    backend: str
    submitted: bool
    dry_run: bool = False
    output: str = ""

    def to_dict(self) -> dict[str, object]:
        return {
            "backend": self.backend,
            "submitted": self.submitted,
            "dry_run": self.dry_run,
            "output": self.output,
        }


class InjectorError(RuntimeError):
    """No usable backend, or the backend call failed."""


# A backend is a callable taking (text, submit_key, runner) -> str.
# ``runner`` is a stub for subprocess.run used by tests.
Runner = Callable[[list[str], str | None], "subprocess.CompletedProcess[bytes]"]


def _default_runner(cmd: list[str], stdin: str | None) -> "subprocess.CompletedProcess[bytes]":
    return subprocess.run(  # noqa: S603 — caller passes a fixed argv
        cmd,
        input=stdin.encode("utf-8") if stdin is not None else None,
        capture_output=True,
        check=False,
    )


@dataclass
class Injector:
    """Pick the best available backend and type text through it.

    Parameters
    ----------
    session:
        Override desktop session ("wayland", "x11"). Empty string =
        autodetect from environment.
    which:
        Override :func:`shutil.which` (tests inject a stub).
    runner:
        Override :func:`subprocess.run`.
    """

    session: str = field(default_factory=_session_type)
    which: Callable[[str], str | None] = staticmethod(_which)
    runner: Runner = field(default=_default_runner)

    # ----- public API ----------------------------------------------------

    def probe(self) -> list[BackendStatus]:
        """Return per-backend availability — used by ``autopilot doctor``."""
        return [
            self._probe_one("xdotool", session_required="x11"),
            self._probe_one("wtype", session_required="wayland"),
            self._probe_one("ydotool", session_required="wayland"),
            self._probe_one("wl-copy", session_required="wayland"),
            self._probe_one("xclip", session_required="x11"),
        ]

    def select_backend(self) -> str | None:
        """Pick the most reliable backend for the current session.

        Returns ``None`` when no backend is available.
        """
        # X11 → xdotool wins (mature, no permissions issues).
        if self.session == "x11" and self.which("xdotool"):
            return "xdotool"
        # Wayland → wtype works in sway/Hyprland; ydotool needs uinput
        # but works on gnome.
        if self.session == "wayland":
            if self.which("wtype"):
                return "wtype"
            if self.which("ydotool"):
                return "ydotool"
        # Last resort: clipboard + keystroke. Requires a key-injector
        # to send ctrl+v afterwards, so we still need xdotool or wtype.
        if self.which("xdotool"):
            return "xdotool"
        if self.which("wtype"):
            return "wtype"
        return None

    def type_text(
        self,
        text: str,
        *,
        ide: str = "default",
        submit: bool = True,
        dry_run: bool = False,
    ) -> InjectionResult:
        """Type ``text`` and optionally press the IDE's submit key.

        Raises :class:`InjectorError` when no backend is available.
        """
        if not text:
            raise InjectorError("refusing to inject empty text")
        backend = self.select_backend()
        if backend is None:
            raise InjectorError(
                "no keyboard injection backend found "
                "(install xdotool on X11 or wtype/ydotool on Wayland)"
            )
        submit_key = _submit_key_for(ide) if submit else None
        if dry_run:
            return InjectionResult(
                backend=backend,
                submitted=submit,
                dry_run=True,
                output=f"[dry-run] would type {len(text)} chars via {backend}"
                + (f" then press {submit_key}" if submit_key else ""),
            )
        if backend == "xdotool":
            self._call(["xdotool", "type", "--delay", "5", "--clearmodifiers", "--", text])
            if submit_key:
                self._call(["xdotool", "key", "--clearmodifiers", submit_key])
        elif backend == "wtype":
            self._call(["wtype", "--", text])
            if submit_key:
                # wtype uses ``-k`` for key names and lowercase + comma syntax
                # for chords. ``Return`` works as-is; ``ctrl+Return`` requires
                # ``-M ctrl -k Return -m ctrl``.
                self._press_wtype(submit_key)
        elif backend == "ydotool":
            # ydotool's ``type`` reads from argv directly.
            self._call(["ydotool", "type", "--", text])
            if submit_key:
                # ydotool key syntax uses ``KEY:1`` press / ``KEY:0`` release.
                # For the simple ``Return`` case we tap ENTER.
                self._call(["ydotool", "key", "28:1", "28:0"])  # 28 = KEY_ENTER
        else:
            raise InjectorError(f"unreachable: unknown backend {backend!r}")
        return InjectionResult(backend=backend, submitted=submit)

    # ----- internals -----------------------------------------------------

    def _probe_one(self, tool: str, *, session_required: str) -> BackendStatus:
        path = self.which(tool)
        if not path:
            return BackendStatus(
                name=tool, available=False, reason=f"{tool!r} is not in PATH",
            )
        if self.session and session_required and self.session != session_required:
            return BackendStatus(
                name=tool,
                available=False,
                reason=f"requires {session_required} session, current is {self.session!r}",
            )
        return BackendStatus(name=tool, available=True, reason=path)

    def _call(self, cmd: list[str]) -> None:
        result = self.runner(cmd, None)
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            raise InjectorError(
                f"{cmd[0]} exited {result.returncode}: {stderr or '(no stderr)'}"
            )

    def _press_wtype(self, combo: str) -> None:
        # Translate e.g. ``ctrl+Return`` into the wtype invocation.
        # R3: refuse multi-modifier combos explicitly — the press /
        # release ordering required for ``ctrl+shift+x`` differs per
        # compositor and would silently misbehave under the previous
        # naive implementation. Better to fail loud and let the caller
        # set a different key in ``~/.config/koru/autopilot.toml``.
        parts = combo.split("+")
        key = parts[-1]
        modifiers = parts[:-1]
        if len(modifiers) > 1:
            raise InjectorError(
                f"wtype submit key {combo!r} has {len(modifiers)} modifiers; "
                "only single-modifier combos are supported"
            )
        argv = ["wtype"]
        for m in modifiers:
            argv += ["-M", m]
        argv += ["-k", key]
        for m in reversed(modifiers):
            argv += ["-m", m]
        self._call(argv)


__all__ = [
    "BackendStatus",
    "InjectionResult",
    "InjectorError",
    "Injector",
]
