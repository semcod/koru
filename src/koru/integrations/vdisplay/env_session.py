"""Session / prepare env helpers extracted from ``vdisplay_client``.

Keeps prepare-scoped capture pointers in ``os.environ`` without pulling the
full vdisplay control plane. Re-exported from ``vdisplay_client`` for
backward-compatible imports.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def clear_stale_observe_session_env() -> None:
    """Drop prepare-scoped capture pointers so perform can use fresh or map-based VQL."""
    for key in (
        "KORU_AUTONOMY_SESSION_DIR",
        "KORU_VDISPLAY_PHOTO_PATH",
        "KORU_VDISPLAY_VQL_PATH",
        "KORU_VDISPLAY_CAPTURE_MATCHES_IDE",
    ):
        os.environ.pop(key, None)


def sync_prepare_capture_flags_to_env(prepare: dict[str, Any]) -> None:
    """Restore capture guard env from a reused observe/prepare payload."""
    source = str(prepare.get("source") or "").strip()
    if source:
        os.environ["KORU_VDISPLAY_SOURCE"] = source
    session_raw = str(prepare.get("session_dir") or "").strip()
    if session_raw:
        session_path = Path(session_raw).expanduser()
        if not session_path.is_absolute():
            session_path = (Path.cwd() / session_path).resolve()
        if session_path.is_dir():
            os.environ["KORU_AUTONOMY_SESSION_DIR"] = str(session_path)
    png = str(prepare.get("png") or "").strip()
    if png:
        png_path = Path(png).expanduser()
        if png_path.is_file():
            os.environ["KORU_VDISPLAY_PHOTO_PATH"] = str(png_path.resolve())
            vql = png_path.with_suffix(png_path.suffix + ".vql.json")
            if vql.is_file():
                os.environ["KORU_VDISPLAY_VQL_PATH"] = str(vql.resolve())
    if prepare.get("surface_only_fallback"):
        os.environ["KORU_VDISPLAY_SURFACE_ONLY_FALLBACK"] = "1"
        if prepare.get("capture_confirmed"):
            os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
        else:
            os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)
    elif prepare.get("capture_confirmed") and prepare.get("ok"):
        os.environ.pop("KORU_VDISPLAY_SURFACE_ONLY_FALLBACK", None)
        os.environ["KORU_VDISPLAY_CAPTURE_MATCHES_IDE"] = "1"
    else:
        os.environ.pop("KORU_VDISPLAY_SURFACE_ONLY_FALLBACK", None)
        os.environ.pop("KORU_VDISPLAY_CAPTURE_MATCHES_IDE", None)


def session_type() -> str:
    """Best-effort XDG session type: wayland / x11 / headless."""
    explicit = (os.environ.get("XDG_SESSION_TYPE") or "").strip().lower()
    if explicit in {"wayland", "x11"}:
        return explicit
    if (os.environ.get("WAYLAND_DISPLAY") or "").strip():
        return "wayland"
    if (os.environ.get("DISPLAY") or "").strip():
        return "x11"
    return explicit or "headless"


def dry_run_enabled() -> bool:
    return os.environ.get("KORU_VDISPLAY_DRY_RUN", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


__all__ = [
    "clear_stale_observe_session_env",
    "dry_run_enabled",
    "session_type",
    "sync_prepare_capture_flags_to_env",
]
