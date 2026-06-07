"""Environment defaults for ``koru autonomous up`` and ``koru-autoloop.sh``.

Boolean parsing matches the shell helper ``is_true`` in
``scripts/koru-autoloop.sh`` (1/true/yes/y/on).

:data:`AUTOLOOP_ENV_DEFAULTS` documents default *string* values from the
shell script; the autonomous CLI may still use different argparse defaults
before env overrides are applied.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Final

from koru.env_flags import parse_boolish

from koruide.ide import (
    canonical_autopilot_ide_id,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    supports_vscode_extension_plugin,
)

_VALID_TICKET_SOURCES: Final[frozenset[str]] = frozenset({"queue", "scan", "all"})

# Mirrors scripts/koru-autoloop.sh initial "${VAR:-default}" (see script header).
AUTOLOOP_ENV_DEFAULTS: dict[str, str] = {
    "ENABLE_SCAN": "true",
    "TICKET_SOURCES": "queue",
    "ENABLE_INTERACTIVE": "false",
    "ENABLE_AUTOPILOT_DRIVE": "true",
    "AUTOPILOT_ACTION": "drive",
    "AUTOPILOT_IDE": "auto",
    "AUTOPILOT_SUBMIT": "true",
    "AUTOPILOT_ON_IDLE_ONLY": "false",
    "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL": "true",
    "AUTOPILOT_ENSURE_DAEMON": "true",
    "AUTOPILOT_SKIP_DRIVE_IDLE_STREAK": "0",
    "ENABLE_IDLE_DIAGNOSTICS": "false",
    "IDLE_DIAGNOSTICS_PROFILE": "quick",
    "STRICT_DIAGNOSTICS": "false",
    "ENABLE_DIAGNOSTIC_TICKETS": "false",
    "DIAGNOSTIC_TICKET_QUEUE": "default",
    "DIAGNOSTIC_TICKET_PRIORITY": "high",
    "REGIX_DIAGNOSTIC_CMD": "regix compare HEAD --local --format rich",
    "REDUP_DIAGNOSTIC_CMD": "python3 -m redup scan . --min-lines 10",
    "TESTQL_DIAGNOSTIC_CMD": "testql suite --pattern '*.testql.toon.yaml' --output console --fail-fast",
    "SCAN_AFTER_IDLE_QUEUE": "false",
    "SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS": "0",
    "TOPOLOGY_INTEGRATION": "true",
    "USE_ALL_QUEUES": "false",
    "MAX_ITERATIONS": "50",
    "MAX_CYCLES": "0",
    "SLEEP_SECONDS": "120",
    "INITIAL_DELAY_SECONDS": "0",
}


def env_truthy(name: str, default: bool, *, environ: Mapping[str, str] | None = None) -> bool:
    """Parse env *name* as boolean (same truth set as koru-autoloop ``is_true``)."""
    env = os.environ if environ is None else environ
    return parse_boolish(env.get(name), default=default)


def env_get(name: str, default: str | None, *, environ: Mapping[str, str] | None = None) -> str | None:
    """Return stripped env value or ``default`` when missing/blank."""
    env = os.environ if environ is None else environ
    raw = env.get(name)
    if raw is None or not str(raw).strip():
        return default
    return str(raw).strip()


def env_int(name: str, default: int, *, environ: Mapping[str, str] | None = None) -> int:
    """Return non-empty integer env value or ``default`` when invalid."""
    raw = env_get(name, None, environ=environ)
    if raw is None:
        return default
    with contextlib.suppress(ValueError):
        return int(raw)
    return default


def effective_ticket_source_flags(ticket_sources: str) -> tuple[bool, bool]:
    """Return ``(enable_scan, use_all_queues)`` for a ticket-sources mode."""
    if ticket_sources == "queue":
        return False, False
    if ticket_sources == "scan":
        return True, False
    return True, True


def _env_ticket_sources(cli_value: str, environ: Mapping[str, str] | None) -> str:
    """``TICKET_SOURCES`` overrides ``--ticket-sources`` when set to a valid value."""
    env = os.environ if environ is None else environ
    raw = env.get("TICKET_SOURCES")
    if raw is None or not str(raw).strip():
        return cli_value
    v = str(raw).strip().lower()
    if v in _VALID_TICKET_SOURCES:
        return v
    print(
        f"! unknown TICKET_SOURCES={raw!r} (expected: queue|scan|all), "
        f"keeping CLI value {cli_value!r}",
        file=sys.stderr,
    )
    return cli_value


def _apply_ticket_and_diagnostics_env(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> None:
    """Apply ticket sources and diagnostics environment overrides."""
    args.ticket_sources = _env_ticket_sources(args.ticket_sources, environ)
    args.idle_diagnostics = (
        env_get(
            "IDLE_DIAGNOSTICS_PROFILE",
            "full"
            if env_truthy("ENABLE_IDLE_DIAGNOSTICS", False, environ=environ)
            else args.idle_diagnostics,
            environ=environ,
        )
        or args.idle_diagnostics
    )
    args.diagnostic_tickets = env_truthy(
        "ENABLE_DIAGNOSTIC_TICKETS",
        args.diagnostic_tickets,
        environ=environ,
    )
    args.diagnostic_ticket_queue = (
        env_get(
            "DIAGNOSTIC_TICKET_QUEUE",
            args.diagnostic_ticket_queue,
            environ=environ,
        )
        or args.diagnostic_ticket_queue
    )
    args.diagnostic_ticket_priority = (
        env_get(
            "DIAGNOSTIC_TICKET_PRIORITY",
            args.diagnostic_ticket_priority,
            environ=environ,
        )
        or args.diagnostic_ticket_priority
    )
    args.diagnostic_state_dir = (
        env_get("DIAG_STATE_DIR", args.diagnostic_state_dir, environ=environ) or args.diagnostic_state_dir
    )
    args.strict_diagnostics = env_truthy(
        "STRICT_DIAGNOSTICS", args.strict_diagnostics, environ=environ
    )


def _apply_autopilot_env(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> None:
    """Apply autopilot environment overrides."""
    ap_action = env_get("AUTOPILOT_ACTION", args.autopilot_action, environ=environ)
    args.autopilot_action = str(ap_action).lower() if ap_action else args.autopilot_action
    if args.autopilot_action not in {"drive", "handoff", "off"}:
        args.autopilot_action = "drive"
    args.autopilot_on_idle_only = env_truthy(
        "AUTOPILOT_ON_IDLE_ONLY",
        args.autopilot_on_idle_only,
        environ=environ,
    )
    args.autopilot_skip_on_diagnostics_fail = env_truthy(
        "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL",
        args.autopilot_skip_on_diagnostics_fail,
        environ=environ,
    )
    args.autopilot_skip_statuses = (
        env_get(
            "AUTOPILOT_SKIP_STATUSES",
            args.autopilot_skip_statuses,
            environ=environ,
        )
        or args.autopilot_skip_statuses
    )
    _idle_streak_raw = env_get("AUTOPILOT_SKIP_DRIVE_IDLE_STREAK", None, environ=environ)
    if _idle_streak_raw is not None and str(_idle_streak_raw).strip():
        with contextlib.suppress(ValueError):
            args.autopilot_skip_drive_idle_streak = max(0, int(str(_idle_streak_raw).strip()))
    args.backoff_on_stagnation = env_truthy(
        "BACKOFF_ON_STAGNATION",
        args.backoff_on_stagnation,
        environ=environ,
    )


def _apply_scan_env(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> None:
    """Apply scan environment overrides."""
    args.scan_skip_if_clean = env_truthy(
        "SCAN_SKIP_IF_CLEAN", args.scan_skip_if_clean, environ=environ
    )
    args.scan_after_idle_queue = env_truthy(
        "SCAN_AFTER_IDLE_QUEUE",
        args.scan_after_idle_queue,
        environ=environ,
    )
    _idle_min_raw = env_get("SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS", None, environ=environ)
    if _idle_min_raw is not None and str(_idle_min_raw).strip():
        with contextlib.suppress(ValueError):
            args.scan_after_idle_min_interval = max(0.0, float(str(_idle_min_raw).strip()))
    args.topology_integration = env_truthy(
        "TOPOLOGY_INTEGRATION", args.topology_integration, environ=environ
    )


def _apply_wup_env(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> None:
    """Apply WUP environment overrides."""
    _emap = os.environ if environ is None else environ
    env_wup_watch = _emap.get("WUP_WATCH")
    if env_wup_watch is not None:
        args.wup_watch = str(env_wup_watch).strip().lower() in {"1", "true", "yes", "y", "on"}
    elif args.wup_watch is None:
        args.wup_watch = None
    wm = env_get("WUP_MODE", args.wup_mode, environ=environ)
    args.wup_mode = str(wm).lower() if wm else args.wup_mode
    if args.wup_mode not in {"default", "testql"}:
        args.wup_mode = "testql"
    args.wup_deps = env_get("WUP_DEPS", args.wup_deps, environ=environ) or args.wup_deps
    args.wup_scenarios_dir = (
        env_get("WUP_SCENARIOS_DIR", args.wup_scenarios_dir, environ=environ) or args.wup_scenarios_dir
    )
    args.wup_testql_bin = (
        env_get("WUP_TESTQL_BIN", args.wup_testql_bin, environ=environ) or args.wup_testql_bin
    )
    args.wup_track_dir = (
        env_get("WUP_TRACK_DIR", args.wup_track_dir, environ=environ) or args.wup_track_dir
    )
    args.wup_diagnostic_tickets = env_truthy(
        "WUP_DIAGNOSTIC_TICKETS",
        args.wup_diagnostic_tickets,
        environ=environ,
    )
    args.wup_ticket_queue = (
        env_get("WUP_TICKET_QUEUE", args.wup_ticket_queue, environ=environ) or args.wup_ticket_queue
    )


def _apply_operator_env(
    args: argparse.Namespace,
    environ: Mapping[str, str] | None,
) -> None:
    """Apply operator environment overrides."""
    if hasattr(args, "operator_pipeline"):
        args.operator_pipeline = env_truthy(
            "KORU_OPERATOR_PIPELINE",
            args.operator_pipeline,
            environ=environ,
        )
    if hasattr(args, "operator_tickets"):
        args.operator_tickets = env_truthy(
            "KORU_OPERATOR_TICKETS",
            args.operator_tickets,
            environ=environ,
        )
    if hasattr(args, "operator_ticket_queue"):
        args.operator_ticket_queue = (
            env_get("OPERATOR_TICKET_QUEUE", args.operator_ticket_queue, environ=environ)
            or args.operator_ticket_queue
        )
    if hasattr(args, "operator_ticket_priority"):
        args.operator_ticket_priority = (
            env_get("OPERATOR_TICKET_PRIORITY", args.operator_ticket_priority, environ=environ)
            or args.operator_ticket_priority
        )


def apply_autoloop_env_to_args(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Mutate ``args`` with environment defaults (shell-autoloop parity)."""
    _apply_ticket_and_diagnostics_env(args, environ)
    _apply_autopilot_env(args, environ)
    _apply_scan_env(args, environ)
    _apply_wup_env(args, environ)
    _apply_operator_env(args, environ)


