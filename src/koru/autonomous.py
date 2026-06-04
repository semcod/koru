"""One-command autonomous mode for freshly installed koru.

`koru auto` and `koru autonomous up` (or bare `koru autonomous`) bootstrap
the project if needed, applies ``--agent-lane`` exports like
``shell-env.sh``, then starts optional background services (autopilot daemon,
WUP ``wup watch`` when auto-detected), and runs an outer loop.

Each cycle (see ``_run_cycle``): ``koru scan --apply`` when ticket sources
include scan, then ``koru --queue --loop``, then optional idle diagnostics
when the queue is idle, a WUP health read if the watcher is running, then
autopilot. ``--no-serve`` is a compatibility no-op (``koru serve`` is not
started here).
"""

from __future__ import annotations

import argparse
import subprocess
import sys
import threading
import time
import uuid
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from koru import autonomous_cli_config as _autonomous_cli_config
from koru import autonomous_cycle as _autonomous_cycle_module
from koru import autonomous_cycle_config as _autonomous_cycle_config
from koru import autonomous_cycle_gate as _autonomous_cycle_gate
from koru import autonomous_daemon as _autonomous_daemon
from koru import autonomous_diagnostics as _autonomous_diagnostics
from koru import autonomous_loop_runner as _autonomous_loop_runner
from koru import autonomous_onboarding as _autonomous_onboarding
from koru import autonomous_operator as _autonomous_operator
from koru import autonomous_parser as _autonomous_parser
from koru import autonomous_plugin as _autonomous_plugin
from koru import autonomous_resources as _autonomous_resources
from koru import autonomous_runtime as _autonomous_runtime
from koru.autonomous_auto_pipeline import (
    AutoPipelineProfile,
    AutoPipelineState,
    _collect_argv_options,
    _expand_auto_up_defaults,
    _select_auto_pipeline_profile,
    _update_auto_pipeline_state,
)
from koru.autonomous_checkpoint import (
    compute_backoff_sleep as _compute_backoff_sleep,
)
from koru.autonomous_checkpoint import (
    load_loop_checkpoint as _load_loop_checkpoint,
)
from koru.autonomous_checkpoint import (
    queue_loop_waiting_ticket_label as _queue_loop_waiting_ticket_label,
)
from koru.autonomous_checkpoint import (
    save_loop_checkpoint as _save_loop_checkpoint,
)
from koru.autonomous_cycle import (
    AutoloopState,
    DiagnosticResult,
)
from koru.autonomous_cycle_bridge import run_cycle_with_compat as _run_cycle_with_compat
from koru.autonomous_env import (
    apply_autonomous_env_overrides as _env_apply_autoloop_defaults,
)
from koru.autonomous_processes import (
    guard_existing_autonomous_processes as _guard_existing_autonomous_processes,
)
from koru.autonomous_processes import (
    stop_prior_autonomous_for_auto_start,
)
from koru.autonomous_startup import (
    build_startup_probe,
    format_post_startup_operator_hints,
    format_startup_banner,
    resolve_autopilot_ide_for_autonomous,
)
from koru.autonomous_up import (
    AutonomousUpContext,
    StopSignalState,
)
from koru.autonomous_up import (
    action_up as _autonomous_up_action_up,
)
from koru.autonomous_up import (
    autonomous_context_resource_kwargs as _autonomous_context_resource_kwargs_impl,
)
from koru.autonomous_up import (
    prepare_autonomous_startup_probe as _prepare_autonomous_startup_probe_impl,
)
from koru.autonomous_up import (
    prepare_autonomous_up_context as _prepare_autonomous_up_context_impl,
)
from koru.autonomous_up import (
    run_autonomous_up_loop as _run_autonomous_up_loop_impl,
)
from koru.autonomous_wup import (
    WupHealthResult,
    WupWatchConfig,  # noqa: F401
    _stop_process,
    _wup_watch_command,  # noqa: F401
)
from koru.autonomy.env import plugin_required_for_ide
from koru.autonomy.ide_work import release_in_progress_tickets, resolve_idle_drive_prompt
from koru.autonomy.operator_pipeline import run_startup_operator_pipeline
from koru.autonomy.phases.startup_phase import prepare_startup_context
from koru.autonomy.prompts import build_prompt
from koru.autonomy.telemetry_snapshot import write_autonomy_cycle_telemetry
from koru.autopilot import default_socket_path
from koru.autopilot.plugin_installer import format_plugin_install_result, install_plugin_for_ide
from koru.git_attribution import install_koru_agent_coauthor_hook
from koru.ide_client import IDEControlClient, build_ide_client
from koru.ide_router import resolve_ide_route
from koru.init import init_project, resolve_project_agent_lane
from koru.queue import (
    QueueLoopResult,
    run_planfile_queue_loop,
)
from koru.queue import (
    default_human_prompt as _default_human_prompt,
)
from koru.queue import (
    run_api_request as _run_api_request,
)
from koru.queue import (
    run_llm_request as _run_llm_request,
)
from koru.queue import (
    run_process as _run_process,
)
from koru.queue import (
    run_shell_command as _run_shell_command,
)
from koru.scan import ScanResult, run_scan
from koru.stdio_events import default_stdio_format_from_env, write_stdio_event
from koru.tasks import create_nl_task
from koru.topology import is_component_enabled, is_pipeline_enabled
from gillm.injection import os_injector as _os_injector_module
from koruide.daemon import AutopilotDaemon
from koruide.drive_policy import DrivePolicy as DriveOrchestrator
from gillm.injection.os_injector import OsInjectorError, inject_with_profile, load_profile

