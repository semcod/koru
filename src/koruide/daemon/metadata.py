"""Runtime metadata sidecar for the autopilot daemon."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
from typing import Any


def daemon_metadata_path(project: Path | None, socket_path: Path) -> Path:
    """Return the metadata sidecar path for a project/socket pair."""
    if project is not None:
        slug = _safe_slug(socket_path.name.removesuffix(".sock"))
        return project / ".planfile" / ".koru" / f"{slug}.daemon.json"
    return socket_path.with_name(f"{socket_path.name}.json")


def _normalized_project(project: Path | None) -> Path | None:
    if project is None:
        return None
    try:
        from koru.autonomous_runtime import normalize_project_root

        return normalize_project_root(project)
    except Exception:
        try:
            return project.resolve()
        except OSError:
            return project


def build_daemon_metadata(
    *,
    socket_path: Path,
    project: Path | None,
    started_at: float,
) -> dict[str, Any]:
    """Build process/runtime metadata for status and stale-daemon diagnosis."""
    normalized = _normalized_project(project)
    return {
        "schema": "koru.autopilot.daemon.v1",
        "pid": os.getpid(),
        "ppid": os.getppid(),
        "uid": os.getuid() if hasattr(os, "getuid") else None,
        "version": _package_version(),
        "git_sha": _git_sha(normalized),
        "python": sys.version.split()[0],
        "python_executable": sys.executable,
        "cwd": os.getcwd(),
        "project": str(normalized.resolve()) if normalized is not None else None,
        "socket": str(socket_path),
        "socket_inode": _inode(socket_path),
        "started_at": datetime.fromtimestamp(started_at, timezone.utc).isoformat(),
        "uptime_seconds": max(0.0, time.time() - started_at),
        "env": {
            "KORU_AUTOPILOT_INSTANCE": os.environ.get("KORU_AUTOPILOT_INSTANCE", ""),
            "VIRTUAL_ENV": os.environ.get("VIRTUAL_ENV", ""),
        },
    }


def write_daemon_metadata(metadata: dict[str, Any], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(metadata, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def read_daemon_metadata(path: Path) -> dict[str, Any] | None:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def remove_daemon_metadata(path: Path, *, pid: int | None = None) -> None:
    if pid is not None:
        existing = read_daemon_metadata(path)
        if existing and existing.get("pid") != pid:
            return
    try:
        path.unlink()
    except FileNotFoundError:
        pass


def _package_version() -> str | None:
    try:
        return version("koru")
    except PackageNotFoundError:
        return None


def _git_sha(project: Path | None) -> str | None:
    if project is None:
        return None
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--short=12", "HEAD"],
            cwd=project,
            check=False,
            capture_output=True,
            text=True,
            timeout=1.0,
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return result.stdout.strip() or None


def _inode(path: Path) -> int | None:
    try:
        return path.stat().st_ino
    except OSError:
        return None


def _safe_slug(value: str) -> str:
    out = [ch if ch.isalnum() or ch in "-_" else "-" for ch in value[:96]]
    return "".join(out).strip("-") or "koru-autopilot"


__all__ = [
    "build_daemon_metadata",
    "daemon_metadata_path",
    "read_daemon_metadata",
    "remove_daemon_metadata",
    "write_daemon_metadata",
]