def autonomous_environ_doctor_probe(project: Path) -> tuple[str, str]:
    """Return ``(status, detail)`` for ``koru --doctor``; process-global, no I/O."""
    del project
    raw = os.environ.get("TICKET_SOURCES")
    if raw is not None and str(raw).strip():
        v = str(raw).strip().lower()
        if v not in _VALID_TICKET_SOURCES:
            return "fail", f"invalid TICKET_SOURCES={raw!r} (use queue|scan|all)"
    bits: list[str] = []
    if raw is not None and str(raw).strip():
        bits.append(f"TICKET_SOURCES={str(raw).strip()}")
    else:
        bits.append("TICKET_SOURCES unset")
    if env_truthy("ENABLE_IDLE_DIAGNOSTICS", False):
        bits.append("ENABLE_IDLE_DIAGNOSTICS=true")
    idp = os.environ.get("IDLE_DIAGNOSTICS_PROFILE")
    if idp and str(idp).strip():
        bits.append(f"IDLE_DIAGNOSTICS_PROFILE={str(idp).strip()}")
    wm = os.environ.get("WUP_MODE")
    if wm and str(wm).strip():
        bits.append(f"WUP_MODE={str(wm).strip()}")
    if env_truthy("ENABLE_DIAGNOSTIC_TICKETS", False):
        bits.append("ENABLE_DIAGNOSTIC_TICKETS=true")
    return "pass", "; ".join(bits)


