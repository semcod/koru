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


def _coord_cache_path(ide: str):
    from pathlib import Path

    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")) / "koru"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"portal_input_xy_{ide}"


def _cache_input_xy(ide: str, xy: tuple[int, int]) -> None:
    try:
        _coord_cache_path(ide).write_text(f"{int(xy[0])},{int(xy[1])}")
    except OSError:
        pass


def _cached_input_xy(ide: str) -> tuple[int, int] | None:
    try:
        x, y = _coord_cache_path(ide).read_text().strip().split(",")
        return int(x), int(y)
    except (OSError, ValueError):
        return None


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


def _focused_near(after: bytes, sx: int, sy: int, *, tol: int = 160) -> bool:
    """True when a blue focus ring is PRESENT near the target in the after-click
    frame (absolute check) — works whether the input was already focused or just
    got focused. A click that missed leaves no ring near the target -> rejected,
    so a keystroke never leaks into the wrong window."""
    hit = _blue_ring_center(after)
    if hit is None:
        return False
    fx, fy, _n = hit
    p = _session
    if p is None:
        return False
    from PIL import Image  # noqa: F401
    aw, ah = _png_size(after)
    rsx, rsy = p.frame_to_stream(fx, fy, frame_w=aw, frame_h=ah)
    return abs(rsx - sx) <= tol and abs(rsy - sy) <= tol


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


def _blue_ring_center(frame: bytes) -> tuple[int, int, int] | None:
    """Center (frame px) + pixel count of the focused input's blue ring, or None.

    Manual calibration: the user clicks the chat input; Qoder draws a blue focus
    ring around it. The ring is a wide, blue-dominant band — its bbox center is
    the input. Returns (fx, fy, count).
    """
    try:
        import io

        import numpy as np
        from PIL import Image
    except ImportError:
        return None
    try:
        a = np.asarray(Image.open(io.BytesIO(frame)).convert("RGB"), dtype=np.int16)
    except Exception:
        return None
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    mask = (b > 130) & (b > r + 45) & (b > g + 30)
    ys, xs = np.nonzero(mask)
    if xs.size < 300:
        return None
    # The composer sits at the BOTTOM of the chat panel; when Qoder is busy it
    # shows other blue elements higher up (links, a 'Run Ctrl+Enter' button, a
    # generating spinner). Pick the LOWEST wide blue band (a real input focus
    # ring spans much of the panel width) so those don't mislead us.
    fh = a.shape[0]
    rows = np.bincount(ys, minlength=fh)
    wide = np.where(rows >= 120)[0]  # rows with a wide blue span = ring borders
    if wide.size == 0:
        return None
    band_y = int(wide.max())  # lowest such row
    near = np.abs(ys - band_y) < 80
    if near.sum() < 200:
        return None
    fx = int(np.median(xs[near]))
    fy = int(np.median(ys[near]))
    return fx, fy, int(near.sum())


def calibrate_input_from_focus(*, ide: str = "jetbrains") -> dict[str, Any]:
    """One-time manual calibration: with the chat input CLICKED/focused by the
    user, detect its blue focus ring and cache the stream coords. Deterministic
    thereafter — no OCR variance."""
    p = _get_session()
    if p is None:
        return {"ok": False, "error": "portal unavailable"}
    frame = p.grab_frame()
    fw, fh = _png_size(frame)
    hit = _blue_ring_center(frame)
    if hit is None:
        return {"ok": False, "error": "no focus ring found — click inside the Qoder input first"}
    fx, fy, n = hit
    sx, sy = p.frame_to_stream(fx, fy, frame_w=fw, frame_h=fh)
    _cache_input_xy(ide, (sx, sy))
    logger.info("PORTAL_CALIBRATED ide=%s frame=(%d,%d) stream=(%d,%d) ring_px=%d", ide, fx, fy, sx, sy, n)
    return {"ok": True, "ide": ide, "stream_xy": [sx, sy], "frame_xy": [fx, fy], "ring_px": n}


def _pending_action_present(frame: bytes) -> bool:
    """True when Qoder shows a pending-action confirmation ('Run Ctrl+Enter /
    Cancel Ctrl+Backspace'). Detected by the distinctive 'Ctrl+Backspace' cancel
    shortcut inside the chat panel (right half, above the terminal region) so a
    stray 'ctrl-enter' elsewhere on screen can't trigger a false confirm.
    """
    try:
        from vdisplay.control.vision_ocr import ocr_available, ocr_png
    except ImportError:
        return False
    ok, _ = ocr_available()
    if not ok:
        return False
    try:
        boxes = ocr_png(frame, min_confidence=35.0)
    except Exception:
        return False
    fw, fh = _png_size(frame)
    for b in boxes:
        t = (b.text or "").strip().lower()
        # 'Backspace' appears only in the 'Cancel Ctrl+Backspace' confirm button;
        # match it alone (OCR often misreads 'Ctrl' as 'ctri', l->i).
        if "backspace" in t:
            # inside the chat panel (right side, not the bottom terminal strip)
            if b.bounds.x > fw * 0.45 and b.bounds.y < fh * 0.62:
                return True
    return False


