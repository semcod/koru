"""Socket path helpers for `koruide` control-plane clients/servers."""

from __future__ import annotations

import contextlib
import os
from pathlib import Path


def _autopilot_socket_basename() -> str:
    """File name (with ``.sock``) under ``$XDG_RUNTIME_DIR`` or ``/tmp``."""
    instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
    if not instance or instance.lower() == "auto":
        return "koru-autopilot.sock"
    slug_chars: list[str] = []
    for ch in instance[:64]:
        if ch.isalnum() or ch in "-_":
            slug_chars.append(ch)
        else:
            slug_chars.append("-")
    slug = "".join(slug_chars).strip("-") or "instance"
    return f"koru-autopilot-{slug}.sock"


def default_socket_path() -> Path:
    """Return the canonical unix-socket location for the control daemon."""
    explicit = os.environ.get("KORU_AUTOPILOT_SOCKET", "").strip()
    if explicit:
        return Path(explicit).expanduser().resolve()

    name = _autopilot_socket_basename()
    runtime = os.environ.get("XDG_RUNTIME_DIR")
    if runtime:
        path = Path(runtime) / name
        with contextlib.suppress(OSError):
            path.parent.mkdir(parents=True, exist_ok=True)
        return path
    if name == "koru-autopilot.sock":
        return Path(f"/tmp/koru-autopilot-{os.getuid()}.sock")
    stem = name.removesuffix(".sock")
    return Path(f"/tmp/{stem}-{os.getuid()}.sock")


__all__ = ["default_socket_path"]
