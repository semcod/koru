"""Fallback capture paths (portal + native CLI) used by :mod:`koruvision.capture`."""

from __future__ import annotations

import hashlib
import os
import shutil
import struct
import subprocess
import sys
from datetime import UTC, datetime
from typing import Any

from koruvision.capture_mss import is_wayland, portal_capture_dict


def parse_png_size(payload: bytes) -> tuple[int, int]:
    """Extract ``(width, height)`` from a PNG IHDR header (returns zeros on parse failure)."""
    if len(payload) < 24 or payload[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    width, height = struct.unpack(">II", payload[16:24])
    return int(width), int(height)


def png_descriptor(payload: bytes, *, output: str) -> dict[str, Any]:
    """Build a VisionFrame descriptor for a PNG byte payload (portal/native CLI)."""
    width, height = parse_png_size(payload)
    return {
        "frame_id": hashlib.sha256(payload).hexdigest()[:16],
        "monitor_id": -1,
        "captured_at": datetime.now(UTC).isoformat(),
        "mime": "image/png",
        "width": width,
        "height": height,
        "payload": payload,
        "native_width": width,
        "native_height": height,
        "output": output,
    }


def command_candidates() -> list[tuple[str, list[str], bool]]:
    """Return ``(name, argv, png_on_stdout)`` for native screenshot commands."""
    return [
        ("grim", ["grim", "-"], True),
        ("scrot", ["scrot", "-o", "/dev/stdout"], True),
        ("gnome-screenshot", ["gnome-screenshot", "-f", "/dev/stdout"], True),
        ("spectacle", ["spectacle", "-b", "-n", "-o", "/dev/stdout"], True),
        ("screencapture", ["screencapture", "-t", "png", "-x", "-"], True),
    ]


def try_native_command() -> dict[str, Any] | None:
    """Run the first available native screenshot command and return a descriptor."""
    for name, argv, _stdout in command_candidates():
        if not shutil.which(argv[0]):
            continue
        try:
            proc = subprocess.run(argv, capture_output=True, timeout=15, check=False)
        except (OSError, subprocess.TimeoutExpired):
            continue
        if proc.returncode != 0 or not proc.stdout:
            continue
        return png_descriptor(proc.stdout, output=name)
    return None


def looks_headless() -> bool:
    """Return True when the host lacks any graphical session or screenshot CLI."""
    env_vars = ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS", "XDG_SESSION_TYPE")
    if any(os.environ.get(var) for var in env_vars):
        return False
    return try_native_command() is None


def portal_descriptor() -> dict[str, Any]:
    """Run the portal capture and decorate the descriptor with parsed PNG size."""
    descriptor = portal_capture_dict()
    descriptor.update(png_descriptor(descriptor["payload"], output="portal"))
    return descriptor


def wayland_portal_fallback(mss_exc: Exception) -> dict[str, Any]:
    """Try the portal backend; surface a helpful error if it also fails."""
    try:
        descriptor = portal_descriptor()
    except RuntimeError as portal_exc:
        msg = (
            f"{mss_exc}; portal fallback failed: {portal_exc}. "
            "Try: export KORU_VISION_BACKEND=portal and grant Screenshot "
            "in Settings → Privacy."
        )
        raise RuntimeError(msg) from portal_exc
    print(
        "koru vision: mss returned black frames on Wayland — used portal capture",
        file=sys.stderr,
    )
    return descriptor


def command_fallback(mss_exc: Exception) -> dict[str, Any]:
    """Run the native CLI fallback; raise a headless error when nothing is usable."""
    descriptor = try_native_command()
    if descriptor is not None:
        return descriptor
    if looks_headless():
        raise RuntimeError(
            f"{mss_exc}; environment looks headless (no DISPLAY/WAYLAND_DISPLAY "
            "and no screenshot command available)."
        )
    raise mss_exc


def fallback_for_environment(mss_exc: Exception) -> dict[str, Any]:
    """Pick the right fallback (portal on Wayland, native command otherwise)."""
    if is_wayland():
        return wayland_portal_fallback(mss_exc)
    return command_fallback(mss_exc)
