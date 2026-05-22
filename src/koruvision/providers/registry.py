"""Built-in capture provider instances."""

from __future__ import annotations

from koruvision.providers.base import CaptureProvider
from koruvision.providers.browser_getdisplay import BrowserGetDisplayProvider
from koruvision.providers.cli_tools import CliToolsProvider
from koruvision.providers.grim import GrimProvider
from koruvision.providers.mss import MssProvider
from koruvision.providers.obs_websocket import ObsWebSocketProvider
from koruvision.providers.portal_screencast import PortalScreenCastProvider
from koruvision.providers.portal_screenshot import PortalScreenshotProvider

_ALL: list[CaptureProvider] = [
    ObsWebSocketProvider(),
    PortalScreenCastProvider(),
    PortalScreenshotProvider(),
    MssProvider(),
    GrimProvider(),
    CliToolsProvider(),
    BrowserGetDisplayProvider(),
]

_BY_NAME: dict[str, CaptureProvider] = {provider.name: provider for provider in _ALL}


def all_providers() -> list[CaptureProvider]:
    return list(_ALL)


def provider_by_name(name: str) -> CaptureProvider | None:
    return _BY_NAME.get(name.strip().lower())
