"""Capture diagnostics for the observation dashboard.

When the vision agent fails to publish any frame (Wayland blocks capture,
``mss`` returns black, portal is denied, …) the dashboard would otherwise
show an empty grid with no explanation. ``capture_diagnostics`` exposes:

- the list of detected monitors (via :mod:`koruvision.capture` if ``mss``
  is installed, falling back to ``xrandr --listmonitors`` for headless
  environments or when ``mss`` itself is unusable),
- the last ``koru vision agent: capture failed: ...`` line from
  ``.koru/run/vision.log`` plus a short ``status`` (``ok`` /
  ``blocked`` / ``no-log``),
- the session type (``wayland`` / ``x11`` / ``unknown``) so the grid UI
  can suggest the right workaround.

The function is intentionally side-effect free and never raises on a
malformed log; the dashboard depends on a stable JSON shape.
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path
from typing import Any

_VISION_LOG_REL = Path(".koru") / "run" / "vision.log"
_FAILED_PREFIX = "koru vision agent: capture failed: "
_MAX_LOG_BYTES = 64 * 1024


def _session_type() -> str:
    """Return the best-effort session label (``wayland`` / ``x11`` / ``unknown``)."""
    if os.environ.get("WAYLAND_DISPLAY"):
        return "wayland"
    if os.environ.get("DISPLAY"):
        return "x11"
    return os.environ.get("XDG_SESSION_TYPE", "unknown") or "unknown"


def _monitors_from_mss() -> list[dict[str, Any]] | None:
    try:
        from koruvision.capture import list_monitors  # type: ignore[import-not-found]
    except Exception:
        return None
    try:
        rows = list_monitors()
    except Exception:
        return None
    out: list[dict[str, Any]] = []
    for idx, row in enumerate(rows):
        out.append(
            {
                "id": idx,
                "output": row.get("name") or row.get("output") or "",
                "width": int(row.get("width", 0) or 0),
                "height": int(row.get("height", 0) or 0),
                "source": "mss",
            }
        )
    return out


_XRANDR_LINE = re.compile(
    r"^\s*\d+:\s+\+\*?(?P<name>\S+)\s+(?P<w>\d+)/\d+x(?P<h>\d+)/\d+"
)


def _monitors_from_xrandr() -> list[dict[str, Any]] | None:
    try:
        proc = subprocess.run(  # noqa: S603,S607
            ["xrandr", "--listmonitors"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        return None
    rows: list[dict[str, Any]] = []
    for line in (proc.stdout or "").splitlines():
        match = _XRANDR_LINE.match(line)
        if not match:
            continue
        rows.append(
            {
                "id": len(rows),
                "output": match.group("name"),
                "width": int(match.group("w")),
                "height": int(match.group("h")),
                "source": "xrandr",
            }
        )
    return rows or None


def detect_monitors() -> list[dict[str, Any]]:
    """Return detected monitors using ``mss`` first, ``xrandr`` as fallback."""
    return _monitors_from_mss() or _monitors_from_xrandr() or []


def _read_log_tail(path: Path) -> str:
    try:
        size = path.stat().st_size
    except OSError:
        return ""
    with path.open("rb") as handle:
        if size > _MAX_LOG_BYTES:
            handle.seek(size - _MAX_LOG_BYTES)
        return handle.read().decode("utf-8", errors="replace")


def _last_failure_line(text: str) -> str | None:
    last: str | None = None
    for line in text.splitlines():
        if line.startswith(_FAILED_PREFIX):
            last = line[len(_FAILED_PREFIX) :].strip()
    return last


def _wayland_hint(session: str) -> str:
    if session == "wayland":
        return (
            "GNOME/Wayland blocks silent screenshots for unsandboxed apps. "
            "Try KORU_VISION_PROVIDER=portal_screencast and accept the screen-share "
            "dialog once (PipeWire + xdg-desktop-portal), or KORU_VISION_PROVIDER=portal "
            "for one-shot portal screenshots. X11 session ('Ubuntu on Xorg') also works."
        )
    return ""


def capture_diagnostics(project: Path) -> dict[str, Any]:
    """Return JSON-friendly diagnostics for ``/api/mesh/diagnostics``.

    Shape::

        {
          "session_type": "wayland",
          "monitors": [
            {"id": 0, "output": "DP-3", "width": 3840, "height": 2160}
          ],
          "last_error": "no screenshot backend succeeded; ...",
          "status": "blocked" | "ok" | "no-log",
          "hint": "..."
        }
    """
    log_path = project / _VISION_LOG_REL
    monitors = detect_monitors()
    log_text = _read_log_tail(log_path) if log_path.is_file() else ""
    last_error = _last_failure_line(log_text) if log_text else None
    if not log_text:
        status = "no-log"
    elif last_error:
        status = "blocked"
    else:
        status = "ok"
    session = _session_type()
    ranked: list[str] = []
    providers: list[dict[str, Any]] = []
    try:
        from koruvision.providers.detector import provider_diagnostics_rows

        ranked, providers = provider_diagnostics_rows()
    except Exception:
        pass
    return {
        "session_type": session,
        "monitors": monitors,
        "ranked_providers": ranked,
        "providers": providers,
        "last_error": last_error,
        "status": status,
        "hint": _wayland_hint(session) if status == "blocked" else "",
    }
