"""Environment defaults for ``koru autonomous up`` and ``koru-autoloop.sh``.

Boolean parsing matches the shell helper ``is_true`` in
``scripts/koru-autoloop.sh`` (1/true/yes/y/on).

:data:`AUTOLOOP_ENV_DEFAULTS` documents default *string* values from the
shell script; the autonomous CLI may still use different argparse defaults
before env overrides are applied. The overrides themselves are declared in
one place — :data:`_AUTOLOOP_ENV_OVERRIDES` — so adding an autoloop env
knob is a single table row instead of assignments scattered across
per-domain functions.
"""

from __future__ import annotations

import argparse
import contextlib
import os
import sys
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Final

from koruide.ide import (
    canonical_autopilot_ide_id,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    supports_vscode_extension_plugin,
)

from koru.env_flags import parse_boolish

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


def _stripped(raw: str | None) -> str:
    return "" if raw is None else str(raw).strip()


def _env_ticket_sources(cli_value: str, environ: Mapping[str, str]) -> str:
    """``TICKET_SOURCES`` overrides ``--ticket-sources`` when set to a valid value."""
    raw = environ.get("TICKET_SOURCES")
    if raw is None or not str(raw).strip():
        return cli_value
    v = str(raw).strip().lower()
    if v in _VALID_TICKET_SOURCES:
        return v
    print(
        f"! unknown TICKET_SOURCES={raw!r} (expected: queue|scan|all), keeping CLI value {cli_value!r}",
        file=sys.stderr,
    )
    return cli_value


# A coercion reads the env mapping plus the current args value and returns the
# new value for one attribute; it never mutates args itself.
_EnvCoerce = Callable[[Mapping[str, str], argparse.Namespace], object]


@dataclass(frozen=True)
class _EnvOverride:
    """One ``args`` attribute override driven by an environment variable."""

    env: str
    dest: str
    coerce: _EnvCoerce
    # Skip when args lacks the attribute (optional operator extras).
    optional: bool = False


def _keep_flag(env: str, dest: str, *, optional: bool = False) -> _EnvOverride:
    """Env truth value wins; otherwise keep the current value."""

    def coerce(environ: Mapping[str, str], args: argparse.Namespace) -> bool:
        return parse_boolish(environ.get(env), default=getattr(args, dest))

    return _EnvOverride(env, dest, coerce, optional)


def _keep_value(env: str, dest: str, *, optional: bool = False) -> _EnvOverride:
    """Non-blank stripped env value wins; otherwise keep the current value."""

    def coerce(environ: Mapping[str, str], args: argparse.Namespace) -> object:
        return _stripped(environ.get(env)) or getattr(args, dest)

    return _EnvOverride(env, dest, coerce, optional)


def _lower_choice(
    env: str,
    dest: str,
    choices: frozenset[str],
    fallback: str,
) -> _EnvOverride:
    """Lowercased env/current value must be one of *choices*; else *fallback*."""

    def coerce(environ: Mapping[str, str], args: argparse.Namespace) -> object:
        raw = _stripped(environ.get(env)) or getattr(args, dest)
        value = str(raw).lower() if raw else raw
        return value if value in choices else fallback

    return _EnvOverride(env, dest, coerce)


def _keep_number(
    env: str,
    dest: str,
    convert: Callable[[str], float],
    minimum: float,
) -> _EnvOverride:
    """Numeric env value clamped to *minimum*; missing/unparseable keeps current."""

    def coerce(environ: Mapping[str, str], args: argparse.Namespace) -> object:
        raw = _stripped(environ.get(env))
        if not raw:
            return getattr(args, dest)
        with contextlib.suppress(ValueError):
            return max(minimum, convert(raw))
        return getattr(args, dest)

    return _EnvOverride(env, dest, coerce)


def _coerce_ticket_sources(environ: Mapping[str, str], args: argparse.Namespace) -> str:
    return _env_ticket_sources(args.ticket_sources, environ)


def _coerce_idle_diagnostics(environ: Mapping[str, str], args: argparse.Namespace) -> object:
    fallback = args.idle_diagnostics
    default = "full" if parse_boolish(environ.get("ENABLE_IDLE_DIAGNOSTICS"), default=False) else fallback
    return _stripped(environ.get("IDLE_DIAGNOSTICS_PROFILE")) or default or fallback


