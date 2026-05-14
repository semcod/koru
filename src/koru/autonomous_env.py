"""Environment-driven defaults for ``koru autonomous up``.

Centralizes autodetection of CLI overrides from process environment so
``autonomous.py`` stays focused on the control loop. Parity with
``scripts/koru-autoloop.sh`` for ``TICKET_SOURCES`` / WUP / diagnostics flags.
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path
from typing import Final

_VALID_TICKET_SOURCES: Final[frozenset[str]] = frozenset({"queue", "scan", "all"})


def _env_default_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in {"1", "true", "yes", "y", "on"}


def effective_ticket_source_flags(ticket_sources: str) -> tuple[bool, bool]:
    """Return ``(enable_scan, use_all_queues)`` for a ticket-sources mode."""
    if ticket_sources == "queue":
        return False, False
    if ticket_sources == "scan":
        return True, False
    return True, True


def _env_ticket_sources(cli_value: str) -> str:
    """``TICKET_SOURCES`` overrides ``--ticket-sources`` when set to a valid value."""
    raw = os.environ.get("TICKET_SOURCES")
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


def apply_autonomous_env_overrides(args: argparse.Namespace) -> None:
    """Mutate ``args`` with environment defaults (shell-autoloop parity)."""
    args.ticket_sources = _env_ticket_sources(args.ticket_sources)
    args.idle_diagnostics = os.environ.get(
        "IDLE_DIAGNOSTICS_PROFILE",
        "full" if _env_default_bool("ENABLE_IDLE_DIAGNOSTICS", False) else args.idle_diagnostics,
    )
    args.diagnostic_tickets = _env_default_bool(
        "ENABLE_DIAGNOSTIC_TICKETS", args.diagnostic_tickets
    )
    args.diagnostic_ticket_queue = os.environ.get(
        "DIAGNOSTIC_TICKET_QUEUE", args.diagnostic_ticket_queue
    )
    args.diagnostic_ticket_priority = os.environ.get(
        "DIAGNOSTIC_TICKET_PRIORITY", args.diagnostic_ticket_priority
    )
    args.diagnostic_state_dir = os.environ.get("DIAG_STATE_DIR", args.diagnostic_state_dir)
    args.strict_diagnostics = _env_default_bool("STRICT_DIAGNOSTICS", args.strict_diagnostics)
    args.autopilot_action = os.environ.get("AUTOPILOT_ACTION", args.autopilot_action).lower()
    if args.autopilot_action not in {"drive", "handoff", "off"}:
        args.autopilot_action = "drive"
    args.autopilot_on_idle_only = _env_default_bool(
        "AUTOPILOT_ON_IDLE_ONLY", args.autopilot_on_idle_only
    )
    args.autopilot_skip_on_diagnostics_fail = _env_default_bool(
        "AUTOPILOT_SKIP_ON_DIAGNOSTICS_FAIL", args.autopilot_skip_on_diagnostics_fail
    )
    args.autopilot_skip_statuses = os.environ.get(
        "AUTOPILOT_SKIP_STATUSES", args.autopilot_skip_statuses
    )
    args.backoff_on_stagnation = _env_default_bool(
        "BACKOFF_ON_STAGNATION", args.backoff_on_stagnation
    )
    args.scan_skip_if_clean = _env_default_bool("SCAN_SKIP_IF_CLEAN", args.scan_skip_if_clean)
    args.topology_integration = _env_default_bool("TOPOLOGY_INTEGRATION", args.topology_integration)
    env_wup_watch = os.environ.get("WUP_WATCH")
    if env_wup_watch is not None:
        args.wup_watch = env_wup_watch.strip().lower() in {"1", "true", "yes", "y", "on"}
    elif args.wup_watch is None:
        args.wup_watch = None
    args.wup_mode = os.environ.get("WUP_MODE", args.wup_mode).lower()
    if args.wup_mode not in {"default", "testql"}:
        args.wup_mode = "testql"
    args.wup_deps = os.environ.get("WUP_DEPS", args.wup_deps)
    args.wup_scenarios_dir = os.environ.get("WUP_SCENARIOS_DIR", args.wup_scenarios_dir)
    args.wup_testql_bin = os.environ.get("WUP_TESTQL_BIN", args.wup_testql_bin)
    args.wup_track_dir = os.environ.get("WUP_TRACK_DIR", args.wup_track_dir)
    args.wup_diagnostic_tickets = _env_default_bool(
        "WUP_DIAGNOSTIC_TICKETS", args.wup_diagnostic_tickets
    )
    args.wup_ticket_queue = os.environ.get("WUP_TICKET_QUEUE", args.wup_ticket_queue)


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
    if _env_default_bool("ENABLE_IDLE_DIAGNOSTICS", False):
        bits.append("ENABLE_IDLE_DIAGNOSTICS=true")
    idp = os.environ.get("IDLE_DIAGNOSTICS_PROFILE")
    if idp and str(idp).strip():
        bits.append(f"IDLE_DIAGNOSTICS_PROFILE={str(idp).strip()}")
    wm = os.environ.get("WUP_MODE")
    if wm and str(wm).strip():
        bits.append(f"WUP_MODE={str(wm).strip()}")
    if _env_default_bool("ENABLE_DIAGNOSTIC_TICKETS", False):
        bits.append("ENABLE_DIAGNOSTIC_TICKETS=true")
    return "pass", "; ".join(bits)