_ORIGINAL_LOAD_PROFILE = load_profile
_ORIGINAL_INJECT_WITH_PROFILE = inject_with_profile


def _try_gillm_gui_fallback(
    prompt: str,
    *,
    submit: bool,
    ide: str,
    project: Path | None = None,
) -> dict[str, Any] | None:
    return _autonomous_cycle_gate.try_gillm_gui_fallback(
        prompt,
        submit=submit,
        ide=ide,
        project=project,
    )


def _try_os_injector_fallback(prompt: str, *, submit: bool) -> dict[str, Any] | None:
    load_profile_fn = (
        _os_injector_module.load_profile
        if load_profile is _ORIGINAL_LOAD_PROFILE
        else load_profile
    )
    inject_with_profile_fn = (
        _os_injector_module.inject_with_profile
        if inject_with_profile is _ORIGINAL_INJECT_WITH_PROFILE
        else inject_with_profile
    )
    return _autonomous_cycle_gate.try_os_injector_fallback_with_deps(
        prompt,
        submit=submit,
        load_profile_fn=load_profile_fn,
        inject_with_profile_fn=inject_with_profile_fn,
        os_injector_error=OsInjectorError,
    )


def _stdio_info(msg: str, *, fmt: str) -> None:
    """Human-oriented status; jsonl mode routes to stderr so stdout stays NDJSON-only."""
    from koru.activity_log import activity_info

    activity_info(msg, fmt=fmt)


def _daemon_activity_log(msg: str, *, fmt: str) -> None:
    from koru.activity_log import activity

    if msg.startswith("drive"):
        activity("DAEMON", msg, fmt=fmt)
    else:
        activity("DAEMON", msg, fmt=fmt)


def _allow_keyboard_autopilot_fallback() -> bool:
    return _autonomous_cycle_gate.allow_keyboard_autopilot_fallback()


def _effective_cycle_autopilot_enabled(
    enabled: bool,
    *,
    client: object | None,
    autopilot_ide: str,
    stdio_format: str,
) -> bool:
    return _autonomous_cycle_gate.effective_cycle_autopilot_enabled(
        enabled,
        client=client,
        autopilot_ide=autopilot_ide,
        stdio_format=stdio_format,
        plugin_required_for_ide=plugin_required_for_ide,
        status_has_autopilot_plugin=_status_has_autopilot_plugin,
        stdio_info=_stdio_info,
    )


def _scan_while_waiting_input_enabled() -> bool:
    return _autonomous_cycle_gate.scan_while_waiting_input_enabled()


def _effective_cycle_scan_enabled(
    enabled: bool,
    *,
    state: object,
    stdio_format: str,
) -> bool:
    return _autonomous_cycle_gate.effective_cycle_scan_enabled(
        enabled,
        state=state,
        stdio_format=stdio_format,
        stdio_info=_stdio_info,
    )


