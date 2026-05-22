"""Native CLI screenshot tools (grim, scrot, spectacle — via capture_mss shim)."""

from __future__ import annotations

from typing import Any

from koruvision.providers.base import MonitorSpec, ProviderAvailability


class CliToolsProvider:
    name = "cli_tools"
    streams = False

    def availability(self) -> ProviderAvailability:
        from koruvision.capture_mss import command_candidates

        for binary, _, _ in command_candidates():
            if _tool_available(binary):
                return ProviderAvailability(available=True, reason=f"{binary} found")
        return ProviderAvailability(
            available=False,
            reason="no supported CLI screenshot tool",
            install_hint="install grim (wlroots) or scrot (X11)",
        )

    def list_monitors(self) -> list[MonitorSpec]:
        from koruvision.providers.detector import monitors_via_xrandr

        return monitors_via_xrandr()

    def capture_all(self, scale: float) -> list[dict[str, Any]]:
        del scale
        from koruvision.capture_mss import command_capture_dict

        return [command_capture_dict()]

    def capture_one(self, monitor_id: int | None, scale: float) -> dict[str, Any]:
        del monitor_id
        return self.capture_all(scale)[0]


def _tool_available(name: str) -> bool:
    import shutil

    return bool(shutil.which(name))
