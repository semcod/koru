"""Low-level mss + native-screenshot primitives shared by :mod:`koruvision.providers`.

This module used to orchestrate the full ``mss → portal → command`` fallback
chain. That responsibility now lives in :mod:`koruvision.providers.detector`
(ranked provider list), so the helpers below are intentionally narrow:

* ``BlackFrameError`` + ``_grab_single_mss_raw`` / ``_grab_all_mss_raw`` —
  the actual ``mss`` calls. Tests monkeypatch these directly.
* ``command_candidates`` / ``run_png_command`` / ``command_capture_dict`` —
  shell out to the native screenshot CLIs (``grim``, ``spectacle``,
  ``scrot``…). Wrapped by :class:`koruvision.providers.cli_tools.CliToolsProvider`.
* ``portal_capture_dict`` — single-shot portal screenshot wrapper.
* ``png_dimensions`` / ``png_payload_descriptor`` / ``frame_from_shot`` —
  byte-level helpers reused across providers.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import shutil
import struct
import subprocess
import sys
import tempfile
from datetime import UTC, datetime
from typing import Any

from koruvision.scaling import downscale_rgb_nearest, rgb_mostly_black


class BlackFrameError(RuntimeError):
    """Captured buffer is empty/black (common with XWayland + ``mss``)."""


_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def is_wayland() -> bool:
    """True when the active session is Wayland (kept for backward compatibility)."""
    return (
        os.environ.get("XDG_SESSION_TYPE", "").strip().lower() == "wayland"
        or bool(os.environ.get("WAYLAND_DISPLAY", "").strip())
    )


def png_dimensions(payload: bytes) -> tuple[int, int]:
    if len(payload) >= 24 and payload.startswith(_PNG_SIGNATURE) and payload[12:16] == b"IHDR":
        width, height = struct.unpack(">II", payload[16:24])
        return int(width), int(height)
    return 0, 0


def png_payload_descriptor(payload: bytes, *, output: str) -> dict[str, Any]:
    if not payload:
        raise RuntimeError("capture backend returned an empty image")
    width, height = png_dimensions(payload)
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


def frame_from_shot(
    shot: Any,
    *,
    monitor_id: int,
    scale: float,
    output: str = "",
) -> dict[str, Any]:
    """Encode an mss shot as a PNG payload + descriptor dict for :class:`VisionFrame`."""
    import mss.tools

    if rgb_mostly_black(shot.rgb):
        raise BlackFrameError("monitor image is mostly black")
    src_w, src_h = shot.size
    dst_w = max(1, int(src_w * scale))
    dst_h = max(1, int(src_h * scale))
    rgb = downscale_rgb_nearest(shot.rgb, src_w, src_h, dst_w, dst_h)
    payload = mss.tools.to_png(rgb, (dst_w, dst_h))
    return {
        "frame_id": hashlib.sha256(payload).hexdigest()[:16],
        "monitor_id": monitor_id,
        "captured_at": datetime.now(UTC).isoformat(),
        "mime": "image/png",
        "width": dst_w,
        "height": dst_h,
        "payload": payload,
        "native_width": src_w,
        "native_height": src_h,
        "output": output,
    }


def ordered_monitor_indices(targets: list[dict[str, Any]]) -> list[int]:
    """Return indices with the ``is_primary`` monitor(s) first."""
    primary = [index for index, monitor in enumerate(targets) if monitor.get("is_primary")]
    rest = [index for index in range(len(targets)) if index not in primary]
    return primary + rest


def portal_capture_dict() -> dict[str, Any]:
    """Capture via ``org.freedesktop.portal.Screenshot`` returning a VisionFrame descriptor."""
    from koruvision.portal_capture import PortalCaptureError, capture_portal_png

    try:
        payload = capture_portal_png()
    except PortalCaptureError as exc:
        raise RuntimeError(str(exc)) from exc
    return png_payload_descriptor(payload, output="portal")


def command_candidates() -> list[tuple[str, list[str], bool]]:
    if sys.platform == "darwin":
        return [("screencapture", ["screencapture", "-x", "-t", "png", "{path}"], False)]
    if sys.platform.startswith("linux"):
        return [
            ("grim", ["grim", "-"], True),
            ("gnome-screenshot", ["gnome-screenshot", "-f", "{path}"], False),
            ("spectacle", ["spectacle", "-b", "-n", "-o", "{path}"], False),
            ("maim", ["maim", "{path}"], False),
            # scrot 1.x refuses to overwrite an existing file; the tempfile
            # helper creates the path first so we always pass --overwrite.
            ("scrot", ["scrot", "--overwrite", "{path}"], False),
        ]
    return []


def run_png_command(binary: str, template: list[str], stdout_png: bool) -> bytes:
    exe = shutil.which(binary)
    if not exe:
        raise RuntimeError(f"{binary} not found")
    if stdout_png:
        cmd = [exe if part == binary else part for part in template]
        proc = subprocess.run(  # noqa: S603 — executable resolved with shutil.which, no shell.
            cmd,
            capture_output=True,
            timeout=15,
            check=False,
        )
        if proc.returncode == 0 and proc.stdout:
            return proc.stdout
        stderr = (proc.stderr or b"").decode("utf-8", "replace").strip()
        raise RuntimeError(f"{binary} failed ({proc.returncode}): {stderr[-300:]}")

    tmp_path = ""
    try:
        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            tmp_path = tmp.name
        # gnome-screenshot, spectacle and older scrot refuse to overwrite an
        # existing path — remove the zero-byte placeholder NamedTemporaryFile
        # leaves behind before invoking the screenshot binary.
        with contextlib.suppress(OSError):
            os.unlink(tmp_path)
        cmd = [exe if part == binary else part.format(path=tmp_path) for part in template]
        proc = subprocess.run(  # noqa: S603 — executable resolved with shutil.which, no shell.
            cmd,
            capture_output=True,
            timeout=15,
            check=False,
        )
        if proc.returncode != 0:
            stderr = (proc.stderr or b"").decode("utf-8", "replace").strip()
            raise RuntimeError(f"{binary} failed ({proc.returncode}): {stderr[-300:]}")
        if not os.path.isfile(tmp_path):
            raise RuntimeError(f"{binary} did not write {tmp_path}")
        with open(tmp_path, "rb") as handle:
            return handle.read()
    finally:
        if tmp_path:
            with contextlib.suppress(OSError):
                os.unlink(tmp_path)


def command_capture_dict() -> dict[str, Any]:
    errors: list[str] = []
    for binary, template, stdout_png in command_candidates():
        try:
            return png_payload_descriptor(
                run_png_command(binary, template, stdout_png),
                output=binary,
            )
        except Exception as exc:  # noqa: BLE001 - optional desktop tools vary by environment.
            errors.append(f"{binary}: {exc}")
    msg = "no native screenshot command worked"
    if errors:
        msg += "; " + "; ".join(errors)
    raise RuntimeError(msg)


def grab_target(grabber: Any, target: dict[str, Any], index: int, scale: float) -> dict[str, Any]:
    """Grab a single monitor through *grabber* and turn it into a VisionFrame descriptor."""
    return frame_from_shot(
        grabber.grab(target),
        monitor_id=index,
        scale=scale,
        output=str(target.get("output") or ""),
    )


def _grab_single_mss_raw(monitor_id: int | None, scale: float) -> dict[str, Any]:
    """Pick one monitor (explicit index or first non-black) via mss."""
    import mss

    with mss.mss() as grabber:
        targets = [dict(monitor) for monitor in grabber.monitors[1:]]
        if not targets:
            raise RuntimeError("no monitors detected")
        if monitor_id is not None:
            index = max(0, min(monitor_id, len(targets) - 1))
            return grab_target(grabber, targets[index], index, scale)
        last_error: Exception | None = None
        for index in ordered_monitor_indices(targets):
            try:
                return grab_target(grabber, targets[index], index, scale)
            except BlackFrameError as exc:
                last_error = exc
        msg = f"mss capture produced only black frames ({last_error})"
        raise RuntimeError(msg) from last_error


def _grab_all_mss_raw(scale: float) -> list[dict[str, Any]]:
    """Capture every monitor mss reports; log+skip blacks/errors."""
    import mss

    frames: list[dict[str, Any]] = []
    with mss.mss() as grabber:
        targets = [dict(monitor) for monitor in grabber.monitors[1:]]
        for index, target in enumerate(targets):
            try:
                frames.append(grab_target(grabber, target, index, scale))
            except BlackFrameError:
                continue
            except Exception as exc:  # noqa: BLE001 — surface in stderr, keep going
                print(
                    f"koru vision: monitor {index} capture failed: {exc}",
                    file=sys.stderr,
                )
    return frames
