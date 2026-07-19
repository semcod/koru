"""Built-in capture provider instances."""

from __future__ import annotations

from vdisplay.capture import (
    CliToolsObservationProvider,
    GrimObservationProvider,
    MssObservationProvider,
    ObservationProvider,
    PortalScreenCastObservationProvider,
    PortalScreenshotObservationProvider,
)

from koruvision.providers.browser_getdisplay import BrowserGetDisplayProvider
from koruvision.providers.obs_websocket import ObsWebSocketProvider

_ALL: list[ObservationProvider] = [
    ObsWebSocketProvider(),
    PortalScreenCastObservationProvider(),
    PortalScreenshotObservationProvider(),
    MssObservationProvider(),
    GrimObservationProvider(),
    CliToolsObservationProvider(),
    BrowserGetDisplayProvider(),
]

_BY_NAME: dict[str, ObservationProvider] = {provider.name: provider for provider in _ALL}


def all_providers() -> list[ObservationProvider]:
    return list(_ALL)


def provider_by_name(name: str) -> ObservationProvider | None:
    return _BY_NAME.get(name.strip().lower())
