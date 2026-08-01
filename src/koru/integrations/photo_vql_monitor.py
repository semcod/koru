"""Monitor/source resolution for photo-VQL capture — koru's binding.

The monitor topology moved to :mod:`vdisplay.monitors` on 2026-07-23: which
physical screen an IDE surface lives on, how DP-* outputs rank, whether two
renamed outputs are the same display by geometry. That is knowledge about
screens, and vdisplay owns it.

koru keeps only what is koru's own contract:

* ``KORU_VDISPLAY_SOURCE`` — koru's environment override. vdisplay's
  ``resolve_vdisplay_source_for_ide`` takes the value as ``explicit_source``;
  this module reads the variable and passes it in.
* :func:`format_wayland_vdisplay_operator_hint` — a koru-CLI operator hint
  (``koru autopilot vdisplay-up``, the koru dashboard on :8765,
  ``KORU_ALLOW_BLIND_KEYBOARD_FALLBACK``). It describes koru, not any display,
  and stays here in full.

``resolve_vdisplay_source_for_ide`` and ``map_capture_monitor_mismatch`` are
re-exported with the same names so existing call sites and the tests that
patch them keep working; the resolve wrapper injects the env override.
"""

from __future__ import annotations

import os
from typing import Any


def _monitor_api() -> tuple[Any, Any]:
    """Load the optional, versioned vdisplay monitor API only when needed.

    Queue and headless autonomy commands do not use screen capture.  Importing
    this integration during CLI startup must therefore not make every Koru
    command depend on the newest vdisplay package being installed.
    """
    try:
        from vdisplay.monitors import map_capture_monitor_mismatch as map_mismatch
        from vdisplay.monitors import resolve_vdisplay_source_for_ide as resolve_source
    except ImportError as exc:
        raise RuntimeError(
            "vdisplay monitor support is unavailable; install/update the optional "
            "vdisplay integration before using photo-VQL capture"
        ) from exc
    return map_mismatch, resolve_source


def map_capture_monitor_mismatch(map_path: str, *, source: str) -> dict[str, Any] | None:
    """Delegate monitor mismatch detection to the optional vdisplay package."""
    map_mismatch, _ = _monitor_api()
    return map_mismatch(map_path, source=source)


def resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    canonical_ide: Any,
    desktop_probe: Any,
    probe: dict[str, Any] | None = None,
    ide_default_source: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Resolve the capture monitor, honouring koru's ``KORU_VDISPLAY_SOURCE``."""
    _, resolve_source = _monitor_api()
    return resolve_source(
        ide,
        canonical_ide=canonical_ide,
        desktop_probe=desktop_probe,
        probe=probe,
        ide_default_source=ide_default_source,
        explicit_source=os.environ.get("KORU_VDISPLAY_SOURCE", ""),
    )


def format_wayland_vdisplay_operator_hint(*, ide: str) -> str:
    """Short operator hint for koru auto / bridge (monitor + screencast + prepare)."""
    monitor: str | None = None
    try:
        from koru.integrations.vdisplay_client import _desktop_probe

        probe = _desktop_probe(ide=ide, source=None)
        best = probe.get("ide_surface_best") if isinstance(probe, dict) else None
        if isinstance(best, dict):
            monitor = best.get("monitor_name")  # type: ignore[assignment]
    except Exception:
        pass
    if monitor:
        mon = f"koru auto-resolves capture to {monitor!r} (IDE surface)"
        bridge_source = monitor
    else:
        mon = "set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives"
        bridge_source = "HDMI-1"
    port_note = ""
    try:
        from koru.integrations.vdisplay_agent_bootstrap import is_koru_dashboard_on_port

        if is_koru_dashboard_on_port(8765):
            port_note = " (koru dashboard uses :8765 — run vdisplay-agent on :8766)"
    except ImportError:
        pass
    return (
        f"Wayland vdisplay/photo-VQL: koru autopilot vdisplay-up --ide {ide}{port_note} "
        "(starts agent + manager + opens browser bridge; in Chrome/Chromium click Share screen, "
        f"select {bridge_source}, keep the tab open); "
        f"lower-level: vdisplay services up --instance {ide} --source {bridge_source} --open-browser-bridge; "
        f"vdisplay services status --source {bridge_source}; "
        f"{mon}; koru autopilot prepare-vdisplay --ide {ide}; "
        "manual stack: vdisplay-agent serve; vdisplay electron-share start; browser bridge page; "
        "fallback keeper: vdisplay agent screencast start --force, then verify with "
        f"vdisplay agent screencast probe --via-agent --source {bridge_source}; "
        "blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
    )


__all__ = [
    "format_wayland_vdisplay_operator_hint",
    "map_capture_monitor_mismatch",
    "resolve_vdisplay_source_for_ide",
]
