"""Wayland-friendly screenshot via XDG Desktop Portal (optional ``dbus-python``)."""

from __future__ import annotations

import urllib.parse
import uuid
from pathlib import Path


class PortalCaptureError(RuntimeError):
    """Portal screenshot failed or ``dbus-python`` is missing."""


def capture_portal_png(*, timeout_seconds: float = 12.0) -> bytes:
    """Capture the screen through ``org.freedesktop.portal.Screenshot``."""
    try:
        import dbus
        import dbus.mainloop.glib
    except ImportError as exc:
        msg = "portal capture requires dbus-python (pip install 'koru[observe]')"
        raise PortalCaptureError(msg) from exc

    try:
        from gi.repository import GLib
    except ImportError as exc:
        msg = "portal capture requires PyGObject (pip install 'koru[observe]')"
        raise PortalCaptureError(msg) from exc

    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)
    bus = dbus.SessionBus()
    token = f"koruvision{uuid.uuid4().hex}"
    sender = bus.get_unique_name()[1:].replace(".", "_")
    request_path = f"/org/freedesktop/portal/desktop/request/{sender}/{token}"
    state: dict[str, object] = {"uri": None, "error": None}

    def _on_response(response: int, results: dict) -> None:
        if int(response) != 0:
            state["error"] = f"portal response code {response}"
        elif "uri" in results:
            state["uri"] = str(results["uri"])
        else:
            state["error"] = "portal response missing uri"
        loop.quit()

    bus.add_signal_receiver(
        _on_response,
        dbus_interface="org.freedesktop.portal.Request",
        path=request_path,
        signal_name="Response",
    )
    proxy = bus.get_object("org.freedesktop.portal.Desktop", "/org/freedesktop/portal/desktop")
    iface = dbus.Interface(proxy, "org.freedesktop.portal.Screenshot")
    iface.Screenshot("", {"handle_token": token, "interactive": False})

    loop = GLib.MainLoop()
    GLib.timeout_add(int(timeout_seconds * 1000), lambda: (loop.quit(), False)[1])
    loop.run()

    if state.get("error"):
        raise PortalCaptureError(str(state["error"]))
    uri = state.get("uri")
    if not uri:
        raise PortalCaptureError(
            "portal screenshot timed out — grant Screenshot permission in Settings → Privacy"
        )
    path = Path(urllib.parse.unquote(urllib.parse.urlparse(str(uri)).path))
    try:
        return path.read_bytes()
    except OSError as exc:
        raise PortalCaptureError(f"cannot read portal screenshot at {path}") from exc
