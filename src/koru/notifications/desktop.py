"""Optional desktop notifications via ``notify-send`` (Linux)."""

from __future__ import annotations

import os
import shutil
import subprocess

from koru.env_flags import parse_boolish


def desktop_notify_enabled() -> bool:
    raw = os.environ.get("KORU_DESKTOP_NOTIFY", "1").strip()
    return parse_boolish(raw, default=True) and shutil.which("notify-send") is not None


def notify_desktop(*, title: str, body: str, urgency: str = "normal") -> bool:
    """Show a desktop notification when enabled and ``notify-send`` is available."""
    if not desktop_notify_enabled():
        return False
    text = (body or "").strip()
    if not text:
        return False
    try:
        notification = subprocess.run(
            [
                "notify-send",
                f"--urgency={urgency}",
                "--app-name=koru",
                title[:120],
                text[:500],
            ],
            check=False,
            timeout=5,
            capture_output=True,
        )
        return notification.returncode == 0
    except (OSError, subprocess.TimeoutExpired):
        return False
