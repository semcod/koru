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
from collections.abc import Callable
from dataclasses import dataclass, field

from koruide.config import cached_config


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


def _forced_injector_backend() -> str | None:
    """Optional ``KORU_INJECTOR_BACKEND=xdotool|wtype|ydotool`` — use only that tool."""
    raw = os.environ.get("KORU_INJECTOR_BACKEND", "").strip().lower()
    if raw in ("xdotool", "wtype", "ydotool"):
        return raw
    return None


def _ydotool_enter_keycode() -> str:
    """Keycode used by ydotool for submit.

    Default remains ``28`` (classic Enter), but some hosts/layout stacks map it
    differently. Override with ``KORU_YDOTOOL_ENTER_KEYCODE`` (e.g. ``96`` for KP Enter).
    """
    raw = os.environ.get("KORU_YDOTOOL_ENTER_KEYCODE", "").strip()
    if raw.isdigit():
        return raw
    return "28"


def _ydotool_submit_mode() -> str:
    """How to submit for ydotool: ``keycode`` (default), ``newline``, ``ctrl-enter``."""
    raw = os.environ.get("KORU_YDOTOOL_SUBMIT_MODE", "").strip().lower()
    if raw in ("newline", "nl", "linefeed"):
        return "newline"
    if raw in ("ctrl-enter", "ctrl_enter", "ctrl+enter"):
        return "ctrl-enter"
    return "keycode"


def _ydotool_ctrl_keycode() -> str:
    """Keycode used for Ctrl in ydotool chord submit mode."""
    raw = os.environ.get("KORU_YDOTOOL_CTRL_KEYCODE", "").strip()
    if raw.isdigit():
        return raw
    return "29"


def _extra_enter_count() -> int:
    """Optional extra submit presses after normal submit.

    Controlled by ``KORU_INJECTOR_EXTRA_ENTER`` (integer, default 0).
    """
    raw = os.environ.get("KORU_INJECTOR_EXTRA_ENTER", "").strip()
    if not raw:
        return 0
    try:
        value = int(raw)
    except ValueError:
        return 0
    return max(0, value)


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


