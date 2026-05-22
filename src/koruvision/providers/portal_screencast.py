"""Continuous capture via xdg-desktop-portal ScreenCast + GStreamer pipewiresrc."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from typing import Any

from koruvision.portal_capture import _portal_python
from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png
from koruvision.providers.env import portal_possible, tool_available
from koruvision.providers.screencast_session import (
    clear_session_file,
    resolve_screencast_session_file,
)

# argv: out_dir, scale, session_file (optional JSON cache path)
_SCREENCAST_SCRIPT = r"""
import base64
import json
import os
import subprocess
import sys

import dbus
from dbus import UInt32
import dbus.mainloop.glib
from gi.repository import GLib

OUT_DIR = sys.argv[1]
SCALE = float(sys.argv[2])
SESSION_FILE = sys.argv[3] if len(sys.argv) > 3 else ""


def _gst_frames(fd, streams, out_dir, scale):
    frames = []
    for index, stream in enumerate(streams):
        node_id = int(stream[0])
        props = stream[1] if len(stream) > 1 else {}
        size = props.get("size", {}) if isinstance(props, dict) else {}
        native_w = int(size.get("width", 1920) or 1920)
        native_h = int(size.get("height", 1080) or 1080)
        thumb_w = max(1, int(native_w * scale))
        thumb_h = max(1, int(native_h * scale))
        path = os.path.join(out_dir, f"monitor-{index}.png")
        pipeline = (
            f"pipewiresrc fd={fd} path={node_id} do-timestamp=true ! "
            f"videoconvert ! videoscale ! video/x-raw,width={thumb_w},height={thumb_h} ! "
            f"pngenc snapshot=true ! filesink location={path}"
        )
        proc = subprocess.run(
            ["gst-launch-1.0", "-e", pipeline],
            capture_output=True,
            timeout=30,
            check=False,
            pass_fds=[fd],
        )
        if proc.returncode != 0 or not os.path.isfile(path):
            stderr = (proc.stderr or b"").decode("utf-8", errors="replace")[-400:]
            print(f"monitor {index}: gst failed: {stderr}", file=sys.stderr)
            continue
        with open(path, "rb") as handle:
            payload = handle.read()
        frames.append(
            {
                "monitor_id": index,
                "output": str(props.get("id", f"monitor-{index}")),
                "native_width": native_w,
                "native_height": native_h,
                "payload_b64": base64.b64encode(payload).decode("ascii"),
            }
        )
    return frames


def _wait_session_request(session_iface, session_path, token, method_name, options):
    # Wait for a portal Request response (SelectSources or Start).
    bus = dbus.SessionBus()
    sender = bus.get_unique_name()[1:].replace(".", "_")
    request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
    state = {"error": None, "result": None}

    def _on_response(response, results):
        if int(response) != 0:
            state["error"] = f"portal response code {response}"
        else:
            state["result"] = results
        loop.quit()

    bus.add_signal_receiver(
        _on_response,
        dbus_interface="org.freedesktop.portal.Request",
        path=request_path,
        signal_name="Response",
    )
    opts = dict(options)
    opts.setdefault("handle_token", token)
    if method_name == "SelectSources":
        session_iface.SelectSources(session_path, opts)
    elif method_name == "Start":
        session_iface.Start(session_path, "", opts)
    else:
        raise RuntimeError(f"unsupported portal method {method_name!r}")
    loop = GLib.MainLoop()
    GLib.timeout_add(120000, lambda: (loop.quit(), False)[1])
    loop.run()
    if state.get("error"):
        raise RuntimeError(state["error"])
    return state.get("result") or {}


def _wait_start(session_iface, session_path, token):
    result = _wait_session_request(
        session_iface,
        session_path,
        token,
        "Start",
        {"handle_token": token},
    )
    streams = result.get("streams") or []
    if not streams:
        raise RuntimeError("screencast: no streams in portal response")
    remote = session_iface.OpenPipeWireRemote(session_path, {})
    fd = int(remote.take())
    return fd, streams


def _try_reuse(session_path):
    bus = dbus.SessionBus()
    session_iface = dbus.Interface(
        bus.get_object("org.freedesktop.portal.Desktop", session_path),
        "org.freedesktop.portal.Session",
    )
    fd, streams = _wait_start(session_iface, session_path, "koruvision_screencast_reuse")
    return _gst_frames(fd, streams, OUT_DIR, SCALE)


def _full_flow():
    bus = dbus.SessionBus()
    token = "koruvision_screencast"
    proxy = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
    iface = dbus.Interface(proxy, "org.freedesktop.portal.ScreenCast")
    session_path = iface.CreateSession({"handle_token": token + "_session", "persist_mode": 2})
    session_iface = dbus.Interface(
        bus.get_object("org.freedesktop.portal.Desktop", session_path),
        "org.freedesktop.portal.Session",
    )
    # GNOME requires an async SelectSources request (picker dialog) before Start.
    _wait_session_request(
        session_iface,
        session_path,
        token + "_select",
        "SelectSources",
        {
            "types": UInt32(1),
            "multiple": True,
            "cursor_mode": UInt32(2),
            "handle_token": token + "_select",
        },
    )
    fd, streams = _wait_start(session_iface, session_path, token)
    frames = _gst_frames(fd, streams, OUT_DIR, SCALE)
    return frames, session_path


