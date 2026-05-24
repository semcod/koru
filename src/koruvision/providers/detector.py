"""Rank capture providers and run fallbacks."""

from __future__ import annotations

import re
import subprocess
import sys
from typing import Any

from koruvision.providers.base import CaptureProvider, MonitorSpec
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
        proc = subprocess.run(
            ["xrandr", "--query"],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if proc.returncode != 0:
        return []
    monitors: list[MonitorSpec] = []
    index = 0
    for line in (proc.stdout or "").splitlines():
        match = re.match(
            r"^(\S+)\s+connected(?:\s+primary)?\s+(\d+)x(\d+)\+(\d+)\+(\d+)",
            line,
        )
        if not match:
            continue
        name, width, height, left, top = match.groups()
        monitors.append(
            MonitorSpec(
                id=index,
                output=name,
                width=int(width),
                height=int(height),
                left=int(left),
                top=int(top),
                is_primary="primary" in line,
            )
        )
        index += 1
    return monitors


def _forced_provider_rank(pref: str) -> list[CaptureProvider] | None:
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


def _available_ranked_providers(ordered_names: list[str]) -> list[CaptureProvider]:
    seen: set[str] = set()
    ranked: list[CaptureProvider] = []
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


def rank_providers() -> list[CaptureProvider]:
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
    from koruvision.scaling import resolve_scale

    scale_value = resolve_scale(scale)
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
        row["frame_count"] = len(frames)
        row["bytes"] = sum(len(item.get("payload") or b"") for item in frames)
        first = frames[0]
        row["width"] = first.get("width")
        row["height"] = first.get("height")
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


def _provider_label(provider: CaptureProvider) -> str:
    return "portal" if provider.name == "portal_screenshot" else provider.name


def _should_report_auto_portal(provider: CaptureProvider, index: int) -> bool:
    return (
        index == 0
        and provider.name == "portal_screenshot"
        and capture_provider_pref() == "auto"
        and is_wayland()
    )


def _stamp_provider(frame: dict[str, Any], provider_name: str) -> dict[str, Any]:
    stamped = dict(frame)
    stamped["provider"] = provider_name
    return stamped


def capture_one_with_providers(monitor_id: int | None, scale: float) -> dict[str, Any]:
    providers = rank_providers()
    if not providers:
        raise RuntimeError(_auto_failure_message(["no providers available"]))
    errors: list[str] = []
    for index, provider in enumerate(providers):
        try:
            frame = provider.capture_one(monitor_id, scale)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{provider.name}: {exc}")
            continue
        if index > 0:
            print(
                f"koru vision: {errors[0]} — used {_provider_label(provider)} capture",
                file=sys.stderr,
            )
        elif _should_report_auto_portal(provider, index):
            print(
                "koru vision: auto selected Wayland portal — used portal capture",
                file=sys.stderr,
            )
        return _stamp_provider(frame, provider.name)
    raise RuntimeError(_auto_failure_message(errors))


def capture_all_with_providers(scale: float) -> list[dict[str, Any]]:
    providers = rank_providers()
    if not providers:
        raise RuntimeError(_auto_failure_message(["no providers available"]))
    errors: list[str] = []
    for index, provider in enumerate(providers):
        try:
            frames = provider.capture_all(scale)
        except Exception as exc:  # noqa: BLE001
            errors.append(f"{provider.name}: {exc}")
            continue
        if not frames:
            errors.append(f"{provider.name}: no frames")
            continue
        if index > 0:
            print(
                f"koru vision: {errors[0]} — used {_provider_label(provider)} capture",
                file=sys.stderr,
            )
        elif _should_report_auto_portal(provider, index):
            print(
                "koru vision: auto selected Wayland portal — used portal capture",
                file=sys.stderr,
            )
        return [_stamp_provider(item, provider.name) for item in frames]
    raise RuntimeError(_auto_failure_message(errors))
