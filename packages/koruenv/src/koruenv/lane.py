"""Core lane environment helpers shared by shell wrappers and future services."""

from __future__ import annotations

import os
import re
import tempfile
from pathlib import Path
from typing import Mapping

LANE_VALID_IDES = frozenset(
    {
        "auto",
        "vscode",
        "vscodium",
        "cursor",
        "windsurf",
        "jetbrains",
        "zed",
        "antigravity",
    }
)
_INSTANCE_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def validate_ide(ide: str) -> str:
    normalized = str(ide or "").strip().lower()
    if normalized not in LANE_VALID_IDES:
        allowed = ", ".join(sorted(LANE_VALID_IDES))
        raise ValueError(f"unsupported ide '{ide}' (allowed: {allowed})")
    return normalized


def validate_instance(instance: str) -> str:
    normalized = str(instance or "").strip()
    if not _INSTANCE_RE.fullmatch(normalized):
        raise ValueError("invalid instance (allowed: [A-Za-z0-9_-], len 1..64)")
    return normalized


def _fallback_temp_dir(environ: Mapping[str, str] | None = None) -> Path:
    env = os.environ if environ is None else environ
    for key in ("LOCALAPPDATA", "TEMP", "TMP"):
        value = (env.get(key) or "").strip()
        if value:
            return Path(value)
    return Path(tempfile.gettempdir())


def resolve_lane_socket(instance: str, *, environ: Mapping[str, str] | None = None) -> Path:
    """Resolve canonical per-lane socket path for the current platform."""
    return resolve_lane_socket_for_os(instance, environ=environ, os_name=os.name)


def resolve_lane_socket_for_os(
    instance: str,
    *,
    environ: Mapping[str, str] | None = None,
    os_name: str,
) -> Path:
    """Resolve canonical per-lane socket path for an explicit OS name."""
    inst = validate_instance(instance)
    env = os.environ if environ is None else environ
    xdg_runtime = (env.get("XDG_RUNTIME_DIR") or "").strip()
    if xdg_runtime:
        return Path(xdg_runtime) / f"koru-autopilot-{inst}.sock"
    if os_name == "nt":
        base = str(_fallback_temp_dir(env))
        return Path(base + f"/koru-autopilot-{inst}.sock")
    uid = str(getattr(os, "getuid", lambda: 0)())
    return Path(f"/tmp/koru-autopilot-{inst}-{uid}.sock")


def build_lane_environ(
    *,
    ide: str,
    instance: str,
    environ: Mapping[str, str] | None = None,
) -> dict[str, str]:
    """Build environment overlay for one strict IDE lane."""
    ide_normalized = validate_ide(ide)
    instance_normalized = validate_instance(instance)
    env = dict(os.environ if environ is None else environ)
    socket_path = resolve_lane_socket_for_os(
        instance_normalized,
        environ=env,
        os_name=os.name,
    )
    return {
        "KORU_AUTOPILOT_IDE": ide_normalized,
        "KORU_AUTOPILOT_INSTANCE": instance_normalized,
        "KORU_AUTOPILOT_SOCKET": str(socket_path),
    }
