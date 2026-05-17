"""Runtime bridge for IDE-related host/system capabilities.

This module centralizes legacy autopilot-dependent runtime probes so
higher-level modules (`init_host_environment`, `mcp_provision`) do not
import low-level autopilot modules directly.
"""

from __future__ import annotations

from typing import Any


def build_host_setup_report() -> dict[str, Any]:
    """Return host injector/setup probe report from the current runtime backend."""

    from koruide.host_setup import build_setup_host_report

    return build_setup_host_report()


def detect_running_ides() -> list[dict[str, Any]]:
    """Return running IDE entries as plain dictionaries.

    The current backend proxies :mod:`koruide.ide`.
    """

    from koruide.ide import detect_running_ides as detect_legacy_running_ides

    rows: list[dict[str, Any]] = []
    for ide in detect_legacy_running_ides():
        if isinstance(ide, dict):
            rows.append(dict(ide))
            continue
        to_dict = getattr(ide, "to_dict", None)
        if callable(to_dict):
            payload = to_dict()
            if isinstance(payload, dict):
                rows.append(dict(payload))
                continue
        rows.append({"id": str(ide)})
    return rows


__all__ = ["build_host_setup_report", "detect_running_ides"]
