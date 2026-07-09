"""Cycle-configuration helpers for ``koru autonomous``."""

from __future__ import annotations

import os
import sys
from collections.abc import Mapping
from pathlib import Path
from typing import Any

from koru.autonomy.autopilot_status import parse_autopilot_status
from koru.autonomy.env import env_get

_PLUGIN_RECONNECT_BLOCKERS = frozenset(
    {
        "plugin_missing",
        "plugin_not_connected",
        "plugin_status_unavailable",
        "plugin_version_mismatch",
    }
)


def resolve_agent_lane_from_environ(
    args: Any,
    project: Path,
    *,
    apply_agent_lane_environ: Any,
    environ: Mapping[str, str] | None = None,
) -> str | None:
    """Resolve the selected autopilot lane without hard-coding global env reads."""
    lane = env_get("KORU_AUTOPILOT_INSTANCE", None, environ=environ)
    if lane:
        return lane
    return apply_agent_lane_environ(project, args.agent_lane)


def _autodetect_shell_client_for_auto(
    autopilot_ide: str,
    lane: str | None,
    *,
    tillm_available: Any,
    detect_running_ides_fn: Any = None,
    detect_shell_client_fn: Any = None,
) -> str | None:
    """Resolve ``--ide auto`` to a shell client on editor-less hosts.

    Only engages when no target was named, no lane points at an editor, and no
    editor IDE process is running — i.e. a headless/CI host where the plugin
    lane can never connect. Returns the first tillm client found on PATH.
    """
    token = (autopilot_ide or "").strip().lower()
    if token not in ("", "auto"):
        return None
    if lane not in (None, "", "auto"):
        return None
    if (os.environ.get("KORU_AUTO_SHELL_CLIENT") or "").strip().lower() in (
        "0",
        "false",
        "no",
        "off",
    ):
        return None
    if not tillm_available():
        return None
    if detect_running_ides_fn is None:
        from koruide.ide import detect_running_ides as detect_running_ides_fn
    if detect_running_ides_fn():
        return None
    if detect_shell_client_fn is None:
        from koru.tillm_bridge import (
            detect_available_shell_client as detect_shell_client_fn,
        )
    return detect_shell_client_fn()


def _shell_client_from_environ() -> str | None:
    """Honor operator-configured shell client before PATH autodetect."""
    from koru.tillm_bridge import (
        looks_like_shell_client,
        shell_drive_client_id,
        shell_agent_available,
    )

    for env_key in ("KORU_TILLM_CLIENT", "URIRUN_KORU_IDE"):
        raw = (os.environ.get(env_key) or "").strip()
        if not raw or raw.lower() == "auto":
            continue
        client_id = shell_drive_client_id(raw)
        if client_id and shell_agent_available(client_id):
            return client_id
        if looks_like_shell_client(raw):
            return shell_drive_client_id(raw) or raw
    return None


def _default_shell_execute_profile(client_id: str) -> str:
    """Pick a tillm execute profile the named client actually supports."""
    try:
        from tillm.registry import get_client_spec

        if "automation" in get_client_spec(client_id).supported_execute_profiles():
            return "automation"
    except Exception:
        pass
    return "default"


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
    lane = resolve_agent_lane_from_environ(
        args,
        project,
        apply_agent_lane_environ=apply_agent_lane_environ,
        environ=os.environ,
    )
    # Shell client targets (claude-code, aider, codex, …) bypass IDE-route
    # resolution: the drive step talks to the vendor CLI via tillm instead of
    # the autopilot daemon.
    from koru.tillm_bridge import (
        looks_like_shell_client,
        shell_drive_client_id,
        tillm_available,
    )

    shell_client = shell_drive_client_id(args.autopilot_ide)
    if not shell_client and looks_like_shell_client(args.autopilot_ide):
        # The token names a shell client but tillm could not resolve it —
        # routing it to the IDE plugin lane would silently drive the wrong
        # backend, so abort with an actionable message instead.
        raise SystemExit(
            f"[koru] --ide {args.autopilot_ide} names a shell LLM client but the "
            "tillm package is unavailable in this environment. Install tillm "
            "(pip install tillm) or pick an editor IDE (e.g. --ide vscode)."
        )
    if not shell_client:
        shell_client = _shell_client_from_environ()
        if shell_client:
            print(
                f"[koru] using shell client '{shell_client}' from "
                "KORU_TILLM_CLIENT/URIRUN_KORU_IDE.",
                file=sys.stderr,
            )
    if not shell_client:
        shell_client = _autodetect_shell_client_for_auto(
            args.autopilot_ide, lane, tillm_available=tillm_available
        )
        if shell_client:
            print(
                f"[koru] no editor IDE detected; auto-selected shell client "
                f"'{shell_client}' (tillm). Pass --ide to override.",
                file=sys.stderr,
            )
    if shell_client:
        selected_ide = shell_client
        os.environ["KORU_TILLM_CLIENT"] = shell_client
        llm_model = (getattr(args, "llm_model", None) or "").strip()
        if llm_model:
            os.environ["KORU_TILLM_MODEL"] = llm_model
        # Autonomous drive needs the client to apply edits and run checks;
        # the conservative default profile would leave it read-only — but only
        # for clients that actually support an ``automation`` profile (aider does not).
        if "KORU_TILLM_EXECUTE_PROFILE" not in os.environ:
            os.environ["KORU_TILLM_EXECUTE_PROFILE"] = _default_shell_execute_profile(
                shell_client
            )
    else:
        # Resolve lane slugs (cursor-main, jetbrains-main) to canonical IDE ids (cursor, jetbrains).
        selected_ide, _autopilot_ide_source = resolve_autopilot_ide(
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
    return enable_scan, queue_name, selected_ide, loop_state, checkpoint_path, restored_cycle


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
    enable_autopilot: bool | None = None,
    autopilot_ide: str,
    client: Any,
    loop_state: Any,
    diagnostic_state_dir: Path,
    wup_process: Any | None,
    correlation_id: str,
) -> dict[str, Any]:
    """Build kwargs for the core cycle runner."""
    requested_enable_autopilot = (
        profile.enable_autopilot if profile is not None else args.enable_autopilot
    )
    return {
        "cycle": cycle,
        "project": project,
        "actor": args.actor,
        "queue_name": queue_name,
        "enable_scan": enable_scan,
        "max_iterations": profile.max_iterations if profile is not None else args.max_iterations,
        "enable_autopilot": (
            requested_enable_autopilot
            if enable_autopilot is None
            else enable_autopilot
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
    status = parse_autopilot_status(autopilot_status)
    return status.skipped and status.code in _PLUGIN_RECONNECT_BLOCKERS


__all__ = [
    "configure_loop_state",
    "resolve_agent_lane_from_environ",
    "select_and_log_cycle_profile",
    "resolve_effective_cycle_flags",
    "build_cycle_run_kwargs",
    "compute_cycle_sleep",
]
