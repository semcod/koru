"""Resolve stable IDE CLI binaries (avoid AppImage mount paths)."""

from __future__ import annotations

import os
import shutil


_EDITOR_CANDIDATES: dict[str, tuple[str, ...]] = {
    "cursor": ("/usr/bin/cursor", "/usr/local/bin/cursor", "cursor"),
    "vscode": ("/usr/bin/code", "/usr/share/code/bin/code", "code"),
    "vscodium": ("/usr/bin/codium", "/usr/local/bin/codium", "codium"),
    "windsurf": ("/usr/bin/windsurf", "windsurf"),
    "antigravity": ("/usr/bin/antigravity", "antigravity"),
}


def _is_appimage_mount(path: str) -> bool:
    lowered = path.lower()
    return "/.mount_" in lowered or path.startswith("/tmp/.mount_")


def resolve_editor_cli(ide: str) -> str | None:
    for candidate in _EDITOR_CANDIDATES.get(ide, (ide,)):
        if candidate.startswith("/"):
            if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
                return candidate
            continue
        path = shutil.which(candidate)
        if path and not _is_appimage_mount(path):
            return path
    fallback = shutil.which(ide)
    if fallback and not _is_appimage_mount(fallback):
        return fallback
    return None