def allow_keyboard_autopilot_fallback() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_ALLOW_KEYBOARD_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def allow_gillm_autopilot_fallback() -> bool:
    """Opt-in Gillm GuiDriver fallback when the VSIX plugin drive fails."""
    raw = os.environ.get("KORU_AUTOPILOT_GILLM_FALLBACK", "").strip().lower()
    return raw in {"1", "true", "yes", "on"}


def prefer_keyboard_autopilot() -> bool:
    for key in ("KORU_AUTOPILOT_PREFER_KEYBOARD", "KORU_AUTOPILOT_VISIBLE_TYPING"):
        if os.environ.get(key, "").strip().lower() in {"1", "true", "yes", "on"}:
            return True
    return False


def keyboard_fallback_when_plugin_missing(autopilot_ide: str) -> bool:
    """Allow OS keyboard/injector drive when the VSIX plugin is not connected.

    Opt-in: ``KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN=1`` enables a Wayland-style
    blind paste via wtype/ydotool when the plugin does not connect. Default is
    OFF — once a real VSIX plugin is connected, blind OS-injector shots only
    cause chat clobbering and miswritten input (e.g. clicking the wrong
    monitor coordinates). The strict plugin path is preferred.
    """
    raw = os.environ.get("KORU_AUTOPILOT_KEYBOARD_IF_NO_PLUGIN", "0").strip().lower()
    if raw in {"1", "true", "yes", "on"}:
        ide = canonical_autopilot_ide_id(normalize_ide_id(autopilot_ide) or autopilot_ide)
        return supports_vscode_extension_plugin(ide) or ide == "jetbrains"
    return False


