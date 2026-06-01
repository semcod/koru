"""Best-effort IDE window reload so VSIX extensions load without manual steps.

This module orchestrates the *IDE-side* reload sequence
(``Developer: Reload Window``). Every OS-level decision (which focus
tool, which keyboard injector, Wayland-vs-X11 quirks) is delegated to
:mod:`koruos` — the OS strategy is the single source of truth.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from koru.ide_adapters.shared import config_home_for_ide
from koruide.ides import get_strategy as _get_ide_strategy
from koruos import (
    FocusOutcome,
    KeySequence,
    OsStrategy,
    resolve_active_os_strategy,
)

_VSCODE_FAMILY_IDES = frozenset({"antigravity", "cursor", "vscode", "vscodium", "windsurf"})


def _on_wayland() -> bool:
    if os.environ.get("WAYLAND_DISPLAY", "").strip():
        return True
    return os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"


def _ide_accepts_integrated_terminal(ide: str) -> bool:
    """Whether the IDE id is in the VS Code family that exports
    ``TERM_PROGRAM=vscode`` for its integrated terminal.

    The OS strategy detects the environment; this IDE-axis predicate
    confirms that the IDE actually claims the integrated-terminal
    contract. Putting the IDE predicate on the IDE axis keeps OS
    strategies platform-only — no string-matching on IDE ids.
    """
    return ide in _VSCODE_FAMILY_IDES


def _os_strategy() -> OsStrategy:
    return resolve_active_os_strategy()

# Fallback when an unknown IDE id is passed (supported IDEs use strategies).
_LEGACY_WINDOW_NAME_HINTS: dict[str, tuple[str, ...]] = {}
_LEGACY_EDITOR_CLI: dict[str, tuple[str, ...]] = {}


def _window_name_hints(ide: str) -> tuple[str, ...]:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        return strategy.window_name_hints()
    return _LEGACY_WINDOW_NAME_HINTS.get(ide, (ide,))


def _editor_cli_candidates(ide: str) -> tuple[str, ...]:
    strategy = _get_ide_strategy(ide)
    if strategy is not None:
        candidates = strategy.editor_cli_candidates()
        if candidates:
            return candidates
    return _LEGACY_EDITOR_CLI.get(ide, ())


@dataclass(frozen=True)
class IdeReloadOutcome:
    attempted: bool
    ok: bool
    method: str | None = None
    detail: str | None = None


def auto_reload_enabled() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_AUTO_RELOAD_IDE", "1").strip().lower()
    return raw not in {"0", "false", "no", "off"}


def reuse_window_reload_enabled() -> bool:
    """Whether ``cursor -r <project>`` is allowed as a reload fallback.

    DEFAULT: off. The ``--reuse-window`` flag *replaces* whatever workspace
    the IDE window currently has with ``project``. When koru is started in
    a multi-project setup (e.g. user is editing project A in Cursor while
    ``koru auto`` runs for project B), this silently switches the user's
    open project, killing their session. Require explicit opt-in.
    """
    raw = os.environ.get(
        "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD",
        "",
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def new_window_reload_enabled() -> bool:
    """Whether opening a fresh IDE window is allowed after reopen fails.

    This is a stronger recovery than ``--reuse-window``: it starts a fresh
    extension host for the project, which gives auto-connect VSIX plugins a
    clean activation path. It may create an extra editor window, so callers
    must opt in explicitly.
    """
    raw = os.environ.get(
        "KORU_AUTOPILOT_NEW_WINDOW_RELOAD",
        "",
    ).strip().lower()
    return raw in {"1", "true", "yes", "on"}


def _run(argv: list[str], *, timeout: float = 15.0) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        argv,
        capture_output=True,
        text=True,
        check=False,
        timeout=timeout,
    )


def _resolve_editor_cli(ide: str) -> str | None:
    for name in _editor_cli_candidates(ide):
        path = shutil.which(name)
        if path:
            return path
    return None


def _focus_ide_window(ide: str) -> tuple[bool, str]:
    """Delegate window focus to the active :class:`OsStrategy`.

    Returns ``(ok, method)`` where ``method`` is the OS strategy's
    chosen technique (``xdotool`` / ``wmctrl`` / ``integrated_terminal``
    / ``osascript`` / …). The IDE id is consulted only to decide whether
    the integrated-terminal heuristic is admissible for this family —
    a JetBrains target should not be activated by ``TERM_PROGRAM=vscode``
    even if Koru was launched from a Cursor terminal.
    """
    strategy = _os_strategy()
    outcome: FocusOutcome = strategy.focus_window(_window_name_hints(ide))
    if outcome.ok and outcome.method == "integrated_terminal":
        if not _ide_accepts_integrated_terminal(ide):
            return False, ""
    return outcome.ok, outcome.method


def reload_jetbrains_via_shortcut() -> IdeReloadOutcome:
    """Reload JetBrains IDE via keyboard shortcut (Invalidate Caches / Restart).

    Sequence:
    1. Ask the OS strategy to focus the JetBrains window.
    2. Inject ``Ctrl+Shift+F9`` to open Invalidate Caches dialog.
    3. Press ``Return`` to confirm Invalidate and Restart.

    Note: This works on Linux/Windows. macOS uses different shortcuts.
    """
    strategy = _os_strategy()
    capabilities = strategy.capabilities()
    if not capabilities.can_inject_keys:
        return IdeReloadOutcome(
            attempted=False,
            ok=False,
            detail=(
                f"{strategy.label}: no keyboard-injection tool available "
                f"(strategy={strategy.id})"
            ),
        )
    # Focus JetBrains window first
    focused, _ = _focus_ide_window("jetbrains")
    if not focused:
        wayland = "wayland" if _on_wayland() else "x11"
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="jetbrains_shortcut",
            detail=(
                f"could not focus JetBrains window (session={wayland}, "
                f"strategy={strategy.id}, methods={capabilities.focus_methods}). "
                "Run `koru auto` from a terminal inside JetBrains, or install wmctrl/xdotool"
            ),
        )
    time.sleep(0.6)
    # Ctrl+Shift+F9 opens Invalidate Caches dialog on Linux/Windows
    if not strategy.inject_keys(KeySequence(modifiers=("ctrl", "shift"), key="f9")):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="jetbrains_shortcut",
            detail=f"failed to open Invalidate Caches dialog ({capabilities.keyboard_tool})",
        )
    time.sleep(0.5)
    # Press Return to confirm "Invalidate and Restart"
    if not strategy.inject_keys(KeySequence(key="Return")):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="jetbrains_shortcut",
            detail="failed to confirm Invalidate and Restart",
        )
    return IdeReloadOutcome(attempted=True, ok=True, method="jetbrains_shortcut")


def reload_via_command_palette(ide: str) -> IdeReloadOutcome:
    """Open the command palette and run ``Developer: Reload Window``.

    Sequence:
    1. Ask the OS strategy to focus the IDE window (or accept its
       integrated-terminal alibi).
    2. Inject ``Ctrl+Shift+P`` to open the command palette.
    3. Type ``Developer: Reload Window``.
    4. Press ``Return``.

    Every step is delegated to ``strategy.inject_keys`` — this function
    no longer cares which tool the OS strategy uses internally.
    """
    strategy = _os_strategy()
    capabilities = strategy.capabilities()
    if not capabilities.can_inject_keys:
        return IdeReloadOutcome(
            attempted=False,
            ok=False,
            detail=(
                f"{strategy.label}: no keyboard-injection tool available "
                f"(strategy={strategy.id})"
            ),
        )
    focused, focus_method = _focus_ide_window(ide)
    if not focused:
        wayland = "wayland" if _on_wayland() else "x11"
        if wayland == "wayland":
            help_text = (
                "Wayland: auto-focus requires wmctrl (with XWayland) or running "
                "koru inside the IDE's integrated terminal. "
                "Alternatively: 1) Install ydotool + wtype for keyboard injection; "
                "2) Manually reload the IDE (Ctrl+Shift+P → 'Developer: Reload Window'); "
                "3) Run 'koru: Connect autopilot daemon' after reload. "
                "Or set KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to enable CLI reload fallback."
            )
        else:
            help_text = (
                "Run `koru auto` from a terminal *inside* the IDE so "
                "TERM_PROGRAM=vscode is set, or install wmctrl/xdotool"
            )
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail=(
                f"could not focus {ide} window (session={wayland}, "
                f"strategy={strategy.id}, methods={capabilities.focus_methods}). "
                f"{help_text}"
            ),
        )
    if focus_method == "integrated_terminal":
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail=(
                "refusing command-palette reload from integrated terminal focus; "
                "typing `Developer: Reload Window` here would write into the "
                "shell. Reload the IDE manually or enable "
                "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to allow the CLI "
                "reuse-window fallback."
            ),
        )
    time.sleep(0.6)
    if not strategy.inject_keys(KeySequence(modifiers=("ctrl", "shift"), key="p")):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail=f"failed to open command palette ({capabilities.keyboard_tool})",
        )
    time.sleep(0.5)
    if not strategy.inject_keys(KeySequence(literal_text="Developer: Reload Window")):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail="failed to type reload command",
        )
    time.sleep(0.2)
    if not strategy.inject_keys(KeySequence(key="Return")):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail="failed to confirm reload command",
        )
    return IdeReloadOutcome(attempted=True, ok=True, method="command_palette")


def reload_via_reopen_workspace(ide: str, project: Path) -> IdeReloadOutcome:
    """Ask the editor CLI to reuse the window for ``project`` (may reload extensions)."""
    editor = _resolve_editor_cli(ide)
    if editor is None:
        return IdeReloadOutcome(attempted=False, ok=False, detail="editor CLI not found")
    proc = _run([editor, "-r", str(project.resolve())], timeout=30.0)
    if proc.returncode != 0:
        hint = (proc.stderr or proc.stdout or "").strip()[:200]
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="reuse_window",
            detail=hint or f"rc={proc.returncode}",
        )
    return IdeReloadOutcome(attempted=True, ok=True, method="reuse_window")


def reload_via_new_window(ide: str, project: Path) -> IdeReloadOutcome:
    """Open ``project`` in a fresh IDE window to start a new extension host."""
    editor = _resolve_editor_cli(ide)
    if editor is None:
        return IdeReloadOutcome(attempted=False, ok=False, detail="editor CLI not found")
    proc = _run([editor, "-n", str(project.resolve())], timeout=30.0)
    if proc.returncode != 0:
        hint = (proc.stderr or proc.stdout or "").strip()[:200]
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="new_window",
            detail=hint or f"rc={proc.returncode}",
        )
    return IdeReloadOutcome(attempted=True, ok=True, method="new_window")


def _reload_fallback_reopen(
    ide: str,
    project: Path,
    palette: IdeReloadOutcome,
) -> IdeReloadOutcome:
    reopen = reload_via_reopen_workspace(ide, project)
    if reopen.ok:
        return reopen
    if palette.attempted:
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette+reuse_window",
            detail=f"{palette.detail}; reopen: {reopen.detail}",
        )
    return reopen


def _reload_explain_reuse_window_disabled(palette: IdeReloadOutcome) -> IdeReloadOutcome:
    if palette.attempted:
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method=palette.method,
            detail=(
                f"{palette.detail or 'palette failed'}; "
                "reuse-window fallback disabled (would replace user's current "
                "workspace with --reuse-window). Set "
                "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to enable, or reload the "
                "IDE manually with `Developer: Reload Window`."
            ),
        )
    return IdeReloadOutcome(
        attempted=False,
        ok=False,
        method=None,
        detail=(
            "command palette reload unavailable (no wtype/xdotool focus "
            "on Wayland) and --reuse-window fallback disabled to protect "
            "the user's open workspace. Set "
            "KORU_AUTOPILOT_REUSE_WINDOW_RELOAD=1 to opt in, or reload "
            "the IDE manually with `Developer: Reload Window`."
        ),
    )


def detect_reload_command(
    ide: str,
    *,
    dry_run: bool,
) -> tuple[str | None, str | None]:
    """Return ``(method, reason)`` for the reload strategy decision."""
    if ide not in _VSCODE_FAMILY_IDES and ide != "jetbrains":
        return None, f"unsupported ide={ide}"
    if not auto_reload_enabled():
        return None, "auto reload disabled"
    if dry_run:
        return "dry_run", None
    if ide == "jetbrains":
        return "jetbrains_shortcut", None
    if config_home_for_ide(ide) is None:
        return None, "unknown config home"
    return "command_palette", None


def execute_reload(
    ide: str,
    *,
    method: str,
    project: Path | None,
) -> IdeReloadOutcome:
    """Execute the selected reload strategy and return the raw outcome."""
    if method == "dry_run":
        return IdeReloadOutcome(attempted=True, ok=True, method="dry_run")

    if method == "jetbrains_shortcut":
        return reload_jetbrains_via_shortcut()

    if method != "command_palette":
        return IdeReloadOutcome(
            attempted=False,
            ok=False,
            method=method,
            detail=f"unsupported reload method={method}",
        )

    palette = reload_via_command_palette(ide)
    if palette.ok:
        return palette

    if project is None or not project.is_dir():
        return palette
    if reuse_window_reload_enabled():
        return _reload_fallback_reopen(ide, project, palette)
    return _reload_explain_reuse_window_disabled(palette)


def await_plugin_handshake(
    ide: str,
    *,
    timeout_seconds: float = 5.0,
    interval_seconds: float = 0.25,
) -> tuple[bool, str]:
    """Optionally verify extension-host activation after issuing reload."""
    raw = os.environ.get("KORU_AUTOPILOT_RELOAD_VERIFY_PLUGIN", "").strip().lower()
    if raw not in {"1", "true", "yes", "on"}:
        return True, "handshake_verification_disabled"

    from koru.ide_adapters import shared

    deadline = time.time() + max(0.0, timeout_seconds)
    while time.time() <= deadline:
        handshake_state = shared.extension_activated_in_exthost(ide)
        if handshake_state is True:
            return True, "plugin_handshake_ok"
        if handshake_state is False:
            time.sleep(max(0.0, interval_seconds))
            continue
        return False, "plugin_handshake_unknown"
    return False, "plugin_handshake_timeout"


def explain_reload_failure(
    *,
    ide: str,
    method: str,
    reason: str,
    outcome: IdeReloadOutcome,
    handshake_reason: str | None = None,
) -> str:
    """Compose a stable failure explanation for operator logs and telemetry."""
    detail = outcome.detail or reason or f"reload_failed ide={ide}"
    if handshake_reason and handshake_reason != "handshake_verification_disabled":
        return f"{detail}; {handshake_reason}"
    return detail


def try_reload_vscode_family_ide(
    ide: str,
    *,
    project: Path | None = None,
    dry_run: bool = False,
) -> IdeReloadOutcome:
    """Reload a VS Code–family IDE so a newly installed VSIX can activate."""
    method, reason = detect_reload_command(ide, dry_run=dry_run)
    if method is None:
        return IdeReloadOutcome(attempted=False, ok=False, detail=reason)

    outcome = execute_reload(ide, method=method, project=project)
    if not outcome.ok:
        return IdeReloadOutcome(
            attempted=outcome.attempted,
            ok=False,
            method=outcome.method,
            detail=explain_reload_failure(
                ide=ide,
                method=method,
                reason=reason or "reload execution failed",
                outcome=outcome,
            ),
        )

    handshake_ok, handshake_reason = await_plugin_handshake(ide)
    if handshake_ok:
        return outcome
    return IdeReloadOutcome(
        attempted=outcome.attempted,
        ok=False,
        method=outcome.method,
        detail=explain_reload_failure(
            ide=ide,
            method=method,
            reason=reason or "plugin handshake failed",
            outcome=outcome,
            handshake_reason=handshake_reason,
        ),
    )


def try_open_vscode_family_ide_new_window(
    ide: str,
    *,
    project: Path | None = None,
) -> IdeReloadOutcome:
    """Open a fresh IDE window as plugin activation fallback."""
    if ide not in _VSCODE_FAMILY_IDES:
        return IdeReloadOutcome(attempted=False, ok=False, detail=f"unsupported ide={ide}")
    if not auto_reload_enabled():
        return IdeReloadOutcome(attempted=False, ok=False, detail="auto reload disabled")
    if not new_window_reload_enabled():
        return IdeReloadOutcome(
            attempted=False,
            ok=False,
            detail="new-window reload fallback disabled",
        )
    if project is None or not project.is_dir():
        return IdeReloadOutcome(attempted=False, ok=False, detail="project directory missing")
    return reload_via_new_window(ide, project)


__all__ = [
    "IdeReloadOutcome",
    "await_plugin_handshake",
    "auto_reload_enabled",
    "detect_reload_command",
    "execute_reload",
    "explain_reload_failure",
    "reload_via_command_palette",
    "reload_via_new_window",
    "reload_via_reopen_workspace",
    "new_window_reload_enabled",
    "reuse_window_reload_enabled",
    "try_open_vscode_family_ide_new_window",
    "try_reload_vscode_family_ide",
    "_focus_ide_window",
    "_ide_accepts_integrated_terminal",
    "_on_wayland",
]
