"""Rank capture providers and run fallbacks."""

from __future__ import annotations

import sys
from typing import Any

from vdisplay.capture import (
    MonitorSpec,
    ObservationProvider,
    ObservationProviderChainError,
    ScreenObservation,
    capture_observations_with_fallback,
    coerce_screen_observation,
    resolve_capture_scale,
)
from vdisplay.discovery import list_outputs as discover_monitors

from koruvision.providers.env import (
    capture_provider_pref,
    compositor_hint,
    env_truthy,
    is_wayland,
    looks_headless,
    portal_possible,
)
from koruvision.providers.registry import all_providers, provider_by_name

_LEGACY_MAP = {
    "mss": "mss",
    "portal": "portal_screenshot",
    "command": "cli_tools",
    "native": "cli_tools",
    "desktop": "cli_tools",
    "portal_screencast": "portal_screencast",
    "screencast": "portal_screencast",
    "obs": "obs_websocket",
    "obs_websocket": "obs_websocket",
    "browser": "browser_getdisplay",
    "browser_getdisplay": "browser_getdisplay",
}


def monitors_via_xrandr() -> list[MonitorSpec]:
    try:
        rows = discover_monitors(enrich_nl=False)
    except Exception:  # noqa: BLE001 - monitor discovery is advisory.
        return []
    monitors: list[MonitorSpec] = []
    for fallback_index, row in enumerate(rows):
        if not row.get("connected", True):
            continue
        monitor_index = row.get("monitor_index")
        monitors.append(
            MonitorSpec(
                id=fallback_index if monitor_index is None else int(monitor_index),
                output=str(row.get("name") or f"monitor-{fallback_index}"),
                width=int(row.get("width") or 0),
                height=int(row.get("height") or 0),
                left=int(row.get("x") or 0),
                top=int(row.get("y") or 0),
                is_primary=bool(row.get("primary")),
            )
        )
    return monitors


def _forced_provider_rank(pref: str) -> list[ObservationProvider] | None:
    if pref == "auto":
        return None
    forced = _LEGACY_MAP.get(pref, pref)
    provider = provider_by_name(forced)
    if provider is None:
        raise ValueError(f"unknown KORU_VISION_PROVIDER: {pref}")
    return [provider]


def _auto_provider_order() -> list[str]:
    ordered_names: list[str] = []
    from koruvision.providers.browser_getdisplay import browser_capture_requested
    from koruvision.providers.obs_websocket import probe_obs_reachable

    if browser_capture_requested():
        ordered_names.append("browser_getdisplay")
    if probe_obs_reachable():
        ordered_names.append("obs_websocket")
    if is_wayland() and portal_possible():
        ordered_names.append("portal_screencast")
    if env_truthy("KORU_VISION_PREFER_PORTAL") and portal_possible():
        ordered_names.append("portal_screenshot")
    ordered_names.append("mss")
    if portal_possible():
        ordered_names.append("portal_screenshot")
    if compositor_hint() == "wlroots" or (is_wayland() and compositor_hint() != "gnome"):
        ordered_names.append("grim")
    ordered_names.append("cli_tools")
    return ordered_names


def _available_ranked_providers(ordered_names: list[str]) -> list[ObservationProvider]:
    seen: set[str] = set()
    ranked: list[ObservationProvider] = []
    for name in ordered_names:
        if name in seen:
            continue
        seen.add(name)
        provider = provider_by_name(name)
        if provider is None:
            continue
        if provider.availability().available:
            ranked.append(provider)
    return ranked


def rank_providers() -> list[ObservationProvider]:
    pref = capture_provider_pref()
    forced = _forced_provider_rank(pref)
    if forced is not None:
        return forced

    return _available_ranked_providers(_auto_provider_order())


def list_provider_status() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for provider in all_providers():
        avail = provider.availability()
        rows.append(
            {
                "name": provider.name,
                "streams": provider.streams,
                "available": avail.available,
                "reason": avail.reason,
                "install_hint": avail.install_hint,
                "needs_consent": avail.needs_consent,
            }
        )
    return rows


def provider_diagnostics_rows() -> tuple[list[str], list[dict[str, Any]]]:
    """Return ``(ranked_names, rows)`` with ``selected`` and ``rank`` fields set."""
    ranked = rank_providers()
    ranked_names = [provider.name for provider in ranked]
    selected = set(ranked_names)
    rows: list[dict[str, Any]] = []
    for row in list_provider_status():
        name = str(row["name"])
        enriched = dict(row)
        enriched["selected"] = name in selected
        enriched["rank"] = ranked_names.index(name) + 1 if name in selected else None
        rows.append(enriched)
    return ranked_names, rows


