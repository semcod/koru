"""Cycle-configuration helpers for ``koru autonomous``."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any


def configure_loop_state(
    args: Any,
    project: Path,
    *,
    effective_flags: Any,
    apply_agent_lane_environ: Any,
    resolve_autopilot_ide: Any,
    resolve_ide_route_fn: Any,
    state_factory: Any,
    load_checkpoint: Any,
) -> tuple[bool, str | None, str, Any, Path, int]:
    """Configure queue flags, autopilot IDE, and loop state."""
    enable_scan, use_all_queues = effective_flags(args.ticket_sources)
    queue_name = None if use_all_queues else args.queue_name
    # apply_agent_lane_environ is already called in build_and_log_startup_probe
    # so we can read the lane directly from the environment variable
    lane = os.environ.get("KORU_AUTOPILOT_INSTANCE") or apply_agent_lane_environ(
        project,
        args.agent_lane,
    )
    # If lane is explicit, use it directly as autopilot_ide to respect the user's choice.
    # This ensures non-plugin lanes like jetbrains are not overridden by the router
    if lane and lane != "auto":
        autopilot_ide = lane
        _autopilot_ide_source = f"lane:{lane}"
    else:
        autopilot_ide, _autopilot_ide_source = resolve_autopilot_ide(
            args.autopilot_ide,
            lane,
            resolve_ide_route_fn=resolve_ide_route_fn,
        )
    loop_state = state_factory()
    checkpoint_path = (project / ".planfile/.koru/autonomous-state.json").resolve()
    restored_cycle = load_checkpoint(
        checkpoint_path,
        state=loop_state,
        stdio_format=args.emit_events,
    )
    return enable_scan, queue_name, autopilot_ide, loop_state, checkpoint_path, restored_cycle


def select_and_log_cycle_profile(
    args: Any,
    auto_pipeline_state: Any | None,
    *,
    enable_scan: bool,
    select_profile: Any,
    stdio_info: Any,
) -> Any | None:
    """Select auto pipeline profile and log it if enabled."""
    if auto_pipeline_state is None:
        return None
    profile = select_profile(args, auto_pipeline_state, base_enable_scan=enable_scan)
    stdio_info(
        "koru auto: "
        f"pipeline={profile.name} reason={profile.reason}; "
        f"scan={'on' if profile.enable_scan else 'off'} "
        f"semcod={'on' if profile.include_semcod_artifacts else 'off'} "
        f"diagnostics={profile.idle_diagnostics} "
        f"max_iterations={profile.max_iterations} "
        f"autopilot={'on' if profile.enable_autopilot else 'off'}",
        fmt=args.emit_events,
    )
    return profile


def resolve_effective_cycle_flags(
    args: Any,
    profile: Any | None,
    *,
    enable_scan: bool,
    loop_state: Any,
    client: Any,
    autopilot_ide: str,
    effective_scan_enabled: Any,
    effective_autopilot_enabled: Any,
) -> tuple[bool, bool]:
    """Resolve effective scan and autopilot enable flags for the cycle."""
    requested_enable_scan = profile.enable_scan if profile is not None else enable_scan
    effective_enable_scan = effective_scan_enabled(
        requested_enable_scan,
        state=loop_state,
        stdio_format=args.emit_events,
    )
    requested_enable_autopilot = (
        profile.enable_autopilot if profile is not None else args.enable_autopilot
    )
    effective_enable_autopilot = effective_autopilot_enabled(
        requested_enable_autopilot,
        client=client,
        autopilot_ide=autopilot_ide,
        stdio_format=args.emit_events,
    )
    return effective_enable_scan, effective_enable_autopilot


def build_cycle_run_kwargs(
    args: Any,
    profile: Any | None,
    *,
    cycle: int,
    project: Path,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    client: Any,
    loop_state: Any,
    diagnostic_state_dir: Path,
    wup_process: Any | None,
    correlation_id: str,
) -> dict[str, Any]:
    """Build kwargs for the core cycle runner."""
    return {
        "cycle": cycle,
        "project": project,
        "actor": args.actor,
        "queue_name": queue_name,
        "enable_scan": enable_scan,
        "max_iterations": profile.max_iterations if profile is not None else args.max_iterations,
        "enable_autopilot": (
            profile.enable_autopilot if profile is not None else args.enable_autopilot
        ),
        "autopilot_ide": autopilot_ide,
        "drive_prompt": args.drive_prompt,
        "submit": args.submit,
        "include_semcod_artifacts": (
            profile.include_semcod_artifacts if profile is not None else args.semcod_artifacts
        ),
        "client": client,
        "state": loop_state,
        "idle_diagnostics": (
            profile.idle_diagnostics if profile is not None else args.idle_diagnostics
        ),
        "diagnostic_tickets": (
            profile.diagnostic_tickets if profile is not None else args.diagnostic_tickets
        ),
        "diagnostic_ticket_queue": args.diagnostic_ticket_queue,
        "diagnostic_ticket_priority": args.diagnostic_ticket_priority,
        "diagnostic_state_dir": diagnostic_state_dir,
        "wup_watch_enabled": wup_process is not None,
        "wup_diagnostic_tickets": args.wup_diagnostic_tickets,
        "wup_ticket_queue": args.wup_ticket_queue,
        "strict_diagnostics": args.strict_diagnostics,
        "autopilot_action": (
            profile.autopilot_action if profile is not None else args.autopilot_action
        ),
        "autopilot_on_idle_only": args.autopilot_on_idle_only,
        "autopilot_skip_on_diagnostics_fail": args.autopilot_skip_on_diagnostics_fail,
        "autopilot_skip_drive_idle_streak": args.autopilot_skip_drive_idle_streak,
        "autopilot_skip_statuses": args.autopilot_skip_statuses,
        "scan_skip_if_clean": args.scan_skip_if_clean,
        "scan_skip_after": args.scan_skip_after,
        "scan_after_idle_queue": (
            profile.scan_after_idle_queue if profile is not None else args.scan_after_idle_queue
        ),
        "scan_after_idle_min_interval_seconds": (
            profile.scan_after_idle_min_interval
            if profile is not None
            else args.scan_after_idle_min_interval
        ),
        "topology_integration": args.topology_integration,
        "stdio_format": args.emit_events,
        "correlation_id": correlation_id,
    }


def compute_cycle_sleep(
    args: Any,
    loop_state: Any,
    queue_result: Any,
    *,
    compute_backoff_sleep: Any,
    now: Any,
    autopilot_status: str = "",
) -> float:
    """Compute sleep duration for the cycle."""
    effective_sleep = compute_backoff_sleep(
        args.sleep_seconds,
        loop_state.stagnation_streak,
        args.max_sleep_seconds,
        args.backoff_on_stagnation,
    )
    if (
        queue_result.last_status == "idle"
        and loop_state.last_message_sent_ts > 0
        and now() - loop_state.last_message_sent_ts < 120.0
    ):
        effective_sleep = min(effective_sleep, 15.0)
    if _autopilot_needs_plugin_reconnect(autopilot_status):
        effective_sleep = min(effective_sleep, 15.0)
    return effective_sleep


def _autopilot_needs_plugin_reconnect(autopilot_status: str) -> bool:
    return autopilot_status in {
        "skipped(plugin_missing)",
        "skipped(plugin_not_connected)",
        "skipped(plugin_status_unavailable)",
        "skipped(plugin_version_mismatch)",
    }


__all__ = [
    "configure_loop_state",
    "select_and_log_cycle_profile",
    "resolve_effective_cycle_flags",
    "build_cycle_run_kwargs",
    "compute_cycle_sleep",
]
