"""Session / desktop environment probes for provider ranking."""

from __future__ import annotations

import os
import shutil
import sys


def capture_provider_pref() -> str:
    raw = os.environ.get("KORU_VISION_PROVIDER", "").strip().lower()
    if raw:
        return raw
    legacy = os.environ.get("KORU_VISION_BACKEND", "auto").strip().lower()
    if legacy and legacy != "auto":
        return legacy
    return "auto"


def is_wayland() -> bool:
    return (
        os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
        or bool(os.environ.get("WAYLAND_DISPLAY", "").strip())
    )


def env_truthy(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in {"1", "true", "yes", "on"}


def portal_possible() -> bool:
    return sys.platform.startswith("linux") and (
        is_wayland() or bool(os.environ.get("DBUS_SESSION_BUS_ADDRESS", "").strip())
    )


def looks_headless() -> bool:
    if not sys.platform.startswith("linux"):
        return False
    return not any(
        os.environ.get(name, "").strip()
        for name in ("DISPLAY", "WAYLAND_DISPLAY", "DBUS_SESSION_BUS_ADDRESS")
    )


def compositor_hint() -> str:
    desktop = os.environ.get("XDG_CURRENT_DESKTOP", "").lower()
    if "gnome" in desktop:
        return "gnome"
    if "kde" in desktop or "plasma" in desktop:
        return "kde"
    if is_wayland():
        return "wayland"
    return "x11"


def tool_available(name: str) -> bool:
    return bool(shutil.which(name))
