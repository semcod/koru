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
    # the composer footer is at the BOTTOM of the panel; pick the lowest
    # 'context' match so a stray 'context' word higher up can't mislead us.
    ctxs = [b for b in boxes if "context" in (b.text or "").strip().lower()]
    autos = [b for b in boxes if (b.text or "").strip().lower() in {"auto", "agent"}]
    if not ctxs:
        return None
    ctx = max(ctxs, key=lambda b: b.bounds.y)
    x = int(ctx.bounds.x + 40)
    below = [b for b in autos if b.bounds.y > ctx.bounds.y]
    if below:
        auto = min(below, key=lambda b: b.bounds.y)
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


def _token_cache_path():
    from pathlib import Path

    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")) / "koru"
    base.mkdir(parents=True, exist_ok=True)
    return base / "portal_restore_token"


def _focus_ring_appeared(before: bytes, after: bytes, sx: int, sy: int, *, radius: int = 90) -> bool:
    """True when a blue focus ring appears near the target after the click.

    A focused input (Qoder highlights it blue) is the only reliable proof the
    click landed on the composer — pointing at the panel isn't enough. We count
    blue-dominant pixels in a window around the target and require a meaningful
    increase from before -> after. Coords are stream-space; the frames are the
    (larger) buffer, so scale the window.
    """
    try:
        import io

        import numpy as np
        from PIL import Image
    except ImportError:
        return True  # can't check -> don't block (numpy absent)
    try:
        b = np.asarray(Image.open(io.BytesIO(before)).convert("RGB"), dtype=np.int16)
        a = np.asarray(Image.open(io.BytesIO(after)).convert("RGB"), dtype=np.int16)
    except Exception:
        return True
    if b.shape != a.shape:
        return True
    fh, fw = a.shape[:2]
    # map stream coord -> frame pixel (frame buffer can be larger than stream)
    sw, sh = _session.stream_size if _session is not None else (fw, fh)
    fx = int(sx * fw / sw) if sw else sx
    fy = int(sy * fh / sh) if sh else sy
    r = int(radius * fw / sw) if sw else radius
    y0, y1 = max(0, fy - r), min(fh, fy + r)
    x0, x1 = max(0, fx - r), min(fw, fx + r)

    def blue_count(img):
        w = img[y0:y1, x0:x1]
        if w.size == 0:
            return 0
        r_, g_, bl = w[..., 0], w[..., 1], w[..., 2]
        mask = (bl > 120) & (bl > r_ + 40) & (bl > g_ + 25)
        return int(mask.sum())

    before_blue = blue_count(b)
    after_blue = blue_count(a)
    return after_blue - before_blue > 200  # a focus ring is many blue px


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
    if tok is None:
        try:
            tok = _token_cache_path().read_text().strip() or None
        except OSError:
            tok = None
    _session = RemoteDesktopPortal(restore_token=tok).open(timeout_s=90)
    # persist the (rotating) restore token so the approval dialog only shows once
    if _session.restore_token:
        try:
            _token_cache_path().write_text(_session.restore_token)
        except OSError:
            pass
    return _session


def _anchor_precise(frame: bytes, ide: str) -> tuple[int, int] | None:
    """Precise placeholder anchor only (empty input); None when input has text."""
    try:
        from vdisplay.control.vision_chat_detect import ocr_anchor_chat_target
    except ImportError:
        return None
    a = ocr_anchor_chat_target(frame, ide=ide)
    cc = (a or {}).get("click_center") or {}
    return (int(cc["x"]), int(cc["y"])) if cc.get("x") is not None else None


def type_into_chat_via_portal(text: str, *, ide: str = "jetbrains", submit: bool = False) -> dict[str, Any]:
    """Full portal flow: locate the chat input on the portal's own frame and
    type (guarded). Returns a result dict."""
    import time

    p = _get_session()
    if p is None:
        return {"ok": False, "method": "portal", "error": "portal unavailable"}

    def _target(frame: bytes) -> tuple[int, int] | None:
        fw, fh = _png_size(frame)
        xy = _ocr_anchor_xy(frame, ide)  # placeholder anchor, then landmark
        if xy is None:
            return None
        return p.frame_to_stream(xy[0], xy[1], frame_w=fw, frame_h=fh)

    frame = p.grab_frame()
    precise = _anchor_precise(frame, ide)  # empty input -> exact placeholder bbox

    # Two-pass when the input already holds text (no placeholder): a rough
    # landmark click focuses + clears it, the placeholder reappears, then we
    # re-anchor precisely on the now-empty input before typing.
    if precise is None:
        rough = _target(frame)
        if rough is None:
            return {"ok": False, "method": "portal", "error": "chat input not found on portal frame"}
        p.move_abs(*rough); time.sleep(0.35)
        p.click(); time.sleep(0.4)
        p.clear_input(200); time.sleep(0.4)
        frame = p.grab_frame()  # placeholder should be back now

    sxy = _target(frame)
    if sxy is None:
        return {"ok": False, "method": "portal", "error": "chat input not found after clear"}
    sx, sy = sxy

    def _verify(before: bytes, after: bytes) -> bool:
        # focus guard: the click must have FOCUSED the input — confirmed by the
        # blue focus ring appearing around it (Qoder highlights the focused
        # composer). Pointing at Qoder is not enough; only an actual focus change
        # lets us type, so a keystroke can never leak into the wrong window.
        if not _focus_ring_appeared(before, after, sx, sy):
            return False
        a2 = _target(after)
        return a2 is not None and abs(a2[0] - sx) <= 160 and abs(a2[1] - sy) <= 160

    typed = p.type_into_input_verified(sx, sy, text, verify=_verify, submit=submit, clear_first=True)
    logger.info("PORTAL_INPUT typed=%s ide=%s stream=(%d,%d) submit=%s", typed, ide, sx, sy, submit)
    return {
        "ok": bool(typed),
        "method": "portal-remotedesktop",
        "stream_xy": [sx, sy],
        "submitted": bool(submit and typed),
        "error": None if typed else "click did not focus the chat input (guard rejected)",
    }
