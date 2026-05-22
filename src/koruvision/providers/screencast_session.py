"""Persist xdg-desktop-portal ScreenCast session handles across capture cycles."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

SESSION_FILENAME = "screencast.session"


def session_file_for_project(project: Path) -> Path:
    return project.resolve() / ".koru" / "keys" / SESSION_FILENAME


def resolve_screencast_session_file() -> Path:
    """Return the JSON session cache path for the active project."""
    override = os.environ.get("KORU_SCREENCAST_SESSION", "").strip()
    if override:
        return Path(override).expanduser().resolve()
    store = os.environ.get("KORU_MESH_FRAME_STORE", "").strip()
    if store:
        run_dir = Path(store).expanduser().resolve().parent
        return run_dir.parent / "keys" / SESSION_FILENAME
    return Path.cwd().resolve() / ".koru" / "keys" / SESSION_FILENAME


def load_session_path(path: Path | None = None) -> str | None:
    """Load a saved D-Bus session object path, or ``None`` if missing/invalid."""
    target = path or resolve_screencast_session_file()
    if not target.is_file():
        return None
    try:
        data = json.loads(target.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    session_path = str(data.get("session_path") or "").strip()
    return session_path or None


def save_session_path(session_path: str, path: Path | None = None) -> Path:
    """Write ``session_path`` to disk with mode ``0600``."""
    target = path or resolve_screencast_session_file()
    target.parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"session_path": session_path}
    target.write_text(json.dumps(payload) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)
    return target


def clear_session_file(path: Path | None = None) -> bool:
    """Remove the session cache file if present."""
    target = path or resolve_screencast_session_file()
    if not target.is_file():
        return False
    target.unlink()
    return True