def confirm_pending_via_portal(*, ide: str = "jetbrains") -> dict[str, Any]:
    """If Qoder is waiting on a 'Run Ctrl+Enter' action, focus the chat and press
    Ctrl+Enter to confirm it. Returns {confirmed: bool}."""
    p = _get_session()
    if p is None:
        return {"ok": False, "error": "portal unavailable"}
    frame = p.grab_frame()
    if not _pending_action_present(frame):
        return {"ok": True, "confirmed": False, "reason": "no pending action"}
    cached = _cached_input_xy(ide)
    if cached is None:
        return {"ok": False, "error": "not calibrated (run calibrate_input_from_focus)"}
    import time

    sx, sy = cached
    p.move_abs(sx, sy); time.sleep(0.3)  # noqa: E702
    p.click(); time.sleep(0.4)                   # click the chat panel -> Qoder gets kb focus  # noqa: E702
    # light guard: a confirm sends no text, so we don't need the input focus
    # ring — just verify we're still on Qoder (the pending button is still there,
    # i.e. the click didn't switch to another app) before the Ctrl+Enter.
    if not _pending_action_present(p.grab_frame()):
        return {"ok": False, "confirmed": False, "error": "pending action gone after click (not on Qoder?)"}
    p.submit(mode="ctrl-enter")                  # Run Ctrl+Enter
    logger.info("PORTAL_CONFIRM pressed Ctrl+Enter on pending action at (%d,%d)", sx, sy)
    return {"ok": True, "confirmed": True}


def autoconfirm_loop_via_portal(
    *, ide: str = "jetbrains", duration_s: float = 120.0, poll_s: float = 1.5, idle_polls: int = 40,
) -> dict[str, Any]:
    """Drive Qoder's agent: poll continuously and press Ctrl+Enter on each
    pending 'Run' action as it appears. The button is TRANSIENT (shows only while
    the agent waits), so keep polling — an empty frame doesn't mean 'done', the
    agent may be generating the next action. Stops after ``idle_polls`` consecutive
    empty polls (agent truly idle) or ``duration_s``."""
    import time

    p = _get_session()  # open once, reuse the session for the whole loop
    if p is None:
        return {"ok": False, "error": "portal unavailable"}
    confirmed = 0
    empties = 0
    deadline = None  # set after first grab (Date/monotonic via time.monotonic)  # noqa: F841
    start = time.monotonic()
    while time.monotonic() - start < duration_s and empties < idle_polls:
        try:
            present = _pending_action_present(p.grab_frame())
        except Exception:
            present = False
        if present:
            res = confirm_pending_via_portal(ide=ide)
            if res.get("confirmed"):
                confirmed += 1
                empties = 0
                time.sleep(poll_s)
                continue
        empties += 1
        time.sleep(poll_s)
    logger.info("PORTAL_AUTOCONFIRM confirmed %d action(s) over %.0fs", confirmed, time.monotonic() - start)
    return {"ok": True, "confirmed": confirmed}


def _env_truthy(name: str) -> bool:
    return (os.environ.get(name) or "").strip().lower() in {"1", "true", "yes", "on"}


def _portal_type_result(
    *,
    ok: bool,
    method: str,
    sx: int | None = None,
    sy: int | None = None,
    submit: bool = False,
    typed: bool = False,
    error: str | None = None,
) -> dict[str, Any]:
    out: dict[str, Any] = {
        "ok": ok,
        "method": method,
        "error": error,
    }
    if sx is not None and sy is not None:
        out["stream_xy"] = [sx, sy]
        out["submitted"] = bool(submit and typed)
    return out


def _maybe_autoremember_focused_input(p: Any, ide: str) -> None:
    """Opt-in: cache blue-ring focus position. Off by default (busy screens)."""
    if not _env_truthy("KORU_VDISPLAY_PORTAL_AUTOREMEMBER"):
        return
    try:
        f0 = p.grab_frame()
        ring = _blue_ring_center(f0)
        if ring is None:
            return
        fw0, fh0 = _png_size(f0)
        rsx, rsy = p.frame_to_stream(ring[0], ring[1], frame_w=fw0, frame_h=fh0)
        _cache_input_xy(ide, (rsx, rsy))
        logger.info("PORTAL_REMEMBER focused input at stream=(%d,%d)", rsx, rsy)
    except Exception:
        pass


