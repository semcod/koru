"""Resolve autopilot socket paths without importing koru."""

from __future__ import annotations

import contextlib
import os
import tempfile
from pathlib import Path


def socket_basename(instance: str) -> str:
    slug_chars: list[str] = []
    for ch in instance[:64]:
        if ch.isalnum() or ch in "-_":
            slug_chars.append(ch)
        else:
            slug_chars.append("-")
    slug = "".join(slug_chars).strip("-") or "instance"
    return f"koru-autopilot-{slug}.sock"


def socket_path_for_instance(instance: str) -> Path:
    explicit = (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip()
    if explicit and os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip() == instance:
        return Path(explicit).expanduser().resolve()

    name = socket_basename(instance)
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        path = Path(runtime) / name
        with contextlib.suppress(OSError):
            path.parent.mkdir(parents=True, exist_ok=True)
        return path
    if os.name == "nt":
        base = (
            os.environ.get("LOCALAPPDATA")
            or os.environ.get("TEMP")
            or tempfile.gettempdir()
        )
        path = Path(base) / name
        with contextlib.suppress(OSError):
            path.parent.mkdir(parents=True, exist_ok=True)
        return path

    uid = str(getattr(os, "getuid", lambda: 0)())
    stem = name.removesuffix(".sock")
    return Path(f"/tmp/{stem}-{uid}.sock")
