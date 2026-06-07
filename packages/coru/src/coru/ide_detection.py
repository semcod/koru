"""IDE / terminal context detection extracted from ``coru.cli``.

This module collects best-effort heuristics that determine which IDE (if any)
owns the current shell.  It is used by the ``coru`` CLI so that commands like
``coru auto`` can default to the correct IDE lane.
"""

from __future__ import annotations

import os
from pathlib import Path

_VALID_AUTOPILOT_IDES = frozenset(
    {"auto", "vscode", "vscodium", "cursor", "windsurf", "jetbrains", "zed", "antigravity"}
)

_WORKSPACE_SETTINGS_BY_IDE: dict[str, Path] = {
    "cursor": Path(".cursor") / "settings.json",
    "vscode": Path(".vscode") / "settings.json",
    "vscodium": Path(".vscode-oss") / "settings.json",
    "windsurf": Path(".windsurf") / "settings.json",
    "antigravity": Path(".antigravity") / "settings.json",
}


def _ide_from_vscode_pid() -> str | None:
    pid = (os.environ.get("VSCODE_PID") or "").strip()
    if not pid.isdigit():
        return None
    exe_path = Path(f"/proc/{pid}/exe")
    try:
        target = str(exe_path.resolve()).lower()
    except Exception:
        return None
    if "antigravity" in target:
        return "antigravity"
    if "cursor" in target:
        return "cursor"
    if "windsurf" in target or "devin" in target:
        return "windsurf"
    if "codium" in target or "vscodium" in target:
        return "vscodium"
    if "code" in target or "vscode" in target:
        return "vscode"
    return None


def _vscode_family_env_hint() -> str | None:
    haystack = " ".join(
        (
            os.environ.get("CHROME_DESKTOP", ""),
            os.environ.get("VSCODE_CODE_CACHE_PATH", ""),
            os.environ.get("VSCODE_NLS_CONFIG", ""),
            os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", ""),
        )
    ).lower()
    if "vscodium" in haystack or "codium" in haystack:
        return "vscodium"
    if "antigravity" in haystack:
        return "antigravity"
    if "cursor" in haystack:
        return "cursor"
    if "windsurf" in haystack or "devin" in haystack:
        return "windsurf"
    if "code" in haystack or "vscode" in haystack:
        return "vscode"
    return None


def _windsurf_terminal_marker() -> bool:
    """True when env carries a Windsurf/Devin marker (the current provider name)."""
    tpv = os.environ.get("TERM_PROGRAM_VERSION", "").strip().lower()
    chrome = os.environ.get("CHROME_DESKTOP", "").strip().lower()
    gio = os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").strip().lower()
    return bool(
        os.environ.get("WINDSURF_CASCADE_TERMINAL")
        or os.environ.get("WINDSURF_VERSION")
        or any("windsurf" in v or "devin" in v for v in (tpv, chrome, gio))
    )


def _terminal_shell_context_fallback(
    ide_from_vscode_pid: Any = None,
    vscode_family_env_hint: Any = None,
    windsurf_terminal_marker: Any = None,
) -> tuple[str | None, str, bool]:
    """Provider-first shell context detection (brand name before generic vscode)."""
    _ide_from_pid = ide_from_vscode_pid if ide_from_vscode_pid is not None else _ide_from_vscode_pid
    _vscode_hint = vscode_family_env_hint if vscode_family_env_hint is not None else _vscode_family_env_hint
    _windsurf_marker = windsurf_terminal_marker if windsurf_terminal_marker is not None else _windsurf_terminal_marker

    chrome = os.environ.get("CHROME_DESKTOP", "").strip().lower()
    term_program = os.environ.get("TERM_PROGRAM", "").strip().lower()
    if "antigravity" in os.environ.get("GIO_LAUNCHED_DESKTOP_FILE", "").lower():
        return "antigravity", "env:GIO_LAUNCHED_DESKTOP_FILE", True
    if term_program in {"vscode", "code"}:
        if os.environ.get("VSCODE_PID"):
            via_pid = _ide_from_pid()
            if via_pid:
                return via_pid, "env:VSCODE_PID.exe", True
        flavor = _vscode_hint()
        if flavor and flavor != "vscode":
            return flavor, "env:VSCODE_*", True
        if _windsurf_marker():
            return "windsurf", "env:WINDSURF_*", True
        return "vscode", "env:TERM_PROGRAM", True
    terminal_emulator = os.environ.get("TERMINAL_EMULATOR", "").strip().lower()
    if (
        "jetbrains" in terminal_emulator
        or "jediterm" in terminal_emulator
        or os.environ.get("IDEA_INITIAL_DIRECTORY")
        or os.environ.get("PYCHARM_HOSTED")
        or os.environ.get("JETBRAINS_IDE")
    ):
        return "jetbrains", "env:TERMINAL_EMULATOR", True
    if "cursor" in chrome or os.environ.get("CURSOR_AGENT") or os.environ.get("CURSOR_CLI"):
        return "cursor", "env:CURSOR_*", True
    if term_program in _VALID_AUTOPILOT_IDES and term_program != "auto":
        return term_program, "env:TERM_PROGRAM", True
    if _windsurf_marker():
        return "windsurf", "env:WINDSURF_*", True
    return None, "none", False


def terminal_shell_context() -> tuple[str | None, str, bool]:
    """Return ``(ide, source, integrated)`` for the current shell context."""
    fallback = _terminal_shell_context_fallback()
    if fallback[2]:
        return fallback
    try:
        from koruide.ide import detect_terminal_host_context
        ctx = detect_terminal_host_context()
        return ctx.ide, ctx.source, ctx.integrated
    except Exception:
        return fallback


def terminal_ide_hint() -> str | None:
    """Best-effort IDE owning this shell."""
    ide, _source, _integrated = terminal_shell_context()
    return ide


def terminal_host_kind() -> str:
    try:
        from koruide.ide import detect_terminal_host_context
        return detect_terminal_host_context().kind
    except Exception:
        return "system"
