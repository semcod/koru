"""One-shot capture via xdg-desktop-portal.Screenshot (interactive on GNOME 49+)."""

from __future__ import annotations

from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability
from koruvision.providers.env import portal_possible
class PortalScreenshotProvider:
    name = "portal_screenshot"
    streams = False

    def availability(self) -> ProviderAvailability:
        if not portal_possible():
            return ProviderAvailability(
                available=False,
                reason="no D-Bus session (portal unavailable)",
            )
        return ProviderAvailability(
            available=True,
            reason="xdg-desktop-portal Screenshot API",
            needs_consent=True,
            install_hint="Grant Screenshot in Settings → Privacy",
        )

    def list_monitors(self) -> list[MonitorSpec]:
        from koruvision.providers.detector import monitors_via_xrandr

        return monitors_via_xrandr()

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        return [self.capture_one(None, scale)]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        del monitor_id
        from koruvision.portal_capture import PortalCaptureError, capture_portal_png

        try:
            payload = capture_portal_png()
        except PortalCaptureError as exc:
            raise RuntimeError(str(exc)) from exc
        from koruvision.capture_mss import png_payload_descriptor

        return png_payload_descriptor(payload, output="portal")
