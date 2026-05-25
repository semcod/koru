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
from collections.abc import Callable, Iterable
from dataclasses import dataclass, field

from koruide.config import cached_config
from koruide.injector_backends import type_with_backend
from koruide.injector_errors import InjectorError


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


def _unique_backend_names(names: Iterable[str]) -> list[str]:
    out: list[str] = []
    for name in names:
        if name not in out:
            out.append(name)
    return out


def _session_backend_order(session: str) -> list[str]:
    if session == "x11":
        preferred = ["xdotool"]
    elif session == "wayland":
        preferred = ["wtype", "ydotool"]
    elif not os.environ.get("DISPLAY"):
        preferred = ["wtype", "ydotool"]
    else:
        preferred = []
    return _unique_backend_names([*preferred, "xdotool", "wtype", "ydotool"])


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
    log: Callable[[str], None] | None = field(default=None)

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
            return self._forced_backend_candidates(forced)

        if self.log:
            self.log(f"injector: session={self.session or 'unknown'}")
        out = self._available_backend_candidates(_session_backend_order(self.session))
        if self.log:
            self.log(f"injector: candidate backends: {out}")
        return out

    def _forced_backend_candidates(self, forced: str) -> list[str]:
        if self.which(forced):
            if self.log:
                self.log(f"injector: forced backend={forced} (KORU_INJECTOR_BACKEND)")
            return [forced]
        if self.log:
            self.log(f"injector: forced backend={forced} not found, no backends available")
        return []

    def _available_backend_candidates(self, names: Iterable[str]) -> list[str]:
        out: list[str] = []
        for name in names:
            if not self.which(name):
                continue
            out.append(name)
            if self.log:
                self.log(f"injector: candidate backend {name} available")
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
        type_with_backend(self._call, self.log, backend, text, submit_key)

    def _type_text_backends(self) -> list[str]:
        backends = self._candidate_backends()
        if backends:
            return backends
        if self.log:
            self.log("injector: ERROR no backends available")
        raise InjectorError(
            "no keyboard injection backend found "
            "(install xdotool on X11 or wtype/ydotool on Wayland)",
        )

    def _log_type_text_request(self, text: str, ide: str, submit: bool) -> None:
        if not self.log:
            return
        text_preview = text[:100].replace("\n", "\\n") + ("..." if len(text) > 100 else "")
        self.log(
            f"injector: type_text called with {len(text)} chars, "
            f"ide={ide}, submit={submit}, preview='{text_preview}'"
        )

    def _dry_run_type_text_result(
        self,
        *,
        backend: str,
        text: str,
        submit: bool,
        submit_key: str | None,
    ) -> InjectionResult:
        if self.log:
            self.log("injector: dry-run mode, skipping actual typing")
        return InjectionResult(
            backend=backend,
            submitted=submit,
            dry_run=True,
            output=f"[dry-run] would type {len(text)} chars via {backend}"
            + (f" then press {submit_key}" if submit_key else ""),
        )

    def _try_type_text_backends(
        self,
        backends: list[str],
        text: str,
        submit: bool,
        submit_key: str | None,
    ) -> InjectionResult:
        errors: list[str] = []
        for backend in backends:
            if self.log:
                self.log(f"injector: trying backend={backend} ...")
            try:
                self._type_with_backend(backend, text, submit_key)
            except InjectorError as exc:
                if self.log:
                    self.log(f"injector: backend={backend} failed: {exc}")
                errors.append(f"{backend}: {exc}")
                continue
            if self.log:
                self.log(
                    f"injector: SUCCESS typed {len(text)} chars via {backend}, "
                    f"submit={submit}"
                )
            return InjectionResult(backend=backend, submitted=submit)
        raise self._all_type_backends_failed(errors)

    def _all_type_backends_failed(self, errors: list[str]) -> InjectorError:
        hint = (
            " Connect the koru autopilot extension for your IDE (preferred on Wayland), "
            "or install a working tool: `apt install wtype` (Sway/Hyprland), "
            "or fix ydotool/uinput per `koru autopilot doctor` / docs/autopilot-quickstart.md. "
            "Override order with KORU_INJECTOR_BACKEND=wtype|xdotool|ydotool."
        )
        if self.log:
            self.log(f"injector: ERROR all backends failed: {'; '.join(errors)}{hint}")
        return InjectorError("all keyboard injection backends failed: " + "; ".join(errors) + hint)

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
        self._log_type_text_request(text, ide, submit)
        backends = self._type_text_backends()
        submit_key = _submit_key_for(ide) if submit else None
        backend0 = backends[0]
        if self.log:
            self.log(
                f"injector: selected backend={backend0}, "
                f"submit_key={submit_key or 'none'}, ide={ide}, chars={len(text)}"
            )
        if dry_run:
            return self._dry_run_type_text_result(
                backend=backend0,
                text=text,
                submit=submit,
                submit_key=submit_key,
            )
        return self._try_type_text_backends(backends, text, submit, submit_key)

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
        if self.log:
            self.log(
                f"injector: submit_only via {backend0}, key={submit_key}"
            )
        if dry_run:
            return InjectionResult(
                backend=backend0,
                submitted=True,
                dry_run=True,
                output=f"[dry-run] would press {submit_key} via {backend0}",
            )
        errors: list[str] = []
        for backend in backends:
            if self.log:
                self.log(f"injector: trying submit via {backend} ...")
            try:
                self._type_with_backend(backend, "", submit_key)
                if self.log:
                    self.log(f"injector: submitted via {backend}")
                return InjectionResult(backend=backend, submitted=True)
            except InjectorError as exc:
                if self.log:
                    self.log(f"injector: submit via {backend} failed: {exc}")
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
        if self.log:
            cmd_preview = ' '.join(c if len(c) < 50 else f'{c[:47]}...' for c in cmd)
            self.log(f"injector: executing: {cmd_preview}")
        result = self.runner(cmd, None)
        if result.returncode != 0:
            stderr = (result.stderr or b"").decode("utf-8", errors="replace").strip()
            if self.log:
                self.log(
                    f"injector: command failed with code {result.returncode}: "
                    f"{stderr or '(no stderr)'}"
                )
            raise InjectorError(f"{cmd[0]} exited {result.returncode}: {stderr or '(no stderr)'}")
        if self.log:
            self.log(f"injector: command succeeded: {cmd[0]}")

__all__ = [
    "BackendStatus",
    "InjectionResult",
    "InjectorError",
    "Injector",
]
