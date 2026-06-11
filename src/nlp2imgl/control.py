from __future__ import annotations

from typing import Any


def apply_nl_with_diag(prompt: str, *, image: str | None = None, window: str | None = None, execute: bool = True, dry_run: bool = False, with_diagnostics: bool = False) -> dict[str, Any]:
    # Minimal logic: consult imgl.autodiag if available to emulate blocking
    try:
        from imgl.autodiag import diagnose_capture
    except Exception:
        diagnose_capture = None

    if diagnose_capture is not None:
        diag = diagnose_capture(image)
        # Block on stale/blank captures depending on env vars
        import os

        if diag and not diag.get("ok") and diag.get("verdict") == "stale_capture":
            if os.environ.get("KORU_IMGL_STALE_BLOCK", "") in {"1", "true", "yes"}:
                return {"ok": False, "blocked_by": "stale_capture", "diagnostics": {**diag, "verdict": "stale_capture_error"}}
        if diag and diag.get("verdict") == "blank_capture":
            if os.environ.get("KORU_IMGL_DIAG_BLOCK", "") in {"1", "true", "yes"}:
                return {"ok": False, "blocked_by": "capture_diagnose", "diagnostics": {**diag, "verdict": "blank_capture_error"}}

    return {"ok": True, "verb": "TYPE", "output": prompt, "data": {"execute": {"ok": True, "method": "xdotool", "dry_run": dry_run}}}


def apply_nl(prompt: str, **_kwargs) -> dict[str, Any]:
    return {"ok": True, "output": prompt}


def default_image_path() -> str:
    return "/tmp/koru-imgl-screen.png"


def default_window() -> str:
    return "region-bottom"


def doctor_capture(image: str, **_kwargs) -> dict[str, Any]:
    return {"ok": True, "capture": {"path": image}}
