"""``koru autopilot`` subcommand wiring.

Kept in its own module to keep ``koru.cli`` digestible. The single
public entrypoint is :func:`autopilot_main` which mirrors the
``_task_main`` / ``_scan_main`` style used elsewhere.
"""

import argparse
import contextlib
import json
import os
import sys
import time
from pathlib import Path

from koru.autopilot import (
    calibrate_cli,
    daemon_cli,
    default_socket_path,
    doctor_cli,
    install_plugin_cli,
    systemd_cli,
    tail_cli,
)
from koru.autopilot.cli_direct_drive import (
    _auto_direct_fallback_enabled as _auto_direct_fallback_enabled,
)
from koru.autopilot.cli_direct_drive import (
    _emit_direct_drive_auto_selection as _emit_direct_drive_auto_selection,
)
from koru.autopilot.cli_direct_drive import (
    _emit_json_payload as _emit_json_payload,
)
from koru.autopilot.cli_direct_drive import (
    _handle_os_injector_fallback as _handle_os_injector_fallback,
)
from koru.autopilot.cli_direct_drive import (
    _handle_os_profile_direct_error as _handle_os_profile_direct_error,
)
from koru.autopilot.cli_direct_drive import (
    _print_drive_delay_message as _print_drive_delay_message,
)
from koru.autopilot.cli_direct_drive import (
    _run_direct_drive as _run_direct_drive,
)
from koru.autopilot.cli_direct_drive import (
    _should_fallback_to_direct as _should_fallback_to_direct,
)
from koru.autopilot.cli_direct_drive import (
    _try_profile_direct_drive as _try_profile_direct_drive,
)
from koru.autopilot.cli_direct_drive import (
    _type_text_direct_drive as _type_text_direct_drive,
)
from koru.autopilot.cli_parser import build_autopilot_parser as _build_parser
from koru.autopilot.commands.drive import action_drive as _drive_action_impl
from koru.autopilot.commands.drive import _drive_command_argv
from koru.autopilot.commands.handoff import action_handoff as _handoff_action_impl
from koru.autopilot.commands.manage import action_manage as _manage_action_impl
from koru.autopilot.commands.shutdown import action_shutdown as _shutdown_action_impl
from koru.autopilot.commands.status import action_status as _status_action_impl
from koru.autopilot.cli_trace import action_trace as _action_trace
from koru.autopilot.client import AutopilotClient
from koru.autopilot.ide import (
    detect_focused_ide_id,
    detect_running_ides,
    detect_terminal_host_ide_id,
    normalize_ide_id,
    resolve_drive_target,
)
from koru.autopilot.injector import Injector
from koru.control_commands import shell_command


def _action_calibrate(args: argparse.Namespace) -> int:
    return calibrate_cli.action_calibrate(
        args,
        sleep_fn=time.sleep,
        resolve_target=resolve_drive_target,
    )


def _action_session_start(args: argparse.Namespace) -> int:
    return calibrate_cli.action_session_start(
        args,
        resolve_ides=calibrate_cli.resolve_session_ides,
        sleep_fn=time.sleep,
    )


@contextlib.contextmanager
def _temporary_autopilot_instance(instance: str):
    previous = os.environ.get("KORU_AUTOPILOT_INSTANCE")
    os.environ["KORU_AUTOPILOT_INSTANCE"] = instance
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop("KORU_AUTOPILOT_INSTANCE", None)
        else:
            os.environ["KORU_AUTOPILOT_INSTANCE"] = previous


def _resolve_cli_ide_lane(args: argparse.Namespace) -> str | None:
    requested = normalize_ide_id(getattr(args, "ide", None))
    if requested and requested != "auto":
        return requested
    instance = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_INSTANCE"))
    if instance and instance != "auto":
        return instance
    env_ide = normalize_ide_id(os.environ.get("KORU_AUTOPILOT_IDE"))
    if env_ide and env_ide != "auto":
        return env_ide
    terminal = normalize_ide_id(detect_terminal_host_ide_id())
    if terminal:
        return terminal
    focused = normalize_ide_id(detect_focused_ide_id())
    if focused:
        return focused
    return None


def _resolve_client_socket(args: argparse.Namespace) -> Path | None:
    if getattr(args, "socket", None) is not None:
        return args.socket
    if (os.environ.get("KORU_AUTOPILOT_SOCKET") or "").strip():
        return None
    if (os.environ.get("KORU_AUTOPILOT_INSTANCE") or "").strip():
        return None
    lane = _resolve_cli_ide_lane(args)
    if not lane:
        return None
    with _temporary_autopilot_instance(lane):
        return default_socket_path()


def _client(args: argparse.Namespace) -> AutopilotClient:
    return AutopilotClient(socket_path=_resolve_client_socket(args))