def plugin_required_for_ide(autopilot_ide: str) -> bool:
    ide = canonical_autopilot_ide_id(normalize_ide_id(autopilot_ide) or autopilot_ide)
    if ide != "auto" and not supports_vscode_extension_plugin(ide):
        return False
    if allow_keyboard_autopilot_fallback() or prefer_keyboard_autopilot():
        return False
    if allow_gillm_autopilot_fallback():
        return False
    if keyboard_fallback_when_plugin_missing(autopilot_ide):
        return False
    return True


def allow_cross_ide_autopilot() -> bool:
    return os.environ.get("KORU_AUTOPILOT_ALLOW_CROSS_IDE", "").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def autopilot_terminal_conflict_reason(
    autopilot_ide: str,
    *,
    plugin_connected: bool = False,
) -> str | None:
    if plugin_connected:
        return None
    if allow_cross_ide_autopilot():
        return None
    wanted = canonical_autopilot_ide_id(normalize_ide_id(autopilot_ide) or autopilot_ide)
    terminal = normalize_ide_id(detect_terminal_host_ide_id())
    if not wanted or wanted == "auto" or not terminal or terminal == wanted:
        return None
    if supports_vscode_extension_plugin(wanted) and supports_vscode_extension_plugin(terminal):
        return (
            f"terminal host is {terminal}, but autopilot target is {wanted}; "
            "refusing cross-IDE plugin drive. Restart `koru auto` from the target IDE "
            "terminal, or set KORU_AUTOPILOT_ALLOW_CROSS_IDE=1 explicitly."
        )
    return None
