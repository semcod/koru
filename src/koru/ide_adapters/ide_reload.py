"""Best-effort IDE window reload so VSIX extensions load without manual steps."""

from __future__ import annotations

import os
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from koru.ide_adapters.shared import config_home_for_ide
from koruide.ides import get_strategy as _get_ide_strategy

_VSCODE_FAMILY_IDES = frozenset({"antigravity", "cursor", "vscode", "vscodium", "windsurf"})

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


def _focus_ide_window(ide: str) -> bool:
    if not shutil.which("xdotool"):
        return False
    for hint in _window_name_hints(ide):
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
        return activate.returncode == 0
    return False


def _type_keys(argv: list[str]) -> bool:
    if not shutil.which("wtype"):
        return False
    return _run(argv).returncode == 0


def reload_via_command_palette(ide: str) -> IdeReloadOutcome:
    """Open the command palette and run ``Developer: Reload Window``."""
    if not shutil.which("wtype"):
        return IdeReloadOutcome(
            attempted=False,
            ok=False,
            detail="wtype not on PATH",
        )
    if not _focus_ide_window(ide):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail=f"could not focus {ide} window (xdotool)",
        )
    time.sleep(0.6)
    if not _type_keys(["wtype", "-M", "ctrl", "-M", "shift", "-p"]):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail="failed to open command palette",
        )
    time.sleep(0.5)
    if not _type_keys(["wtype", "-t", "Developer: Reload Window"]):
        return IdeReloadOutcome(
            attempted=True,
            ok=False,
            method="command_palette",
            detail="failed to type reload command",
        )
    time.sleep(0.2)
    if not _type_keys(["wtype", "-k", "Return"]):
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


def try_reload_vscode_family_ide(
    ide: str,
    *,
    project: Path | None = None,
    dry_run: bool = False,
) -> IdeReloadOutcome:
    """Reload a VS Code–family IDE so a newly installed VSIX can activate."""
    if ide not in _VSCODE_FAMILY_IDES:
        return IdeReloadOutcome(attempted=False, ok=False, detail=f"unsupported ide={ide}")
    if not auto_reload_enabled():
        return IdeReloadOutcome(attempted=False, ok=False, detail="auto reload disabled")
    if dry_run:
        return IdeReloadOutcome(attempted=True, ok=True, method="dry_run")
    if config_home_for_ide(ide) is None:
        return IdeReloadOutcome(attempted=False, ok=False, detail="unknown config home")

    palette = reload_via_command_palette(ide)
    if palette.ok:
        return palette

    if (
        project is not None
        and project.is_dir()
        and reuse_window_reload_enabled()
    ):
        reopen = reload_via_reopen_workspace(ide, project)
        if reopen.ok:
            return reopen
        if palette.attempted:
            palette = IdeReloadOutcome(
                attempted=True,
                ok=False,
                method="command_palette+reuse_window",
                detail=f"{palette.detail}; reopen: {reopen.detail}",
            )
            return palette
        return reopen

    if project is not None and project.is_dir() and not reuse_window_reload_enabled():
        if palette.attempted:
            palette = IdeReloadOutcome(
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
        else:
            palette = IdeReloadOutcome(
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

    return palette


__all__ = [
    "IdeReloadOutcome",
    "auto_reload_enabled",
    "reload_via_command_palette",
    "reload_via_reopen_workspace",
    "reuse_window_reload_enabled",
    "try_reload_vscode_family_ide",
]
