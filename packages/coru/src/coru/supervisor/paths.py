"""Filesystem locations for the coru supervisor."""

from __future__ import annotations

import os
from pathlib import Path


def state_dir() -> Path:
    raw = (os.environ.get("CORU_SUPERVISOR_STATE_DIR") or "").strip()
    if raw:
        return Path(raw).expanduser().resolve()
    xdg = (os.environ.get("XDG_STATE_HOME") or "").strip()
    if xdg:
        return (Path(xdg) / "coru").resolve()
    return (Path.home() / ".local" / "state" / "coru").resolve()


def registry_path() -> Path:
    return state_dir() / "supervisor.json"


def pid_path() -> Path:
    return state_dir() / "supervisor.pid"


def default_http_host() -> str:
    return (os.environ.get("CORU_SUPERVISOR_HOST") or "127.0.0.1").strip() or "127.0.0.1"


def default_http_port() -> int:
    raw = (os.environ.get("CORU_SUPERVISOR_PORT") or "8766").strip()
    try:
        return int(raw)
    except ValueError:
        return 8766


def supervisor_url() -> str:
    explicit = (os.environ.get("CORU_SUPERVISOR_URL") or "").strip().rstrip("/")
    if explicit:
        return explicit
    return f"http://{default_http_host()}:{default_http_port()}"