def _resolve_autopilot_ide(cli_value: str) -> str:
    return _autonomous_cycle_gate.resolve_autopilot_ide(cli_value)


def _apply_agent_lane_environ(project: Path, agent_lane: str) -> str | None:
    return _autonomous_cycle_gate.apply_agent_lane_environ(project, agent_lane)


def _build_parser() -> argparse.ArgumentParser:
    return _autonomous_parser.build_parser(
        default_stdio_format=default_stdio_format_from_env(),
    )


def _ensure_init(project: Path, *, force: bool, stdio_format: str = "human") -> None:
    config_path = project / ".planfile" / "config.yaml"
    if config_path.exists() and not force:
        return
    report = init_project(project, force=force)
    _stdio_info(
        f"koru autonomous: init {'re-' if force else ''}done at {report.project}",
        fmt=stdio_format,
    )


def _current_koru_version() -> str | None:
    return _autonomous_daemon._current_koru_version()


def _daemon_status_version(status: Mapping[str, Any] | None) -> str | None:
    return _autonomous_daemon._daemon_status_version(status)


def _daemon_status_compatible(status: Mapping[str, Any] | None) -> tuple[bool, str]:
    return _autonomous_daemon.daemon_status_compatible(
        status,
        current_version=_current_koru_version,
    )


def _daemon_status_log_summary(status: Mapping[str, Any] | None) -> str:
    return _autonomous_daemon.daemon_status_log_summary(
        status,
        plugin_rows_summary=_plugin_rows_log_summary,
    )


