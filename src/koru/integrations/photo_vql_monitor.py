"""Monitor/source resolution for photo-VQL capture."""

from __future__ import annotations

import os
from typing import Any


_IDE_DEFAULT_SOURCE: dict[str, str] = {
    "cursor": "DP-1",
    "windsurf": "DP-1",
    "antigravity": "DP-1",
    "vscode": "DP-1",
    "jetbrains": "DP-1",
    "pycharm": "DP-1",
    "idea": "DP-1",
}


def _monitor_candidate_order(
    *,
    explicit: str,
    preferred: str,
    probe: dict[str, Any],
    names: set[str],
) -> list[str]:
    candidates: list[str] = []
    for value in (explicit, preferred):
        if value and value not in candidates:
            candidates.append(value)
    for monitor in probe.get("monitors") or []:
        name = str(monitor.get("name") or "")
        if name.startswith("DP-") and name not in candidates:
            candidates.append(name)
    for monitor in probe.get("monitors") or []:
        if monitor.get("primary") and monitor.get("name"):
            name = str(monitor["name"])
            if name not in candidates:
                candidates.append(name)
    for name in sorted(names):
        if name not in candidates:
            candidates.append(name)
    return candidates


def _finalize_resolved_probe(
    probe: dict[str, Any],
    *,
    preferred: str,
    chosen: str,
    names: set[str],
) -> dict[str, Any]:
    resolved_probe = {
        **probe,
        "requested_source": preferred,
        "resolved_source": chosen,
        "source_available": chosen in names if names else None,
    }
    if names and chosen not in names:
        resolved_probe["ok"] = False
        resolved_probe["error"] = (
            f"no connected monitor for {preferred!r} "
            f"(available: {sorted(names)})"
        )
    elif chosen != preferred:
        resolved_probe["source_auto_resolved"] = True
        resolved_probe["source_was"] = preferred
        resolved_probe["ok"] = True
        resolved_probe["source_available"] = True
        resolved_probe.pop("error", None)
    else:
        resolved_probe["ok"] = bool(resolved_probe.get("ok", True))
        resolved_probe["source_available"] = chosen in names if names else None
    return resolved_probe


def _surface_preferred_monitor(probe: dict[str, Any], *, canon: str) -> str | None:
    """Best-effort monitor from correlated IDE surface (e.g. PyCharm on HDMI-1)."""
    best = probe.get("ide_surface_best")
    if not isinstance(best, dict):
        for row in probe.get("ide_surfaces") or []:
            if not isinstance(row, dict):
                continue
            if row.get("ide_hint") != canon and not (
                canon in {"jetbrains", "pycharm", "idea"} and row.get("ide_hint") == "jetbrains"
            ):
                continue
            name = str(row.get("display_name") or "").lower()
            if "toolbox" in name:
                continue
            monitor = row.get("monitor_name")
            if monitor:
                return str(monitor)
        return None
    if canon in {"jetbrains", "pycharm", "idea"} and best.get("ide_hint") not in {None, "jetbrains"}:
        return None
    monitor = best.get("monitor_name")
    return str(monitor) if monitor else None


def map_capture_monitor_mismatch(
    map_path: str,
    *,
    source: str,
) -> dict[str, Any] | None:
    """Return mismatch details when GUI map was calibrated on a different monitor."""
    try:
        from vdisplay.control.gui_map import load_gui_map

        pack = load_gui_map(map_path)
    except Exception as exc:
        return {
            "map_path": map_path,
            "capture_source": source,
            "error": str(exc),
            "message": f"could not load GUI map {map_path!r} to verify capture source",
        }
    meta = pack.capture_meta if isinstance(pack.capture_meta, dict) else {}
    map_source = str(meta.get("source") or meta.get("monitor_name") or "").strip()
    if not map_source or map_source == source:
        return None
    rotation = meta.get("rotation")
    return {
        "map_path": map_path,
        "map_source": map_source,
        "capture_source": source,
        "map_rotation": rotation,
        "message": (
            f"GUI map {map_path!r} is calibrated for monitor {map_source!r}"
            f"{f' (rotation={rotation!r})' if rotation else ''}, "
            f"but capture source is {source!r}. "
            f"Recalibrate the map or set KORU_VDISPLAY_SOURCE={map_source!r}."
        ),
    }


def resolve_vdisplay_source_for_ide(
    ide: str,
    *,
    canonical_ide: Any,
    desktop_probe: Any,
    probe: dict[str, Any] | None = None,
    ide_default_source: dict[str, str] | None = None,
) -> tuple[str, dict[str, Any]]:
    """Pick capture monitor: explicit env > IDE default > DP-* > primary > first connected."""
    defaults = ide_default_source or _IDE_DEFAULT_SOURCE
    explicit = os.environ.get("KORU_VDISPLAY_SOURCE", "").strip()
    canon = canonical_ide(ide)
    preferred = explicit or defaults.get(canon, "DP-1")
    if probe is None:
        probe = desktop_probe(ide=ide, source=preferred)
    names = set(probe.get("monitor_names") or [])

    if not explicit:
        surface_monitor = _surface_preferred_monitor(probe, canon=canon)
        if surface_monitor and surface_monitor in names:
            preferred = surface_monitor
            probe = {
                **probe,
                "source_from_ide_surface": surface_monitor,
                "ide_surface_best": probe.get("ide_surface_best"),
            }

    if explicit and explicit not in names and names:
        failed_probe = {
            **probe,
            "requested_source": explicit,
            "resolved_source": explicit,
            "source_available": False,
            "ok": False,
            "error": (
                f"requested monitor {explicit!r} not connected "
                f"(available: {sorted(names)})"
            ),
        }
        return explicit, failed_probe

    candidates = _monitor_candidate_order(
        explicit=explicit,
        preferred=preferred,
        probe=probe,
        names=names,
    )
    chosen = preferred
    for candidate in candidates:
        if candidate in names:
            chosen = candidate
            break
    return chosen, _finalize_resolved_probe(probe, preferred=preferred, chosen=chosen, names=names)


def format_wayland_vdisplay_operator_hint(*, ide: str) -> str:
    """Short operator hint for coru auto / bridge (monitor + screencast + prepare)."""
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
    else:
        mon = "set KORU_VDISPLAY_SOURCE to the monitor where the IDE window lives"
    port_note = ""
    try:
        from koru.integrations.vdisplay_agent_bootstrap import is_koru_dashboard_on_port

        if is_koru_dashboard_on_port(8765):
            port_note = " (koru dashboard uses :8765 — run vdisplay-agent on :8766)"
    except ImportError:
        pass
    return (
        f"Wayland vdisplay/photo-VQL: vdisplay-agent serve{port_note}; "
        "vdisplay agent preflight; "
        "vdisplay agent screencast start --force (choose All Screens/the IDE monitor); "
        "vdisplay agent screencast probe --via-agent --source <monitor>; "
        f"{mon}; koru autopilot prepare-vdisplay --ide {ide}; "
        "blind OS-injector is blocked unless KORU_ALLOW_BLIND_KEYBOARD_FALLBACK=1"
    )


__all__ = [
    "format_wayland_vdisplay_operator_hint",
    "map_capture_monitor_mismatch",
    "resolve_vdisplay_source_for_ide",
]