def _stream_target_from_ocr(p: Any, frame: bytes, ide: str) -> tuple[int, int] | None:
    fw, fh = _png_size(frame)
    xy = _ocr_anchor_xy(frame, ide)  # placeholder anchor, then landmark
    if xy is None:
        return None
    return p.frame_to_stream(xy[0], xy[1], frame_w=fw, frame_h=fh)


def _type_at_stream_coords(
    p: Any,
    text: str,
    *,
    sx: int,
    sy: int,
    submit: bool,
    method: str,
    log_label: str,
) -> dict[str, Any]:
    def _verify(before: bytes, after: bytes) -> bool:
        # Focus guard: blue ring near target confirms the composer got focus.
        return _focused_near(after, sx, sy)

    typed = p.type_into_input_verified(
        sx,
        sy,
        text,
        verify=_verify,
        submit=submit,
        clear_first=True,
        submit_mode="ctrl-enter",
    )
    logger.info("%s typed=%s stream=(%d,%d) submit=%s", log_label, typed, sx, sy, submit)
    return _portal_type_result(
        ok=bool(typed),
        method=method,
        sx=sx,
        sy=sy,
        submit=submit,
        typed=bool(typed),
        error=None if typed else "click did not focus the chat input (guard rejected)",
    )


def _precise_stream_xy(p: Any, frame: bytes, ide: str) -> tuple[int, int] | None:
    """Empty-input placeholder anchor in stream coords, or None."""
    precise_fx = _anchor_precise(frame, ide)
    if precise_fx is None:
        return None
    fw, fh = _png_size(frame)
    return p.frame_to_stream(precise_fx[0], precise_fx[1], frame_w=fw, frame_h=fh)


def _clear_and_reanchor_stream_xy(
    p: Any,
    frame: bytes,
    ide: str,
) -> tuple[tuple[int, int] | None, str | None]:
    """Two-pass when the input already holds text (no placeholder).

    Rough click → focus guard → clear → re-anchor on empty placeholder.
    Returns ``(stream_xy, error)``; on success ``error`` is None.
    """
    import time

    # Prefer cached known-good position over flaky landmark.
    rough = _cached_input_xy(ide) or _stream_target_from_ocr(p, frame, ide)
    if rough is None:
        return None, "chat input not found (no anchor/landmark/cache)"
    rx, ry = rough
    p.move_abs(rx, ry)
    time.sleep(0.35)
    p.click()
    time.sleep(0.4)
    # Focus guard BEFORE destructive clear (up to 200 deletes).
    if not _focused_near(p.grab_frame(), rx, ry):
        return None, "click did not focus the chat input (guard rejected before clear)"
    p.clear_input(200)
    time.sleep(0.4)
    frame = p.grab_frame()  # placeholder should be back now
    re = _anchor_precise(frame, ide)
    if re is not None:
        fw, fh = _png_size(frame)
        return p.frame_to_stream(re[0], re[1], frame_w=fw, frame_h=fh), None
    return _cached_input_xy(ide), None


def type_into_chat_via_portal(text: str, *, ide: str = "jetbrains", submit: bool = False) -> dict[str, Any]:
    """Full portal flow: locate the chat input on the portal's own frame and
    type (guarded). Returns a result dict."""
    p = _get_session()
    if p is None:
        return _portal_type_result(ok=False, method="portal", error="portal unavailable")

    _maybe_autoremember_focused_input(p, ide)

    # Calibrated/cached coords beat flaky OCR — the composer doesn't move.
    cached = _cached_input_xy(ide)
    if cached is not None:
        sx, sy = cached
        return _type_at_stream_coords(
            p,
            text,
            sx=sx,
            sy=sy,
            submit=submit,
            method="portal-remotedesktop-cached",
            log_label="PORTAL_INPUT(cached)",
        )

    frame = p.grab_frame()
    precise = _precise_stream_xy(p, frame, ide)
    if precise is not None:
        _cache_input_xy(ide, precise)  # seed: the input doesn't move
    else:
        precise, err = _clear_and_reanchor_stream_xy(p, frame, ide)
        if err is not None:
            return _portal_type_result(ok=False, method="portal", error=err)
        frame = p.grab_frame()

    sx_sy = precise or _stream_target_from_ocr(p, frame, ide)
    if sx_sy is None:
        return _portal_type_result(
            ok=False, method="portal", error="chat input not found after clear"
        )
    sx, sy = sx_sy
    return _type_at_stream_coords(
        p,
        text,
        sx=sx,
        sy=sy,
        submit=submit,
        method="portal-remotedesktop",
        log_label=f"PORTAL_INPUT ide={ide}",
    )
