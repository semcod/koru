"""Autonomous ``up`` orchestration.

This module owns the high-level lifecycle for ``koru autonomous up``:
prepare resources, run pre-checks, iterate cycles, and clean up. The
top-level ``koru.autonomous`` module stays as the public compatibility
facade and passes its monkeypatchable callables in here.
"""

from __future__ import annotations

import argparse
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any


@dataclass
class StopSignalState:
    stopped_by_sigterm: bool = False


@dataclass
class AutonomousUpContext:
    args: argparse.Namespace
    previous_stdio_format_env: str | None
    strict_env: str | None
    correlation_id: str
    project: Path
    startup_probe: object
    client: Any
    daemon: Any
    thread: Any
    socket_path: Path | None
    autopilot_socket_observed_at_boot: bool
    enable_scan: bool
    queue_name: str | None
    autopilot_ide: str
    loop_state: Any
    checkpoint_path: Path | None
    restored_cycle: int | None
    diagnostic_state_dir: Path | None
    wup_process: Any
    auto_pipeline_state: Any


def autonomous_context_resource_kwargs(resources: tuple[object, ...]) -> dict[str, object]:
    (
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
    ) = resources
    return {
        "client": client,
        "daemon": daemon,
        "thread": thread,
        "socket_path": socket_path,
        "autopilot_socket_observed_at_boot": autopilot_socket_observed_at_boot,
        "enable_scan": enable_scan,
        "queue_name": queue_name,
        "autopilot_ide": autopilot_ide,
        "loop_state": loop_state,
        "checkpoint_path": checkpoint_path,
        "restored_cycle": restored_cycle,
        "diagnostic_state_dir": diagnostic_state_dir,
        "wup_process": wup_process,
        "auto_pipeline_state": auto_pipeline_state,
    }


def prepare_autonomous_startup_probe(
    args: argparse.Namespace,
    project: Path,
    *,
    install_coauthor_hook: Callable[..., Any],
    build_and_log_startup_probe: Callable[[argparse.Namespace, Path], object],
    stdio_info: Callable[..., None],
) -> object:
    install_coauthor_hook(
        project,
        stdio_info=stdio_info,
        stdio_format=args.emit_events,
    )
    return build_and_log_startup_probe(args, project)


def prepare_autonomous_up_context(
    args: argparse.Namespace,
    *,
    setup_env_vars: Callable[[], tuple[str | None, dict[str, tuple[bool, str | None]]]],
    setup_session: Callable[[argparse.Namespace], tuple[str, Path, int]],
    prepare_startup_probe: Callable[[argparse.Namespace, Path], object],
    setup_resources: Callable[..., tuple[object, ...]],
    enable_strict_plugin_policy: Callable[[argparse.Namespace], None],
    setup_autopilot_daemon: Callable[..., Any],
    load_checkpoint: Callable[..., Any],
) -> tuple[AutonomousUpContext | None, int]:
    previous_stdio_format_env, strict_env = setup_env_vars()
    correlation_id, project, guard_rc = setup_session(args)
    if guard_rc:
        return None, guard_rc

    startup_probe = prepare_startup_probe(args, project)
    resources = setup_resources(
        args,
        project,
        enable_strict_plugin_policy=enable_strict_plugin_policy,
        setup_autopilot_daemon=setup_autopilot_daemon,
        load_checkpoint=load_checkpoint,
    )
    context_kwargs = autonomous_context_resource_kwargs(resources)
    return AutonomousUpContext(
        args=args,
        previous_stdio_format_env=previous_stdio_format_env,
        strict_env=strict_env,
        correlation_id=correlation_id,
        project=project,
        startup_probe=startup_probe,
        **context_kwargs,
    ), 0


def run_autonomous_up_loop(
    context: AutonomousUpContext,
    *,
    install_sigterm_handler: Callable[[argparse.Namespace, StopSignalState], Any],
    run_pre_checks: Callable[..., tuple[bool, bool]],
    run_autonomous_cycle: Callable[..., bool],
    handle_interrupt: Callable[..., int],
    restore_env_vars: Callable[[dict[str, tuple[bool, str | None]]], None],
    cleanup_session: Callable[..., None],
) -> int:
    stop_state = StopSignalState()
    previous_sigterm = install_sigterm_handler(context.args, stop_state)
    try:
        run_pre_checks(
            context.args,
            context.project,
            context.startup_probe,
            context.socket_path,
            context.autopilot_ide,
            context.client,
            context.correlation_id,
        )

        cycle = context.restored_cycle or 0
        while True:
            cycle += 1
            should_exit = run_autonomous_cycle(
                cycle=cycle,
                args=context.args,
                project=context.project,
                client=context.client,
                daemon=context.daemon,
                thread=context.thread,
                socket_path=context.socket_path,
                autopilot_socket_observed_at_boot=context.autopilot_socket_observed_at_boot,
                queue_name=context.queue_name,
                enable_scan=context.enable_scan,
                autopilot_ide=context.autopilot_ide,
                loop_state=context.loop_state,
                checkpoint_path=context.checkpoint_path,
                diagnostic_state_dir=context.diagnostic_state_dir,
                wup_process=context.wup_process,
                correlation_id=context.correlation_id,
                auto_pipeline_state=context.auto_pipeline_state,
            )
            if should_exit:
                return 0
    except KeyboardInterrupt:
        return handle_interrupt(
            context.args,
            correlation_id=context.correlation_id,
            stopped_by_sigterm=stop_state.stopped_by_sigterm,
        )
    finally:
        restore_env_vars(context.strict_env)
        cleanup_session(
            context.previous_stdio_format_env,
            previous_sigterm,
            context.daemon,
            context.thread,
            context.wup_process,
            context.args.emit_events,
        )


def action_up(
    args: argparse.Namespace,
    *,
    maybe_run_interactive_onboarding: Callable[[argparse.Namespace], object | None],
    prepare_up_context: Callable[[argparse.Namespace], tuple[AutonomousUpContext | None, int]],
    run_up_loop: Callable[[AutonomousUpContext], int],
    stdio_info: Callable[..., None],
) -> int:
    try:
        maybe_run_interactive_onboarding(args)
    except KeyboardInterrupt:
        stdio_info("\nkoru auto onboarding: interrupted", fmt=args.emit_events)
        return 130
    context, rc = prepare_up_context(args)
    if context is None:
        return rc
    return run_up_loop(context)


__all__ = [
    "AutonomousUpContext",
    "StopSignalState",
    "action_up",
    "autonomous_context_resource_kwargs",
    "prepare_autonomous_startup_probe",
    "prepare_autonomous_up_context",
    "run_autonomous_up_loop",
]
