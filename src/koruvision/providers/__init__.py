"""Capture provider plugins for :mod:`koruvision.capture`."""

from vdisplay.capture import BlackFrameError, ProviderAvailability

from koruvision.providers.detector import (
    capture_all_with_providers,
    capture_one_with_providers,
    list_provider_status,
    probe_capture_providers,
    provider_diagnostics_rows,
    rank_providers,
)

__all__ = [
    "BlackFrameError",
    "ProviderAvailability",
    "capture_all_with_providers",
    "capture_one_with_providers",
    "list_provider_status",
    "provider_diagnostics_rows",
    "rank_providers",
    "probe_capture_providers",
]
