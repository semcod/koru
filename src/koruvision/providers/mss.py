"""MSS (X11 / cross-platform) capture provider."""

from __future__ import annotations

from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability
from koruvision.scaling import resolve_scale


class MssProvider:
    name = "mss"
    streams = False

    def availability(self) -> ProviderAvailability:
        try:
            import mss  # noqa: F401
        except ImportError:
            return ProviderAvailability(
                available=False,
                reason="mss not installed",
                install_hint="pip install mss",
            )
        return ProviderAvailability(available=True, reason="mss screen grabber")

    def list_monitors(self) -> list[MonitorSpec]:
        import mss

        with mss.mss() as grabber:
            return [
                MonitorSpec(
                    id=index,
                    output=str(target.get("name") or target.get("output") or f"monitor-{index}"),
                    width=int(target.get("width", 0) or 0),
                    height=int(target.get("height", 0) or 0),
                    left=int(target.get("left", 0) or 0),
                    top=int(target.get("top", 0) or 0),
                    is_primary=bool(target.get("is_primary")),
                )
                for index, target in enumerate(grabber.monitors[1:])
            ]

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        from koruvision.capture_mss import _grab_all_mss_raw

        frames = _grab_all_mss_raw(resolve_scale(scale))
        if not frames:
            raise RuntimeError("all monitors returned black frames")
        return frames

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        from koruvision.capture_mss import _grab_single_mss_raw

        return _grab_single_mss_raw(monitor_id, resolve_scale(scale))