def _default_runner(cmd: list[str], stdin: str | None) -> subprocess.CompletedProcess[bytes]:
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

    def _candidate_backends(self) -> list[str]:
        """Ordered injectors to try (session-aware), deduplicated.

        If ``KORU_INJECTOR_BACKEND`` is set, only that tool is attempted.
        """
        forced = _forced_injector_backend()
        if forced is not None:
            if self.which(forced):
                return [forced]
            return []

        out: list[str] = []

        def add(name: str) -> None:
            if self.which(name) and name not in out:
                out.append(name)

        if self.session == "x11":
            add("xdotool")
        elif self.session == "wayland":
            add("wtype")
            add("ydotool")
        elif not os.environ.get("DISPLAY"):
            add("wtype")
            add("ydotool")
        # Same fallbacks as legacy ``select_backend`` (cross-session last resort).
        add("xdotool")
        add("wtype")
        add("ydotool")
        return out

    def select_backend(self) -> str | None:
        """Pick the most reliable backend for the current session.

        Returns ``None`` when no backend is available.
        """
        candidates = self._candidate_backends()
        return candidates[0] if candidates else None

    def _type_with_backend(
        self,
        backend: str,
        text: str,
        submit_key: str | None,
    ) -> None:
        extra_enters = _extra_enter_count()
        if backend == "xdotool":
            self._call(["xdotool", "type", "--delay", "5", "--clearmodifiers", "--", text])
            if submit_key:
                self._call(["xdotool", "key", "--clearmodifiers", submit_key])
                for _ in range(extra_enters):
                    self._call(["xdotool", "key", "--clearmodifiers", "Return"])
        elif backend == "wtype":
            self._call(["wtype", "--", text])
            if submit_key:
                self._press_wtype(submit_key)
                for _ in range(extra_enters):
                    self._call(["wtype", "-k", "Return"])
        elif backend == "ydotool":
            enter_code = _ydotool_enter_keycode()
            submit_mode = _ydotool_submit_mode()
            ctrl_code = _ydotool_ctrl_keycode()
            self._call(["ydotool", "type", "--", text])
            if submit_key:
                if submit_mode == "newline":
                    self._call(["ydotool", "type", "--", "\n"])
                elif submit_mode == "ctrl-enter":
                    self._call(
                        [
                            "ydotool",
                            "key",
                            f"{ctrl_code}:1",
                            f"{enter_code}:1",
                            f"{enter_code}:0",
                            f"{ctrl_code}:0",
                        ],
                    )
                else:
                    self._call(["ydotool", "key", f"{enter_code}:1", f"{enter_code}:0"])
                for _ in range(extra_enters):
                    if submit_mode == "newline":
                        self._call(["ydotool", "type", "--", "\n"])
                    elif submit_mode == "ctrl-enter":
                        self._call(
                            [
                                "ydotool",
                                "key",
                                f"{ctrl_code}:1",
                                f"{enter_code}:1",
                                f"{enter_code}:0",
                                f"{ctrl_code}:0",
                            ],
                        )
                    else:
                        self._call(["ydotool", "key", f"{enter_code}:1", f"{enter_code}:0"])
        else:
            raise InjectorError(f"unreachable: unknown backend {backend!r}")

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
        backends = self._candidate_backends()
        if not backends:
            raise InjectorError(
                "no keyboard injection backend found "
                "(install xdotool on X11 or wtype/ydotool on Wayland)",
            )
        submit_key = _submit_key_for(ide) if submit else None
        backend0 = backends[0]
        if dry_run:
            return InjectionResult(
                backend=backend0,
                submitted=submit,
                dry_run=True,
                output=f"[dry-run] would type {len(text)} chars via {backend0}"
                + (f" then press {submit_key}" if submit_key else ""),
            )
        errors: list[str] = []
        for backend in backends:
            try:
                self._type_with_backend(backend, text, submit_key)
                return InjectionResult(backend=backend, submitted=submit)
            except InjectorError as exc:
                errors.append(f"{backend}: {exc}")
        hint = (
            " Connect the koru autopilot extension for your IDE (preferred on Wayland), "
            "or install a working tool: `apt install wtype` (Sway/Hyprland), "
            "or fix ydotool/uinput per `koru autopilot doctor` / docs/autopilot-quickstart.md. "
            "Override order with KORU_INJECTOR_BACKEND=wtype|xdotool|ydotool."
        )
        raise InjectorError("all keyboard injection backends failed: " + "; ".join(errors) + hint)

    def submit_only(
        self,
        *,
        ide: str = "default",
        dry_run: bool = False,
    ) -> InjectionResult:
        """Press only the IDE submit key via the selected backend."""
        backends = self._candidate_backends()
        if not backends:
            raise InjectorError(
                "no keyboard injection backend found "
                "(install xdotool on X11 or wtype/ydotool on Wayland)",
            )
        submit_key = _submit_key_for(ide)
        backend0 = backends[0]
        if dry_run:
            return InjectionResult(
                backend=backend0,
                submitted=True,
                dry_run=True,
                output=f"[dry-run] would press {submit_key} via {backend0}",
            )
        errors: list[str] = []
        for backend in backends:
            try:
                self._type_with_backend(backend, "", submit_key)
                return InjectionResult(backend=backend, submitted=True)
            except InjectorError as exc:
                errors.append(f"{backend}: {exc}")
        raise InjectorError("all keyboard submit backends failed: " + "; ".join(errors))

    # ----- internals -----------------------------------------------------

    def _probe_one(self, tool: str, *, session_required: str) -> BackendStatus:
        path = self.which(tool)
        if not path:
            return BackendStatus(
                name=tool,
                available=False,
                reason=f"{tool!r} is not in PATH",
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
            raise InjectorError(f"{cmd[0]} exited {result.returncode}: {stderr or '(no stderr)'}")

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
                "only single-modifier combos are supported",
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