def _load_saved_session():
    if not SESSION_FILE or not os.path.isfile(SESSION_FILE):
        return None
    try:
        with open(SESSION_FILE, encoding="utf-8") as handle:
            data = json.load(handle)
        path = str(data.get("session_path") or "").strip()
        return path or None
    except Exception:
        return None


def _save_session(session_path):
    if not SESSION_FILE or not session_path:
        return
    os.makedirs(os.path.dirname(SESSION_FILE) or ".", exist_ok=True)
    with open(SESSION_FILE, "w", encoding="utf-8") as handle:
        json.dump({"session_path": session_path}, handle)
    os.chmod(SESSION_FILE, 0o600)


dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

saved = _load_saved_session()
if saved:
    try:
        frames = _try_reuse(saved)
        if frames:
            print(json.dumps(frames))
            sys.exit(0)
    except Exception as exc:
        print(f"screencast reuse failed: {exc}", file=sys.stderr)

try:
    frames, session_path = _full_flow()
except Exception as exc:
    print(str(exc), file=sys.stderr)
    sys.exit(2)

if not frames:
    print("screencast: no frames captured", file=sys.stderr)
    sys.exit(3)

_save_session(session_path)
print(json.dumps(frames))
"""


class PortalScreenCastProvider:
    name = "portal_screencast"
    streams = True

    def availability(self) -> ProviderAvailability:
        if not portal_possible():
            return ProviderAvailability(available=False, reason="no D-Bus session")
        if not tool_available("gst-launch-1.0"):
            return ProviderAvailability(
                available=False,
                reason="gst-launch-1.0 not found",
                install_hint="apt install gstreamer1.0-tools gstreamer1.0-pipewire",
            )
        python = _portal_python()
        try:
            proc = subprocess.run(
                [python, "-c", "import dbus; import gi"],
                capture_output=True,
                timeout=5,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired):
            proc = None
        if proc is None or proc.returncode != 0:
            return ProviderAvailability(
                available=False,
                reason="system Python lacks dbus/gi",
                install_hint="apt install python3-dbus python3-gi",
            )
        session_file = resolve_screencast_session_file()
        hint = "Accept screen sharing when koru observe starts"
        if session_file.is_file():
            hint = f"cached session at {session_file} (koru observe providers reset to clear)"
        return ProviderAvailability(
            available=True,
            reason="xdg-desktop-portal ScreenCast + PipeWire",
            needs_consent=True,
            install_hint=hint,
        )

    def list_monitors(self) -> list[MonitorSpec]:
        from koruvision.providers.detector import monitors_via_xrandr

        return monitors_via_xrandr()

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        raw_frames = _screencast_frames(scale)
        return [
            frame_from_png(
                item["payload"],
                monitor_id=int(item["monitor_id"]),
                scale=scale,
                output=str(item.get("output") or ""),
                provider=self.name,
            )
            for item in raw_frames
        ]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        frames = self.capture_all(scale)
        if not frames:
            raise RuntimeError("portal_screencast: no frames captured")
        if monitor_id is None:
            return frames[0]
        for frame in frames:
            if frame["monitor_id"] == monitor_id:
                return frame
        return frames[min(monitor_id, len(frames) - 1)]


def _screencast_frames(scale: float, *, retry_without_cache: bool = True) -> list[dict[str, Any]]:
    python = _portal_python()
    session_file = resolve_screencast_session_file()
    with tempfile.TemporaryDirectory(prefix="koru-screencast-") as tmp:
        args = [python, "-c", _SCREENCAST_SCRIPT, tmp, str(scale), str(session_file)]
        proc = _run_screencast_subprocess(args)
        if proc.returncode == 0:
            return _parse_screencast_stdout(proc.stdout or "")
        if retry_without_cache and session_file.is_file():
            clear_session_file(session_file)
            print(
                "koru vision: screencast session expired — retrying with portal dialog",
                file=sys.stderr,
            )
            proc = _run_screencast_subprocess(args)
            if proc.returncode == 0:
                return _parse_screencast_stdout(proc.stdout or "")
        detail = (proc.stderr or "").strip() or f"exit {proc.returncode}"
        raise RuntimeError(f"portal screencast failed: {detail[-500:]}")


def _run_screencast_subprocess(args: list[str]) -> subprocess.CompletedProcess[str]:
    try:
        return subprocess.run(
            args,
            capture_output=True,
            timeout=130,
            text=True,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError(f"portal screencast subprocess failed: {exc}") from exc


def _parse_screencast_stdout(stdout: str) -> list[dict[str, Any]]:
    import base64

    text = stdout.strip()
    if not text:
        raise RuntimeError("portal screencast returned no JSON")
    try:
        raw = json.loads(text)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"portal screencast invalid JSON: {text[:200]}") from exc
    if not isinstance(raw, list) or not raw:
        raise RuntimeError("portal screencast captured no monitors")
    frames: list[dict[str, Any]] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        row = dict(item)
        b64 = row.pop("payload_b64", None)
        if b64 and "payload" not in row:
            row["payload"] = base64.b64decode(str(b64))
        frames.append(row)
    if not frames:
        raise RuntimeError("portal screencast captured no monitors")
    return frames
