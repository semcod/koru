"""Deterministic pointer positioning: uinput ABS device + adaptive closed loop.

Extracted from koru.integrations.vdisplay_client. These convert a capture-pixel
target into an OS pointer move+click, preferring the own uinput ABS device (a
coordinate space we own, calibrated once per monitor) over ydotool's opaque one,
with a visual closed-loop as an alternative. Koru-side helpers are imported
lazily to avoid an import cycle with vdisplay_client.
"""
from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


def _adaptive_pointer_enabled() -> bool:
    return (os.environ.get("KORU_VDISPLAY_ADAPTIVE_POINTER") or "").strip().lower() in {"1", "true", "yes", "on"}


def _adaptive_position_pointer(
    *, x: int, y: int, source: str, capture_meta: dict[str, Any], ide: str
) -> dict[str, Any] | None:
    """Closed-loop adaptive positioning via the coordinate-validation layer.

    Replaces trusting the absolute capture→global mapping (which compounds
    scale/HiDPI/axis unknowns and can miss by a whole monitor) with measured
    correction: confirm the cursor is on ``source``, then nudge until the
    observed cursor is within tolerance of the target capture pixel. Returns a
    click-result dict, or None to fall back to the open-loop mapping.
    """
    try:
        import tempfile
        from pathlib import Path as _Path

        from vdisplay.capture.coordinate_validation import (
            converge_pointer_to_local,
            which_monitor_has_cursor,
        )
        from vdisplay.input.linux_ydotool import LinuxYdotoolInput

        from koru.integrations.vdisplay_client import _photo_vql_refresh_screenshot

        yinput = LinuxYdotoolInput()

        def _move(gx: int, gy: int) -> None:
            yinput.move(int(gx), int(gy))

        _cap_dir = _Path(tempfile.mkdtemp(prefix="koru-coordval-"))

        def _capture(src: str) -> bytes:
            shot = _cap_dir / f"{src}.png"
            err = _photo_vql_refresh_screenshot(src, shot, ide)
            if err is not None:
                return b""
            try:
                return shot.read_bytes()
            except OSError:
                return b""

        # safety: is the pointer actually on the IDE's monitor?
        from vdisplay.input.coords import global_pointer_coords

        gx, gy, _ = global_pointer_coords(int(x), int(y), capture_meta)
        mon, _loc = which_monitor_has_cursor((gx, gy), [source], move=_move, capture=_capture)
        if mon is not None and mon != source:
            logger.warning(
                "ADAPTIVE_POINTER off-monitor: cursor on %s not target %s; aborting write", mon, source
            )
            return {"ok": False, "method": "adaptive-pointer", "error": f"cursor on {mon}, not {source}"}

        res = converge_pointer_to_local(
            (int(x), int(y)), capture_meta, source, move=_move, capture=_capture, tolerance_px=15.0
        )
        logger.info(
            "ADAPTIVE_POINTER converge ok=%s iters=%s err=%s landed_global=%s local=(%s,%s)",
            res.ok, res.iterations, res.final_error_px, res.landed_global, x, y,
        )
        if not res.ok or res.landed_global is None:
            return None  # fall back to open-loop mapping
        fgx, fgy = res.landed_global
        yinput.move(int(fgx), int(fgy))
        yinput.click(1)
        return {
            "ok": True,
            "method": "adaptive-pointer-click",
            "x": int(fgx),
            "y": int(fgy),
            "local_x": int(x),
            "local_y": int(y),
            "converge_error_px": res.final_error_px,
            "iterations": res.iterations,
        }
    except Exception as exc:
        logger.warning("ADAPTIVE_POINTER failed (%s); falling back to open-loop mapping", exc)
        return None


def _abs_pointer_enabled() -> bool:
    return (os.environ.get("KORU_VDISPLAY_ABS_POINTER") or "").strip().lower() in {"1", "true", "yes", "on"}


