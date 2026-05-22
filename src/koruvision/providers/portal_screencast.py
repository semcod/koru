"""Continuous capture via xdg-desktop-portal ScreenCast + GStreamer pipewiresrc."""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from typing import Any

from koruvision.portal_capture import _portal_python
from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png
from koruvision.providers.env import portal_possible, tool_available

_SCREENCAST_SCRIPT = r"""
import json
import os
import subprocess
import sys

import dbus
from dbus import UInt32
import dbus.mainloop.glib
from gi.repository import GLib

dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
bus = dbus.SessionBus()
token = "koruvision_screencast"
sender = bus.get_unique_name()[1:].replace(".", "_")
request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
state = {"error": None, "result": None, "session": None}

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
proxy = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
iface = dbus.Interface(proxy, "org.freedesktop.portal.ScreenCast")

session_path = iface.CreateSession({"handle_token": token + "_session", "persist_mode": 2})
state["session"] = session_path
session_iface = dbus.Interface(
    bus.get_object("org.freedesktop.portal.Desktop", session_path),
    "org.freedesktop.portal.Session",
)
session_iface.SelectSources(
    session_path,
    {"types": UInt32(1), "multiple": True, "cursor_mode": UInt32(2)},
)
session_iface.Start(session_path, "", {"handle_token": token})

loop = GLib.MainLoop()
GLib.timeout_add(120000, lambda: (loop.quit(), False)[1])
loop.run()

if state.get("error"):
    print(state["error"], file=sys.stderr)
    sys.exit(2)
result = state.get("result") or {}
streams = result.get("streams") or []
if not streams:
    print("screencast: no streams in portal response", file=sys.stderr)
    sys.exit(3)

remote = session_iface.OpenPipeWireRemote(session_path, {})
fd = int(remote.take())
out_dir = sys.argv[1]
scale = float(sys.argv[2])
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
            "payload": payload,
        }
    )
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
        return ProviderAvailability(
            available=True,
            reason="xdg-desktop-portal ScreenCast + PipeWire",
            needs_consent=True,
            install_hint="Accept screen sharing when koru observe starts",
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


def _screencast_frames(scale: float) -> list[dict[str, Any]]:
    python = _portal_python()
    with tempfile.TemporaryDirectory(prefix="koru-screencast-") as tmp:
        try:
            proc = subprocess.run(
                [python, "-c", _SCREENCAST_SCRIPT, tmp, str(scale)],
                capture_output=True,
                timeout=130,
                text=True,
                check=False,
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise RuntimeError(f"portal screencast subprocess failed: {exc}") from exc
        if proc.returncode != 0:
            detail = (proc.stderr or "").strip() or f"exit {proc.returncode}"
            raise RuntimeError(f"portal screencast failed: {detail[-500:]}")
        stdout = (proc.stdout or "").strip()
        if not stdout:
            raise RuntimeError("portal screencast returned no JSON")
        try:
            payload = json.loads(stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"portal screencast invalid JSON: {stdout[:200]}") from exc
        if not isinstance(payload, list) or not payload:
            raise RuntimeError("portal screencast captured no monitors")
        return payload