def _coerce_wup_watch(environ: Mapping[str, str], args: argparse.Namespace) -> object:
    raw = environ.get("WUP_WATCH")
    if raw is None:
        return args.wup_watch
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


_AUTOLOOP_ENV_OVERRIDES: Final[tuple[_EnvOverride, ...]] = (
    # ticket sources + diagnostics
    _EnvOverride("TICKET_SOURCES", "ticket_sources", _coerce_ticket_sources),
    _EnvOverride("IDLE_DIAGNOSTICS_PROFILE", "idle_diagnostics", _coerce_idle_diagnostics),
    _keep_flag("ENABLE_DIAGNOSTIC_TICKETS", "diagnostic_tickets"),
    _keep_value("DIAGNOSTIC_TICKET_QUEUE", "diagnostic_ticket_queue"),
    _keep_value("DIAGNOSTIC_TICKET_PRIORITY", "diagnostic_ticket_priority"),
    _keep_value("DIAG_STATE_DIR", "diagnostic_state_dir"),
    _keep_flag("STRICT_DIAGNOSTICS", "strict_diagnostics"),
    # autopilot
    _lower_choice("AUTOPILOT_ACTION", "autopilot_action", frozenset({"drive", "handoff", "off"}), "drive"),
    _keep_flag("AUTOPILOT_ON_IDLE_ONLY", "autopilot_on_idle_only"),
    _keep_flag("AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL", "autopilot_skip_on_diagnostics_fail"),
    _keep_value("AUTOPILOT_SKIP_STATUSES", "autopilot_skip_statuses"),
    _keep_number("AUTOPILOT_SKIP_DRIVE_IDLE_STREAK", "autopilot_skip_drive_idle_streak", int, 0),
    _keep_flag("BACKOFF_ON_STAGNATION", "backoff_on_stagnation"),
    # scan
    _keep_flag("SCAN_SKIP_IF_CLEAN", "scan_skip_if_clean"),
    _keep_flag("SCAN_AFTER_IDLE_QUEUE", "scan_after_idle_queue"),
    _keep_number("SCAN_AFTER_IDLE_MIN_INTERVAL_SECONDS", "scan_after_idle_min_interval", float, 0.0),
    _keep_flag("TOPOLOGY_INTEGRATION", "topology_integration"),
    # wup
    _EnvOverride("WUP_WATCH", "wup_watch", _coerce_wup_watch),
    _lower_choice("WUP_MODE", "wup_mode", frozenset({"default", "testql"}), "testql"),
    _keep_value("WUP_DEPS", "wup_deps"),
    _keep_value("WUP_SCENARIOS_DIR", "wup_scenarios_dir"),
    _keep_value("WUP_TESTQL_BIN", "wup_testql_bin"),
    _keep_value("WUP_TRACK_DIR", "wup_track_dir"),
    _keep_flag("WUP_DIAGNOSTIC_TICKETS", "wup_diagnostic_tickets"),
    _keep_value("WUP_TICKET_QUEUE", "wup_ticket_queue"),
    # operator (args may lack these extras)
    _keep_flag("KORU_OPERATOR_PIPELINE", "operator_pipeline", optional=True),
    _keep_flag("KORU_OPERATOR_TICKETS", "operator_tickets", optional=True),
    _keep_value("OPERATOR_TICKET_QUEUE", "operator_ticket_queue", optional=True),
    _keep_value("OPERATOR_TICKET_PRIORITY", "operator_ticket_priority", optional=True),
)


def apply_autoloop_env_to_args(
    args: argparse.Namespace,
    *,
    environ: Mapping[str, str] | None = None,
) -> None:
    """Mutate ``args`` with environment defaults (shell-autoloop parity).

    This is the only place that writes ``args`` attributes: every override is
    declared in :data:`_AUTOLOOP_ENV_OVERRIDES` and applied here in one loop.
    """
    env = os.environ if environ is None else environ
    for override in _AUTOLOOP_ENV_OVERRIDES:
        if override.optional and not hasattr(args, override.dest):
            continue
        setattr(args, override.dest, override.coerce(env, args))


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
    # Determine if plugin is required by checking IDE's native autopilot capabilities.
    # Only consider explicit user overrides (keyboard, gillm fallback),
    # not optional fallbacks like vdisplay which may or may not be available.
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