def probe_capture_providers(
    name: str | None = None,
    *,
    scale: float = 0.2,
) -> list[dict[str, Any]]:
    """Try capturing with one or all providers; never raises (results per provider)."""
    scale_value = resolve_capture_scale(scale, env_var="KORU_VISION_SCALE")
    if name:
        provider = provider_by_name(name.strip().lower())
        if provider is None:
            return [
                {
                    "name": name,
                    "ok": False,
                    "error": f"unknown provider {name!r}",
                    "available": False,
                }
            ]
        candidates = [provider]
    else:
        candidates = list(all_providers())

    results: list[dict[str, Any]] = []
    for provider in candidates:
        avail = provider.availability()
        row: dict[str, Any] = {
            "name": provider.name,
            "available": avail.available,
            "reason": avail.reason,
            "ok": False,
        }
        if not avail.available:
            row["error"] = avail.reason or "not available"
            results.append(row)
            continue
        try:
            frames = provider.capture_all(scale_value)
        except Exception as exc:  # noqa: BLE001
            row["error"] = str(exc)[:500]
            results.append(row)
            continue
        if not frames:
            row["error"] = "no frames"
            results.append(row)
            continue
        row["ok"] = True
        observations = [coerce_screen_observation(item) for item in frames]
        row["frame_count"] = len(observations)
        row["bytes"] = sum(len(item.payload) for item in observations)
        first = observations[0]
        row["width"] = first.width
        row["height"] = first.height
        results.append(row)
    return results


def _auto_failure_message(errors: list[str]) -> str:
    msg = "no screenshot backend succeeded"
    if looks_headless():
        msg += (
            "; this looks headless because DISPLAY, WAYLAND_DISPLAY, and "
            "DBUS_SESSION_BUS_ADDRESS are unset"
        )
    if errors:
        msg += "; " + "; ".join(errors)
    msg += (
        ". Try KORU_VISION_PROVIDER=portal_screencast on Wayland (one-time screen share), "
        "KORU_VISION_PROVIDER=portal for portal screenshot, "
        "KORU_VISION_PROVIDER=cli_tools when a desktop screenshot tool is installed, "
        "or run koru observe from the graphical session."
    )
    return msg


def _provider_label(provider: ObservationProvider) -> str:
    return "portal" if provider.name == "portal_screenshot" else provider.name


def _should_report_auto_portal(provider: ObservationProvider, index: int) -> bool:
    return (
        index == 0
        and provider.name == "portal_screenshot"
        and capture_provider_pref() == "auto"
        and is_wayland()
    )


def capture_one_with_providers(
    monitor_id: int | None,
    scale: float,
) -> ScreenObservation:
    providers = rank_providers()
    if not providers:
        raise RuntimeError(_auto_failure_message(["no providers available"]))
    try:
        batch = capture_observations_with_fallback(
            providers,
            scale=scale,
            monitor_id=monitor_id,
        )
    except ObservationProviderChainError as exc:
        errors = [f"{item.provider}: {item.error}" for item in exc.failures]
        raise RuntimeError(_auto_failure_message(errors)) from exc
    provider = next(item for item in providers if item.name == batch.provider)
    if batch.failures:
        first = batch.failures[0]
        print(
            f"koru vision: {first.provider}: {first.error} — "
            f"used {_provider_label(provider)} capture",
            file=sys.stderr,
        )
    elif _should_report_auto_portal(provider, 0):
        print(
            "koru vision: auto selected Wayland portal — used portal capture",
            file=sys.stderr,
        )
    return batch.observations[0]


def capture_all_with_providers(scale: float) -> list[ScreenObservation]:
    providers = rank_providers()
    if not providers:
        raise RuntimeError(_auto_failure_message(["no providers available"]))
    try:
        batch = capture_observations_with_fallback(
            providers,
            scale=scale,
            all_monitors=True,
        )
    except ObservationProviderChainError as exc:
        errors = [f"{item.provider}: {item.error}" for item in exc.failures]
        raise RuntimeError(_auto_failure_message(errors)) from exc
    provider = next(item for item in providers if item.name == batch.provider)
    if batch.failures:
        first = batch.failures[0]
        print(
            f"koru vision: {first.provider}: {first.error} — "
            f"used {_provider_label(provider)} capture",
            file=sys.stderr,
        )
    elif _should_report_auto_portal(provider, 0):
        print(
            "koru vision: auto selected Wayland portal — used portal capture",
            file=sys.stderr,
        )
    return list(batch.observations)
