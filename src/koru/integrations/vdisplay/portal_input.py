"""Type into the IDE chat via the RemoteDesktop portal — the sanctioned Wayland
path. Grabs a frame from the portal's OWN stream, locates the chat input on it
(OCR anchor), and injects click+type+submit in the SAME stream coordinate space
— no ydotool opacity, no ABS calibration.

Gated by KORU_VDISPLAY_PORTAL_INPUT=1. A focus guard (re-OCR after the click)
ensures keystrokes never leak into the wrong window (e.g. a shell) when the
target drifts.
"""
from __future__ import annotations

import logging
import os
import struct
from typing import Any

logger = logging.getLogger(__name__)

_session: Any = None  # reused across calls within a process


def portal_input_enabled() -> bool:
    return (os.environ.get("KORU_VDISPLAY_PORTAL_INPUT") or "").strip().lower() in {"1", "true", "yes", "on"}


def _png_size(data: bytes) -> tuple[int, int]:
    w, h = struct.unpack(">II", data[16:24])
    return int(w), int(h)


def _landmark_input_xy(frame: bytes) -> tuple[int, int] | None:
    """Locate the chat input by persistent landmarks around it, so it is found
    even when the input already holds text (placeholder gone). The Qoder
    composer sits between '+ Add Context' (above) and the 'Agent/Auto' row
    (below); target the row just under Add Context, left-aligned with it.
    """
    try:
        from vdisplay.control.vision_ocr import ocr_available, ocr_png
    except ImportError:
        return None
    ok, _ = ocr_available()
    if not ok:
        return None
    try:
        boxes = ocr_png(frame, min_confidence=40.0)
    except Exception:
        return None
    ctx = auto = None
    for b in boxes:
        t = (b.text or "").strip().lower()
        if ctx is None and "context" in t:
            ctx = b
        if auto is None and t in {"auto", "agent"}:
            auto = b
    if ctx is None:
        return None
    x = int(ctx.bounds.x + 40)
    if auto is not None:
        y = int((ctx.bounds.y + ctx.bounds.height + auto.bounds.y) / 2)
    else:
        y = int(ctx.bounds.y + ctx.bounds.height + 40)
    return x, y


def _ocr_anchor_xy(frame: bytes, ide: str) -> tuple[int, int] | None:
    try:
        from vdisplay.control.vision_chat_detect import ocr_anchor_chat_target
    except ImportError:
        ocr_anchor_chat_target = None
    if ocr_anchor_chat_target is not None:
        a = ocr_anchor_chat_target(frame, ide=ide)
        cc = (a or {}).get("click_center") or {}
        if cc.get("x") is not None:
            return int(cc["x"]), int(cc["y"])
    # placeholder gone (input has text) -> fall back to persistent landmarks
    return _landmark_input_xy(frame)


def _get_session():
    global _session
    if _session is not None:
        return _session
    from vdisplay.input.portal_remotedesktop import RemoteDesktopPortal

    ok, reason = RemoteDesktopPortal.available()
    if not ok:
        logger.warning("portal input unavailable: %s", reason)
        return None
    tok = os.environ.get("KORU_VDISPLAY_PORTAL_TOKEN") or None
    _session = RemoteDesktopPortal(restore_token=tok).open(timeout_s=90)
    if _session.restore_token:
        logger.info("portal restore_token acquired (set KORU_VDISPLAY_PORTAL_TOKEN to avoid the dialog)")
    return _session


def type_into_chat_via_portal(text: str, *, ide: str = "jetbrains", submit: bool = False) -> dict[str, Any]:
    """Full portal flow: locate the chat input on the portal's own frame and
    type (guarded). Returns a result dict."""
    p = _get_session()
    if p is None:
        return {"ok": False, "method": "portal", "error": "portal unavailable"}
    frame = p.grab_frame()
    fw, fh = _png_size(frame)
    anchor = _ocr_anchor_xy(frame, ide)
    if anchor is None:
        return {"ok": False, "method": "portal", "error": "chat input not found on portal frame"}
    fx, fy = anchor
    sx, sy = p.frame_to_stream(fx, fy, frame_w=fw, frame_h=fh)

    def _verify(before: bytes, after: bytes) -> bool:
        # focus guard: after the click, confirm the click target is still on the
        # IDE chat (the OCR anchor still resolves near it) — so a drifted click
        # onto e.g. a shell is rejected before any keystroke is sent.
        a2 = _ocr_anchor_xy(after, ide)
        if a2 is None:
            return False
        aw, ah = _png_size(after)
        s2x, s2y = p.frame_to_stream(a2[0], a2[1], frame_w=aw, frame_h=ah)
        return abs(s2x - sx) <= 120 and abs(s2y - sy) <= 120

    typed = p.type_into_input_verified(sx, sy, text, verify=_verify, submit=submit, clear_first=True)
    logger.info("PORTAL_INPUT typed=%s ide=%s stream=(%d,%d) submit=%s", typed, ide, sx, sy, submit)
    return {
        "ok": bool(typed),
        "method": "portal-remotedesktop",
        "stream_xy": [sx, sy],
        "submitted": bool(submit and typed),
        "error": None if typed else "click did not focus the chat input (guard rejected)",
    }
