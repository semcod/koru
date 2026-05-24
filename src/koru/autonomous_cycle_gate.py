"""Cycle gating and lane-selection helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from koru.agents import agent_lane_environment
from koru.autonomous_startup import resolve_agent_lane_id
from koru.ide_router import resolve_ide_route
from koru.init import resolve_project_agent_lane
from koruide.os_injector import OsInjectorError, inject_with_profile, load_profile


def try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    """Best-effort global fallback via coordinate profile.

    Enabled only when ``KORU_OS_INJECTOR_PROFILE`` is set.
    """
    profile_id = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile_id:
        return None
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    try:
        profile = load_profile(profile_id, config_path=cfg)
        return inject_with_profile(profile=profile, text=prompt, submit=submit, dry_run=False)
    except OsInjectorError as exc:
        return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


def try_os_injector_fallback_with_deps(
    prompt: str,
    *,
    submit: bool,
    load_profile_fn: Any,
    inject_with_profile_fn: Any,
    os_injector_error: type[Exception],
) -> dict[str, Any] | None:
    """Best-effort OS injector fallback with injectable callables for tests."""
    profile_id = os.environ.get("KORU_OS_INJECTOR_PROFILE", "").strip()
    if not profile_id:
        return None
    raw_cfg = os.environ.get("KORU_OS_INJECTOR_CONFIG", "").strip()
    cfg = Path(raw_cfg).expanduser().resolve() if raw_cfg else None
    try:
        profile = load_profile_fn(profile_id, config_path=cfg)
        return inject_with_profile_fn(profile=profile, text=prompt, submit=submit, dry_run=False)
    except os_injector_error as exc:
        return {"ok": False, "backend": "os_injector", "message": str(exc), "type": "error"}


def allow_keyboard_autopilot_fallback() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def effective_cycle_autopilot_enabled(
    enabled: bool,
    *,
    client: object | None,
    autopilot_ide: str,
    stdio_format: str,
    plugin_required_for_ide: Any,
    status_has_autopilot_plugin: Any,
    stdio_info: Any,
) -> bool:
    if not enabled:
        return False
    if not plugin_required_for_ide(autopilot_ide):
        return True
    plugin_ready = False
    if client is not None:
        status_fn = getattr(client, "status", None)
        if callable(status_fn):
            try:
                plugin_ready = status_has_autopilot_plugin(status_fn(), autopilot_ide)
            except OSError:
                plugin_ready = False
    if plugin_ready:
        return True
    stdio_info(
        "koru autonomous: autopilot skipped this cycle; "
        f"ide={autopilot_ide} requires a compatible connected plugin",
        fmt=stdio_format,
    )
    return False


def scan_while_waiting_input_enabled() -> bool:
    raw = os.environ.get("KORU_AUTONOMOUS_SCAN_WHILE_WAITING", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def effective_cycle_scan_enabled(
    enabled: bool,
    *,
    state: object,
    stdio_format: str,
    stdio_info: Any,
) -> bool:
    if not enabled:
        return False
    if scan_while_waiting_input_enabled():
        return True
    signature = str(getattr(state, "previous_signature", "") or "")
    if signature.startswith("waiting_input:"):
        waiting_ticket = signature.split(":", 1)[1] or "-"
        stdio_info(
            "koru autonomous: scan skipped this cycle; "
            f"queue is waiting_input ({waiting_ticket})",
            fmt=stdio_format,
        )
        return False
    return True


def resolve_autopilot_ide(cli_value: str) -> str:
    """Resolve autopilot ``--ide`` via :mod:`koru.ide_router`."""
    return resolve_ide_route(cli_autopilot_ide=cli_value).autopilot_ide


def apply_agent_lane_environ(project: Path, agent_lane: str) -> str | None:
    """Set lane exports in ``os.environ``; returns lane id or ``None`` if skipped."""
    lane, _source = resolve_agent_lane_id(
        project,
        agent_lane,
        resolve_project_lane=resolve_project_agent_lane,
    )
    if lane is None:
        return None
    for key, val in agent_lane_environment(lane).items():
        os.environ[key] = val
    return lane


__all__ = [
    "allow_keyboard_autopilot_fallback",
    "apply_agent_lane_environ",
    "effective_cycle_autopilot_enabled",
    "effective_cycle_scan_enabled",
    "resolve_autopilot_ide",
    "scan_while_waiting_input_enabled",
    "try_os_injector_fallback",
    "try_os_injector_fallback_with_deps",
]