def _daemon_start_hint(args: argparse.Namespace) -> str:
    lane = _resolve_cli_ide_lane(args)
    if lane:
        return (
            f"Start it with `KORU_AUTOPILOT_INSTANCE={lane} koru autopilot daemon`, "
            "or run `koru auto` for the selected lane."
        )
    return "Start it with `koru autopilot daemon`, or pass --direct to inject from this terminal."


# ----- action handlers ------------------------------------------------------


_action_daemon = daemon_cli.action_daemon


def _action_drive(args: argparse.Namespace) -> int:
    """Wrapper for drive command with dependency injection."""
    return _drive_action_impl(
        args,
        client_fn=_client,
        daemon_start_hint_fn=_daemon_start_hint,
        run_direct_drive_fn=_run_direct_drive,
        should_fallback_fn=_should_fallback_to_direct,
    )


def _action_status(args: argparse.Namespace) -> int:
    """Wrapper for status command with dependency injection."""
    return _status_action_impl(
        args,
        client_fn=_client,
        daemon_start_hint_fn=_daemon_start_hint,
        normalize_ide_fn=normalize_ide_id,
        resolve_target_ide_fn=resolve_drive_target,
    )


def _action_shutdown(args: argparse.Namespace) -> int:
    """Wrapper for shutdown command with dependency injection."""
    return _shutdown_action_impl(
        args,
        client_fn=_client,
        daemon_shutdown_fn=daemon_cli.action_shutdown,
    )


_action_ide_list = daemon_cli.action_ide_list


def _action_doctor(args: argparse.Namespace) -> int:
    return doctor_cli.action_doctor(
        args,
        injector_factory=Injector,
        fix_payload_factory=doctor_cli.doctor_fix_payload,
        detect_ides=detect_running_ides,
        detect_focused=detect_focused_ide_id,
    )


def _action_setup_host(args: argparse.Namespace) -> int:
    return doctor_cli.action_setup_host(args)


def _action_manage(args: argparse.Namespace) -> int:
    """Wrapper for manage command with dependency injection."""
    from koru.autopilot.install_manager import (
        collect_install_manager_report,
        format_install_manager_report,
        repair_installation,
    )

    return _manage_action_impl(
        args,
        collect_report_fn=collect_install_manager_report,
        format_report_fn=format_install_manager_report,
        repair_fn=repair_installation,
    )


def _action_install_plugin(args: argparse.Namespace) -> int:
    return install_plugin_cli.action_install_plugin(
        args,
        resolve_target_ide=install_plugin_cli.resolve_plugin_target_ide,
        resolve_editor_bin=install_plugin_cli.resolve_plugin_editor_bin,
        resolve_vsix_path=install_plugin_cli.resolve_plugin_vsix_path,
    )


def _action_install_plugin_jetbrains(args: argparse.Namespace) -> int:
    return install_plugin_cli.action_install_plugin_jetbrains(
        args,
        resolve_plugin_dir=install_plugin_cli.resolve_jetbrains_plugin_dir,
        resolve_gradle=install_plugin_cli.resolve_gradle_bin,
        resolve_artifact=install_plugin_cli.resolve_jetbrains_plugin_artifact,
    )


def _action_handoff(args: argparse.Namespace) -> int:
    """Wrapper for handoff command with dependency injection."""
    from koru.context import build_context, render_markdown_handoff

    return _handoff_action_impl(
        args,
        client_fn=_client,
        build_context_fn=build_context,
        render_markdown_handoff_fn=render_markdown_handoff,
    )


def _action_tail(args: argparse.Namespace) -> int:
    return tail_cli.action_tail(args)


def _action_install_unit(args: argparse.Namespace) -> int:
    return systemd_cli.action_install_unit(
        args,
        resolve_bin=systemd_cli.resolve_koru_bin,
        render=systemd_cli.render_unit,
        resolve_unit_dir=systemd_cli.systemd_user_dir,
    )


_ACTIONS = {
    "daemon": _action_daemon,
    "drive": _action_drive,
    "calibrate": _action_calibrate,
    "session-start": _action_session_start,
    "status": _action_status,
    "shutdown": _action_shutdown,
    "ide-list": _action_ide_list,
    "doctor": _action_doctor,
    "setup-host": _action_setup_host,
    "manage": _action_manage,
    "install-plugin": _action_install_plugin,
    "install-plugin-jetbrains": _action_install_plugin_jetbrains,
    "handoff": _action_handoff,
    "tail": _action_tail,
    "install-unit": _action_install_unit,
    "trace": _action_trace,
}


def autopilot_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    handler = _ACTIONS[args.action]
    return handler(args)


__all__ = ["autopilot_main"]
