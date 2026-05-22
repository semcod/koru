"""wlroots capture via grim (stdout PNG)."""

from __future__ import annotations

import subprocess
from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability, frame_from_png
from koruvision.providers.env import tool_available


class GrimProvider:
    name = "grim"
    streams = False

    def availability(self) -> ProviderAvailability:
        if not tool_available("grim"):
            return ProviderAvailability(available=False, reason="grim not installed", install_hint="apt install grim")
        return ProviderAvailability(available=True, reason="grim (wlroots screencopy)")

    def list_monitors(self) -> list[MonitorSpec]:
        from koruvision.providers.detector import monitors_via_xrandr

        return monitors_via_xrandr()

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        payload = _grim_png()
        return [frame_from_png(payload, monitor_id=0, scale=scale, output="grim", provider=self.name)]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        return self.capture_all(scale)[0]


def _grim_png() -> bytes:
    proc = subprocess.run(  # noqa: S603
        ["grim", "-"],
        capture_output=True,
        timeout=15,
        check=False,
    )
    if proc.returncode != 0 or not proc.stdout:
        stderr = (proc.stderr or b"").decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"grim failed ({proc.returncode}): {stderr[-300:]}")
    return proc.stdout