def _stop_reused_daemon(
    client: IDEControlClient,
    socket_path: Path,
    *,
    stdio_format: str,
    timeout_seconds: float = 2.0,
) -> bool:
    return _autonomous_daemon._stop_reused_daemon(
        client,
        socket_path,
        stdio_format=stdio_format,
        timeout_seconds=timeout_seconds,
        stdio_info=_stdio_info,
        build_client=build_ide_client,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


def _start_or_reuse_daemon(
    *,
    project: Path,
    socket_path: Path,
    stdio_format: str = "human",
) -> tuple[IDEControlClient, AutopilotDaemon | None, threading.Thread | None]:
    return _autonomous_daemon.start_or_reuse_daemon(
        project=project,
        socket_path=socket_path,
        stdio_format=stdio_format,
        stdio_info=_stdio_info,
        build_client=build_ide_client,
        daemon_factory=AutopilotDaemon,
        thread_factory=threading.Thread,
        current_version=_current_koru_version,
        plugin_rows_summary=_plugin_rows_log_summary,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


def _plugin_rows_log_summary(rows: object) -> str:
    return _autonomous_plugin.plugin_rows_log_summary(rows)


def _plugin_status_decision(status: Mapping[str, Any], ide: str) -> tuple[bool, str]:
    _autonomous_plugin.DriveOrchestrator = DriveOrchestrator
    return _autonomous_plugin.plugin_status_decision(status, ide)


def _status_has_autopilot_plugin(status: Mapping[str, Any], ide: str) -> bool:
    return _plugin_status_decision(status, ide)[0]


def _wait_for_autopilot_plugin(
    client: IDEControlClient,
    ide: str,
    *,
    timeout_seconds: float,
    interval_seconds: float = 0.25,
    stdio_format: str | None = None,
) -> bool:
    return _autonomous_plugin.wait_for_autopilot_plugin(
        client,
        ide,
        timeout_seconds=timeout_seconds,
        interval_seconds=interval_seconds,
        stdio_info=_stdio_info,
        stdio_format=stdio_format,
        monotonic=time.monotonic,
        sleep=time.sleep,
    )


def _is_topology_enabled(project: Path, key: str, *, fallback: bool, enabled: bool) -> bool:
    if not enabled:
        return fallback
    try:
        if key in {"idle-diagnostics", "autoloop:queue", "scan:on-change", "autopilot:drive"}:
            return is_pipeline_enabled(project, key)
        return is_component_enabled(project, key)
    except Exception:
        return fallback


def _run_command_check(
    project: Path,
    check_id: str,
    command: list[str],
    *,
    stdio_format: str = "human",
) -> bool:
    return _autonomous_diagnostics.run_command_check(
        stdio_info=_stdio_info,
        project=project,
        check_id=check_id,
        command=command,
        stdio_format=stdio_format,
    )


def _create_diagnostic_ticket(
    *,
    stdio_format: str = "human",
    project: Path,
    check_id: str,
    summary: str,
    cycle: int,
    queue_status: str,
    queue_name: str,
    priority: str,
    state_dir: Path,
) -> None:
    return _autonomous_diagnostics.create_diagnostic_ticket(
        stdio_info=_stdio_info,
        stdio_format=stdio_format,
        project=project,
        check_id=check_id,
        summary=summary,
        cycle=cycle,
        queue_status=queue_status,
        queue_name=queue_name,
        priority=priority,
        state_dir=state_dir,
    )


def _clear_diagnostic_marker(state_dir: Path, check_id: str) -> None:
    _autonomous_diagnostics.clear_diagnostic_marker(state_dir, check_id)


def _read_wup_health(
    *,
    project: Path,
    state: AutoloopState,
    diagnostic_tickets: bool,
    ticket_queue: str,
    state_dir: Path,
) -> WupHealthResult:
    return _autonomous_diagnostics.read_wup_health(
        project=project,
        state=state,
        diagnostic_tickets=diagnostic_tickets,
        ticket_queue=ticket_queue,
        state_dir=state_dir,
        create_ticket=_create_diagnostic_ticket,
    )


def _run_idle_diagnostics(
    *,
    stdio_format: str = "human",
    project: Path,
    profile: str,
    cycle: int,
    queue_status: str,
    diagnostic_tickets: bool,
    diagnostic_ticket_queue: str,
    diagnostic_ticket_priority: str,
    diagnostic_state_dir: Path,
    topology_integration: bool,
) -> DiagnosticResult:
    def create_ticket(**kwargs: Any) -> None:
        _create_diagnostic_ticket(stdio_format=stdio_format, **kwargs)

    return _autonomous_diagnostics.run_idle_diagnostics(
        stdio_info=_stdio_info,
        is_topology_enabled=_is_topology_enabled,
        run_command=_run_command_check,
        clear_marker=_clear_diagnostic_marker,
        create_ticket=create_ticket,
        make_result=lambda status, failed: DiagnosticResult(status=status, failed=failed),
        stdio_format=stdio_format,
        project=project,
        profile=profile,
        cycle=cycle,
        queue_status=queue_status,
        diagnostic_tickets=diagnostic_tickets,
        diagnostic_ticket_queue=diagnostic_ticket_queue,
        diagnostic_ticket_priority=diagnostic_ticket_priority,
        diagnostic_state_dir=diagnostic_state_dir,
        topology_integration=topology_integration,
    )


def _run_cycle(**kwargs: Any) -> tuple[ScanResult | None, QueueLoopResult, str, DiagnosticResult]:
    # Keep historical monkeypatch points on ``koru.autonomous`` working by
    # forwarding the current module callables into the canonical cycle module.
    return _run_cycle_with_compat(
        kwargs,
        cycle_module=_autonomous_cycle_module,
        dependencies={
            "time": time,
            "run_scan": run_scan,
            "run_planfile_queue_loop": run_planfile_queue_loop,
            "_run_process": _run_process,
            "_run_shell_command": _run_shell_command,
            "_run_api_request": _run_api_request,
            "_run_llm_request": _run_llm_request,
            "_default_human_prompt": _default_human_prompt,
            "resolve_idle_drive_prompt": resolve_idle_drive_prompt,
            "build_prompt": build_prompt,
            "write_autonomy_cycle_telemetry": write_autonomy_cycle_telemetry,
            "create_nl_task": create_nl_task,
            "is_component_enabled": is_component_enabled,
            "is_pipeline_enabled": is_pipeline_enabled,
            "_run_idle_diagnostics": _run_idle_diagnostics,
            "_try_gillm_gui_fallback": _try_gillm_gui_fallback,
            "_try_os_injector_fallback": _try_os_injector_fallback,
        },
    )


def _setup_autonomous_session(
    args: argparse.Namespace,
) -> tuple[str, Path, int]:
    """Initialize autonomous session and return correlation_id, project path, and guard_rc."""
    return _autonomous_runtime.setup_autonomous_session(
        args,
        apply_env_defaults=_env_apply_autoloop_defaults,
        uuid_factory=uuid.uuid4,
        guard_existing_processes=_guard_existing_autonomous_processes,
        ensure_init=_ensure_init,
        stdio_info=_stdio_info,
        write_event=write_stdio_event,
    )


def _setup_autopilot_daemon(
    args: argparse.Namespace,
    project: Path,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None, Path | None]:
    """Setup autopilot daemon if enabled."""
    return _autonomous_runtime.setup_autopilot_daemon(
        args,
        project,
        apply_agent_lane_environ=_apply_agent_lane_environ,
        resolve_autopilot_ide=resolve_autopilot_ide_for_autonomous,
        resolve_ide_route_fn=resolve_ide_route,
        default_socket_path=default_socket_path,
        start_or_reuse_daemon=_start_or_reuse_daemon,
        stdio_info=_stdio_info,
    )


def _enable_autonomous_strict_plugin_policy(args: argparse.Namespace) -> None:
    """Default autonomous runs to fail-closed on plugin drift and weak ACKs."""
    _autonomous_plugin.enable_autonomous_strict_plugin_policy(
        args,
        stdio_info=_stdio_info,
    )


def _run_mcp_provision(project: Path, stdio_format: str) -> bool:
    """Run MCP workspace provision and return True if it ran."""
    return _autonomous_operator.run_mcp_provision(
        project,
        stdio_format,
        stdio_info=_stdio_info,
    )


def _setup_autopilot_plugin(
    args: argparse.Namespace,
    autopilot_ide: str,
    socket_path: Path | None,
    client: IDEControlClient | None,
) -> bool | None:
    """Install and wait for autopilot plugin if enabled."""
    return _autonomous_operator.setup_autopilot_plugin(
        args,
        autopilot_ide,
        socket_path,
        client,
        project=Path(getattr(args, "project", ".")).expanduser().resolve(),
        install_plugin_for_ide=install_plugin_for_ide,
        format_plugin_install_result=format_plugin_install_result,
        allow_keyboard_fallback=_allow_keyboard_autopilot_fallback,
        wait_for_plugin=_wait_for_autopilot_plugin,
        stdio_info=_stdio_info,
    )


def _run_operator_pipeline(
    args: argparse.Namespace,
    project: Path,
    startup_probe: Any,
    plugin_connected: bool | None,
    mcp_provision_ran: bool,
    correlation_id: str,
) -> None:
    """Run operator pipeline if enabled."""
    def format_runtime_hints(
        probe: Any,
        *,
        plugin_connected: bool | None = None,
    ) -> list[str]:
        return format_post_startup_operator_hints(
            probe,
            plugin_connected=plugin_connected,
            compact=plugin_connected is False,
        )

    _autonomous_operator.run_operator_pipeline(
        args,
        project,
        startup_probe,
        plugin_connected,
        mcp_provision_ran,
        correlation_id,
        format_hints=format_runtime_hints,
        run_pipeline=run_startup_operator_pipeline,
        stdio_info=_stdio_info,
    )


def _unblock_queue_if_needed(project: Path, stdio_format: str) -> None:
    """Release in-progress tickets if KORU_QUEUE_UNBLOCK is set."""
    _autonomous_operator.unblock_queue_if_needed(
        project,
        stdio_format,
        release_in_progress_tickets=release_in_progress_tickets,
        runner=_run_process,
        stdio_info=_stdio_info,
    )


def _restart_daemon_if_needed(
    args: argparse.Namespace,
    client: IDEControlClient | None,
    socket_path: Path | None,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    autopilot_socket_observed_at_boot: bool,
    project: Path,
) -> tuple[IDEControlClient | None, AutopilotDaemon | None, threading.Thread | None]:
    """Restart daemon if socket is missing."""
    return _autonomous_daemon.restart_daemon_if_needed(
        args,
        client,
        socket_path,
        daemon,
        thread,
        autopilot_socket_observed_at_boot,
        project,
        stdio_info=_stdio_info,
        start_or_reuse_daemon_fn=_start_or_reuse_daemon,
    )


def _handle_cycle_exit_conditions(
    args: argparse.Namespace,
    queue_result: Any,
    cycle: int,
    correlation_id: str,
) -> bool:
    """Check if we should exit the cycle loop. Returns True if should exit."""
    return _autonomous_loop_runner.handle_cycle_exit_conditions(
        args,
        queue_result,
        cycle,
        correlation_id,
        write_event=write_stdio_event,
        stdio_info=_stdio_info,
        output_stream=sys.stdout,
    )


def _cleanup_autonomous_session(
    previous_stdio_format_env: str | None,
    previous_sigterm: Any,
    daemon: AutopilotDaemon | None,
    thread: threading.Thread | None,
    wup_process: Any,
    stdio_format: str,
) -> None:
    """Clean up autonomous session resources."""
    _autonomous_runtime.cleanup_autonomous_session(
        previous_stdio_format_env,
        previous_sigterm,
        daemon,
        thread,
        wup_process,
        stdio_format,
        stop_process=_stop_process,
    )


def _select_and_log_cycle_profile(
    args: argparse.Namespace,
    auto_pipeline_state: AutoPipelineState | None,
    *,
    enable_scan: bool,
) -> AutoPipelineProfile | None:
    """Select auto pipeline profile and log it if enabled."""
    return _autonomous_cycle_config.select_and_log_cycle_profile(
        args,
        auto_pipeline_state,
        enable_scan=enable_scan,
        select_profile=_select_auto_pipeline_profile,
        stdio_info=_stdio_info,
    )


def _resolve_effective_cycle_flags(
    args: argparse.Namespace,
    profile: AutoPipelineProfile | None,
    *,
    enable_scan: bool,
    loop_state: object,
    client: object,
    autopilot_ide: str,
) -> tuple[bool, bool]:
    """Resolve effective scan and autopilot enable flags for the cycle."""
    return _autonomous_cycle_config.resolve_effective_cycle_flags(
        args,
        profile,
        enable_scan=enable_scan,
        loop_state=loop_state,
        client=client,
        autopilot_ide=autopilot_ide,
        effective_scan_enabled=_effective_cycle_scan_enabled,
        effective_autopilot_enabled=_effective_cycle_autopilot_enabled,
    )


def _build_cycle_run_kwargs(
    args: argparse.Namespace,
    profile: AutoPipelineProfile | None,
    *,
    cycle: int,
    project: Path,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    client: object,
    loop_state: object,
    diagnostic_state_dir: Path,
    wup_process: subprocess.Popen | None,
    correlation_id: str,
) -> dict[str, Any]:
    """Build kwargs for _run_cycle call."""
    return _autonomous_cycle_config.build_cycle_run_kwargs(
        args,
        profile,
        cycle=cycle,
        project=project,
        queue_name=queue_name,
        enable_scan=enable_scan,
        autopilot_ide=autopilot_ide,
        client=client,
        loop_state=loop_state,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
    )


def _compute_cycle_sleep(
    args: argparse.Namespace,
    loop_state: object,
    queue_result: object,
    autopilot_status: str = "",
) -> float:
    """Compute sleep duration for the cycle."""
    return _autonomous_cycle_config.compute_cycle_sleep(
        args,
        loop_state,
        queue_result,
        autopilot_status=autopilot_status,
        compute_backoff_sleep=_compute_backoff_sleep,
        now=time.time,
    )


def _sleep(seconds: float) -> None:
    time.sleep(seconds)


def _run_autonomous_cycle(
    *,
    cycle: int,
    args: argparse.Namespace,
    project: Path,
    client: object,
    daemon: object,
    thread: threading.Thread,
    socket_path: Path,
    autopilot_socket_observed_at_boot: bool,
    queue_name: str | None,
    enable_scan: bool,
    autopilot_ide: str,
    loop_state: object,
    checkpoint_path: Path,
    diagnostic_state_dir: Path,
    wup_process: subprocess.Popen | None,
    correlation_id: str,
    auto_pipeline_state: AutoPipelineState | None = None,
) -> bool:
    """Run one autonomous cycle. Returns True if the loop should exit."""
    return _autonomous_loop_runner.run_autonomous_cycle(
        cycle=cycle,
        args=args,
        project=project,
        client=client,
        daemon=daemon,
        thread=thread,
        socket_path=socket_path,
        autopilot_socket_observed_at_boot=autopilot_socket_observed_at_boot,
        queue_name=queue_name,
        enable_scan=enable_scan,
        autopilot_ide=autopilot_ide,
        loop_state=loop_state,
        checkpoint_path=checkpoint_path,
        diagnostic_state_dir=diagnostic_state_dir,
        wup_process=wup_process,
        correlation_id=correlation_id,
        auto_pipeline_state=auto_pipeline_state,
        restart_daemon_if_needed=_restart_daemon_if_needed,
        select_and_log_cycle_profile=_select_and_log_cycle_profile,
        resolve_effective_cycle_flags=_resolve_effective_cycle_flags,
        build_cycle_run_kwargs=_build_cycle_run_kwargs,
        run_cycle=_run_cycle,
        update_auto_pipeline_state=_update_auto_pipeline_state,
        save_loop_checkpoint=_save_loop_checkpoint,
        queue_loop_waiting_ticket_label=_queue_loop_waiting_ticket_label,
        handle_exit_conditions=_handle_cycle_exit_conditions,
        compute_cycle_sleep=_compute_cycle_sleep,
        stdio_info=_stdio_info,
        sleep=_sleep,
    )


def _setup_autonomous_env_vars() -> tuple[str | None, dict[str, tuple[bool, str | None]]]:
    """Setup and save environment variables for autonomous mode."""
    return _autonomous_runtime.setup_autonomous_env_vars()


def _restore_autonomous_env_vars(snapshot: dict[str, tuple[bool, str | None]]) -> None:
    """Restore environment variables after autonomous mode."""
    _autonomous_runtime.restore_autonomous_env_vars(snapshot)


def _run_autonomous_pre_checks(
    args: argparse.Namespace,
    project: Path,
    startup_probe: object,
    socket_path: Path,
    autopilot_ide: str,
    client: object,
    correlation_id: str,
) -> tuple[bool, bool]:
    """Run pre-checks before autonomous loop: MCP provision and plugin setup."""
    mcp_provision_ran = _run_mcp_provision(project, args.emit_events)
    plugin_connected = _setup_autopilot_plugin(args, autopilot_ide, socket_path, client)
    _run_operator_pipeline(
        args, project, startup_probe, plugin_connected, mcp_provision_ran, correlation_id
    )
    _unblock_queue_if_needed(project, args.emit_events)
    return mcp_provision_ran, plugin_connected


def _maybe_run_interactive_onboarding(args: argparse.Namespace) -> object | None:
    """Run TTY onboarding for `koru auto` before autonomous resources are created."""
    if not _autonomous_onboarding.should_run_interactive_onboarding(args):
        if getattr(args, "_invoked_as_auto", False):
            _autonomous_onboarding.ensure_project_state(args.project, source="auto")
        return None
    return _autonomous_onboarding.run_interactive_onboarding(
        args,
        stdio_info=lambda msg: _stdio_info(msg, fmt=args.emit_events),
    )


def _build_and_log_startup_probe(args: argparse.Namespace, project: Path) -> object:
    return _autonomous_runtime.build_and_log_startup_probe(
        args,
        project,
        apply_agent_lane_environ=_apply_agent_lane_environ,
        build_startup_probe=build_startup_probe,
        format_startup_banner=format_startup_banner,
        resolve_project_lane=resolve_project_agent_lane,
        stdio_info=_stdio_info,
    )


def _install_sigterm_interrupt_handler(
    args: argparse.Namespace,
    stop_state: StopSignalState,
) -> Any:
    return _autonomous_runtime.install_sigterm_interrupt_handler(
        args,
        stop_state,
        stdio_info=_stdio_info,
    )


def _handle_autonomous_interrupt(
    args: argparse.Namespace,
    *,
    correlation_id: str,
    stopped_by_sigterm: bool,
) -> int:
    return _autonomous_runtime.handle_autonomous_interrupt(
        args,
        correlation_id=correlation_id,
        stopped_by_sigterm=stopped_by_sigterm,
        write_event=write_stdio_event,
        stdio_info=_stdio_info,
    )


def _prepare_autonomous_startup_probe(args: argparse.Namespace, project: Path) -> object:
    return _prepare_autonomous_startup_probe_impl(
        args,
        project,
        install_coauthor_hook=install_koru_agent_coauthor_hook,
        build_and_log_startup_probe=_build_and_log_startup_probe,
        stdio_info=_stdio_info,
    )


def _autonomous_context_resource_kwargs(resources: tuple[object, ...]) -> dict[str, object]:
    return _autonomous_context_resource_kwargs_impl(resources)


def _prepare_autonomous_up_context(
    args: argparse.Namespace,
) -> tuple[AutonomousUpContext | None, int]:
    return prepare_startup_context(
        args,
        prepare_up_context=lambda startup_args: _prepare_autonomous_up_context_impl(
            startup_args,
            setup_env_vars=_setup_autonomous_env_vars,
            setup_session=_setup_autonomous_session,
            prepare_startup_probe=_prepare_autonomous_startup_probe,
            setup_resources=_autonomous_resources.setup_autonomous_resources,
            enable_strict_plugin_policy=_enable_autonomous_strict_plugin_policy,
            setup_autopilot_daemon=_setup_autopilot_daemon,
            load_checkpoint=_load_loop_checkpoint,
        ),
    )


def _run_autonomous_up_loop(context: AutonomousUpContext) -> int:
    return _run_autonomous_up_loop_impl(
        context,
        install_sigterm_handler=_install_sigterm_interrupt_handler,
        run_pre_checks=_run_autonomous_pre_checks,
        run_autonomous_cycle=_run_autonomous_cycle,
        handle_interrupt=_handle_autonomous_interrupt,
        restore_env_vars=_restore_autonomous_env_vars,
        cleanup_session=_cleanup_autonomous_session,
    )


def _action_up(args: argparse.Namespace) -> int:
    return _autonomous_up_action_up(
        args,
        maybe_run_interactive_onboarding=_maybe_run_interactive_onboarding,
        prepare_up_context=_prepare_autonomous_up_context,
        run_up_loop=_run_autonomous_up_loop,
        stdio_info=_stdio_info,
    )


def _normalize_autonomous_argv(argv: list[str]) -> list[str]:
    """Normalize command line arguments for autonomous mode."""
    return _autonomous_cli_config.normalize_autonomous_argv(argv)


def _configure_auto_mode_args(
    argv: list[str],
    args: Any,
    invoked_as_auto: bool,
) -> tuple[set[str], list[str]]:
    """Configure arguments for auto mode and return user options and normalized argv."""
    return _autonomous_cli_config.configure_auto_mode_args(
        argv,
        invoked_as_auto,
        collect_argv_options=_collect_argv_options,
        expand_auto_up_defaults=_expand_auto_up_defaults,
    )


def _apply_auto_pipeline_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply auto-pipeline specific flags to args."""
    _autonomous_cli_config.apply_auto_pipeline_flags(args, invoked_as_auto)


def _apply_replace_existing_flags(args: Any, invoked_as_auto: bool) -> None:
    """Apply replace-existing flags for auto mode."""
    _autonomous_cli_config.apply_replace_existing_flags(args, invoked_as_auto)


def _parse_autonomous_args(argv: list[str], *, invoked_as_auto: bool) -> argparse.Namespace:
    argv = _normalize_autonomous_argv(argv)
    auto_user_options, argv = _configure_auto_mode_args(argv, None, invoked_as_auto)

    args = _build_parser().parse_args(argv)
    args._invoked_as_auto = bool(invoked_as_auto)
    _apply_auto_pipeline_flags(args, invoked_as_auto)
    args._auto_user_options = auto_user_options
    _apply_replace_existing_flags(args, invoked_as_auto)
    _autonomous_cli_config.apply_autonomy_strategy_defaults(args)
    from koru.scan import apply_scan_path_environ

    apply_scan_path_environ(getattr(args, "paths", None))
    return args


def autonomous_main(argv: list[str], *, invoked_as_auto: bool = False) -> int:
    args = _parse_autonomous_args(argv, invoked_as_auto=invoked_as_auto)
    if args.action == "up":
        return _action_up(args)
    return 2


__all__ = [
    "WupHealthResult",
    "WupWatchConfig",
    "_read_wup_health",
    "_wup_watch_command",
    "autonomous_main",
    "stop_prior_autonomous_for_auto_start",
]