def _abs_affine_cache_path(source: str) -> Path:
    base = Path(os.environ.get("XDG_STATE_HOME") or (Path.home() / ".local" / "state")) / "koru" / "abs_affine"
    base.mkdir(parents=True, exist_ok=True)
    return base / f"{source}.json"


def _load_or_calibrate_abs_affine(source: str) -> dict[str, Any] | None:
    """Cached per-monitor ABS→capture affine; calibrate once, reuse forever.

    The compositor maps our own uinput ABS device with a fixed linear transform,
    so a single calibration (a handful of captures) makes positioning
    deterministic. Cached to disk keyed by monitor.
    """
    import json

    cache = _abs_affine_cache_path(source)
    _recal = (os.environ.get("KORU_VDISPLAY_ABS_RECALIBRATE") or "").strip().lower() in {"1", "true", "yes", "on"}
    if cache.exists() and not _recal:
        try:
            return json.loads(cache.read_text())
        except (OSError, ValueError):
            pass
    try:
        from vdisplay.capture.coordinate_validation import calibrate_pointer_affine
        from vdisplay.input.linux_uinput_abs import LinuxUinputAbsInput
    except ImportError:
        return None
    ok, _reason = LinuxUinputAbsInput.available()
    if not ok:
        logger.warning("ABS pointer unavailable: %s", _reason)
        return None
    import subprocess

    from koru.integrations.vdisplay_client import _vdisplay_cli_path

    shot = _abs_affine_cache_path(source).with_suffix(".cal.png")
    cli = _vdisplay_cli_path()
    dev = LinuxUinputAbsInput().open()
    try:
        def _move(ax: int, ay: int) -> None:
            dev.move_abs(ax, ay)

        def _cap(_s: str) -> bytes:
            # lightweight raw screenshot (no VQL/observe processing) — calibration
            # only needs the cursor pixel, and the heavy path is ~3x slower
            try:
                subprocess.run(
                    [cli, "screenshot", "-o", str(shot), "--source", source],
                    capture_output=True, timeout=40, check=False,
                    env={**os.environ, "VDISPLAY_AGENT_URL": os.environ.get("VDISPLAY_AGENT_URL", "http://127.0.0.1:8765")},
                )
                return shot.read_bytes()
            except (OSError, subprocess.SubprocessError):
                return b""

        aff = calibrate_pointer_affine(
            source, move=_move, capture=_cap,
            probe_grid=(3, 3), global_bounds=(500, 900, 3500, 3100),
            anchor_corner=None, avoid_live_quadrants=False,
        )
    finally:
        dev.close()
    if not aff.ok or aff.samples < 3:
        logger.warning("ABS calibration failed for %s (samples=%s)", source, aff.samples)
        return None
    data = aff.to_dict()
    try:
        cache.write_text(json.dumps(data))
    except OSError:
        pass
    logger.info("ABS affine calibrated for %s: %s", source, data)
    return data


def _abs_pointer_click(*, x: int, y: int, source: str) -> dict[str, Any] | None:
    """Deterministic click via the own uinput ABS device + cached affine."""
    aff = _load_or_calibrate_abs_affine(source)
    if not aff or not aff.get("ax") or not aff.get("ay"):
        return None
    try:
        from vdisplay.input.linux_uinput_abs import LinuxUinputAbsInput
    except ImportError:
        return None
    ax_cmd = (x - aff["bx"]) / aff["ax"]
    ay_cmd = (y - aff["by"]) / aff["ay"]
    dev = LinuxUinputAbsInput().open()
    try:
        dev.move_abs_and_click(int(ax_cmd), int(ay_cmd))
    finally:
        dev.close()
    logger.info("ABS_POINTER_CLICK local=(%s,%s) -> ABS(%d,%d) source=%s", x, y, ax_cmd, ay_cmd, source)
    return {
        "ok": True,
        "method": "uinput-abs-click",
        "abs_x": int(ax_cmd),
        "abs_y": int(ay_cmd),
        "local_x": int(x),
        "local_y": int(y),
    }
