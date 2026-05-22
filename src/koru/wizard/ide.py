"""IDE discovery for ``koru wizard``.

Combines the runtime detector in :mod:`koruide.ide` with a filesystem scan of
well-known install locations so we can also propose IDEs that aren't currently
running. Linux-focused but degrades gracefully on macOS/Windows.
"""

from __future__ import annotations

import shutil
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path

from koruide.ide import RunningIDE, detect_running_ides

_INSTALL_HINTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "cursor": (
        "Cursor",
        (
            "/usr/bin/cursor",
            "/usr/local/bin/cursor",
            "/opt/Cursor/cursor",
            "/snap/bin/cursor",
            "/var/lib/flatpak/exports/bin/com.cursor.Cursor",
            "~/.local/bin/cursor",
            "~/Applications/Cursor.AppImage",
            "/Applications/Cursor.app/Contents/MacOS/Cursor",
        ),
    ),
    "vscode": (
        "VS Code",
        (
            "/usr/bin/code",
            "/usr/local/bin/code",
            "/snap/bin/code",
            "/var/lib/flatpak/exports/bin/com.visualstudio.code",
            "~/.local/bin/code",
            "/Applications/Visual Studio Code.app/Contents/Resources/app/bin/code",
        ),
    ),
    "vscodium": (
        "VSCodium",
        (
            "/usr/bin/codium",
            "/snap/bin/codium",
            "/opt/vscodium-bin/bin/codium",
            "~/.local/bin/codium",
        ),
    ),
    "windsurf": (
        "Windsurf",
        (
            "/usr/bin/windsurf",
            "/opt/windsurf/windsurf",
            "/snap/bin/windsurf",
            "~/.local/bin/windsurf",
        ),
    ),
    "antigravity": (
        "Antigravity",
        (
            "/usr/bin/antigravity",
            "/opt/antigravity/antigravity",
            "~/.local/bin/antigravity",
        ),
    ),
    "jetbrains": (
        "JetBrains IDE",
        (
            "/usr/bin/idea",
            "/usr/local/bin/idea",
            "/snap/bin/intellij-idea-community",
            "/snap/bin/pycharm-community",
            "/snap/bin/pycharm-professional",
            "/snap/bin/webstorm",
            "~/.local/share/JetBrains/Toolbox/scripts/idea",
            "~/.local/share/JetBrains/Toolbox/scripts/pycharm",
            "~/.local/share/JetBrains/Toolbox/scripts/webstorm",
            "/Applications/IntelliJ IDEA.app/Contents/MacOS/idea",
            "/Applications/PyCharm.app/Contents/MacOS/pycharm",
        ),
    ),
    "zed": (
        "Zed",
        (
            "/usr/bin/zed",
            "/usr/local/bin/zed",
            "~/.local/bin/zed",
            "/Applications/Zed.app/Contents/MacOS/Zed",
        ),
    ),
}


@dataclass(frozen=True)
class DetectedIDE:
    """One IDE that may be offered as a wizard target."""

    id: str
    label: str
    running: bool
    pid: int | None
    path: str
    extras: tuple[str, ...] = field(default_factory=tuple)

    def to_dict(self) -> dict[str, object]:
        return {
            "id": self.id,
            "label": self.label,
            "running": self.running,
            "pid": self.pid,
            "path": self.path,
            "extras": list(self.extras),
        }


def _expand(path: str) -> Path:
    return Path(path).expanduser()


def _scan_installed(
    hint_map: dict[str, tuple[str, tuple[str, ...]]] | None = None,
) -> list[DetectedIDE]:
    """Return one :class:`DetectedIDE` per IDE id that has an executable on disk."""
    if hint_map is None:
        hint_map = _INSTALL_HINTS
    found: list[DetectedIDE] = []
    for ide_id, (label, candidates) in hint_map.items():
        primary: str | None = None
        extras: list[str] = []
        for candidate in candidates:
            resolved = _expand(candidate)
            if resolved.exists():
                if primary is None:
                    primary = str(resolved)
                else:
                    extras.append(str(resolved))
        if primary is None:
            which = shutil.which(ide_id) or shutil.which(label.lower().replace(" ", "-"))
            if which:
                primary = which
        if primary is not None:
            found.append(
                DetectedIDE(
                    id=ide_id,
                    label=label,
                    running=False,
                    pid=None,
                    path=primary,
                    extras=tuple(extras),
                )
            )
    return found


def _merge_running(
    installed: list[DetectedIDE],
    running: Iterable[RunningIDE],
) -> list[DetectedIDE]:
    """Promote installed entries to ``running=True`` when a live process matches."""
    running_by_id: dict[str, RunningIDE] = {r.id: r for r in running}
    merged: dict[str, DetectedIDE] = {ide.id: ide for ide in installed}

    for ide_id, proc in running_by_id.items():
        existing = merged.get(ide_id)
        if existing is not None:
            merged[ide_id] = DetectedIDE(
                id=existing.id,
                label=existing.label,
                running=True,
                pid=proc.pid,
                path=proc.exe or existing.path,
                extras=existing.extras,
            )
        else:
            merged[ide_id] = DetectedIDE(
                id=proc.id,
                label=proc.label,
                running=True,
                pid=proc.pid,
                path=proc.exe or proc.id,
                extras=(),
            )

    return sorted(
        merged.values(),
        key=lambda ide: (not ide.running, ide.label.lower()),
    )


def discover_installed_ides(
    *,
    hint_map: dict[str, tuple[str, tuple[str, ...]]] | None = None,
    running_override: Iterable[RunningIDE] | None = None,
) -> list[DetectedIDE]:
    """Return all IDEs that are either installed or currently running.

    ``hint_map`` lets callers (mostly tests) inject a custom install-path map.
    ``running_override`` is also a test hook.
    """
    installed = _scan_installed(hint_map if hint_map is not None else None)
    running = running_override if running_override is not None else detect_running_ides()
    return _merge_running(installed, list(running))


def summarize_ides(ides: list[DetectedIDE]) -> str:
    """Plain-text summary, one IDE per line, running ones first."""
    if not ides:
        return "(no IDEs detected — neither running nor installed in known paths)"
    ordered = sorted(ides, key=lambda ide: (not ide.running, ide.label.lower()))
    lines: list[str] = []
    for ide in ordered:
        status = f"running pid={ide.pid}" if ide.running else "installed"
        lines.append(f"  - {ide.label:<14} [{status}]  {ide.path}")
    return "\n".join(lines)
