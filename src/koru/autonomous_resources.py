"""Resource bootstrap helpers for ``koru autonomous``."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from koru import autonomous_cycle_config as _autonomous_cycle_config
from koru.autonomous_auto_pipeline import AutoPipelineState
from koru.autonomous_checkpoint import load_loop_checkpoint
from koru.autonomous_cycle import AutoloopState
from koru.autonomous_cycle_gate import apply_agent_lane_environ
from koru.autonomous_env import effective_ticket_source_flags
from koru.autonomous_startup import resolve_autopilot_ide_for_autonomous
from koru.autonomous_wup import _build_wup_watch_config, _start_wup_watch
from koru.ide_router import resolve_ide_route


def setup_autonomous_resources(
    args: Any,
    project: Path,
    *,
    enable_strict_plugin_policy: Any,
    setup_autopilot_daemon: Any,
    load_checkpoint: Any = load_loop_checkpoint,
) -> tuple[
    object,
    object,
    object | None,
    Path,
    bool,
    bool,
    str | None,
    object,
    Path,
    int | None,
    Path,
    object | None,
    AutoPipelineState | None,
]:
    """Set up resources needed before the autonomous loop starts."""
    enable_strict_plugin_policy(args)
    client, daemon, thread, socket_path = setup_autopilot_daemon(args, project)
    autopilot_socket_observed_at_boot = (
        bool(socket_path and socket_path.exists()) if args.enable_autopilot else False
    )

    enable_scan, queue_name, autopilot_ide, loop_state, checkpoint_path, restored_cycle = (
        _autonomous_cycle_config.configure_loop_state(
            args,
            project,
            effective_flags=effective_ticket_source_flags,
            apply_agent_lane_environ=apply_agent_lane_environ,
            resolve_autopilot_ide=resolve_autopilot_ide_for_autonomous,
            resolve_ide_route_fn=resolve_ide_route,
            state_factory=AutoloopState,
            load_checkpoint=load_checkpoint,
        )
    )

    diagnostic_state_dir = (project / args.diagnostic_state_dir).resolve()
    wup_config = _build_wup_watch_config(args, project)
    wup_process = _start_wup_watch(
        wup_config,
        topology_integration=args.topology_integration,
        stdio_format=args.emit_events,
    )
    auto_pipeline_state = (
        AutoPipelineState() if getattr(args, "_auto_pipeline_enabled", False) else None
    )

    return (
        client,
        daemon,
        thread,
        socket_path,
        autopilot_socket_observed_at_boot,
        enable_scan,
        queue_name,
        autopilot_ide,
        loop_state,
        checkpoint_path,
        restored_cycle,
        diagnostic_state_dir,
        wup_process,
        auto_pipeline_state,
    )


__all__ = ["setup_autonomous_resources"]