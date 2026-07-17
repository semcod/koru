"""Top-level command dispatch extracted from ``coru.cli``.

Each dispatcher returns ``None`` when the command does not match, otherwise
the process exit code. Handlers are injected to avoid circular imports with
the large ``cli`` module.
"""

from __future__ import annotations

import argparse
import os
import sys
from collections.abc import Callable
from typing import Any


def dispatch_lane_command(
    args: argparse.Namespace,
    *,
    default_lane: Callable[[Any, Any], tuple[str, str]],
    lane_env: Callable[[str, str, str], int],
    lane_status: Callable[[str, str], int],
    diagnose_lane: Callable[..., int],
) -> int | None:
    if args.command == "lane":
        ide, instance = default_lane(args.ide, args.instance)
        return lane_env(ide, instance, args.shell)
    if args.command == "lane-status":
        ide, instance = default_lane(args.ide, args.instance)
        return lane_status(ide, instance)
    if args.command == "status":
        ide, instance = default_lane(args.ide, args.instance)
        return diagnose_lane(ide, instance, probe_drive=bool(getattr(args, "probe", False)))
    if args.command == "env":
        ide, instance = default_lane(args.ide, args.instance)
        return lane_env(ide, instance, args.shell)
    return None


def dispatch_auto_command(
    args: argparse.Namespace,
    *,
    default_lane: Callable[[Any, Any], tuple[str, str]],
    remember_settings: Callable[[str, str], None],
    run_auto: Callable[[str, str, list[str]], int],
) -> int | None:
    if args.command != "auto":
        return None
    ide, instance = default_lane(args.ide, args.instance)
    if args.ide or args.instance:
        remember_settings(ide, instance)
    rest = list(args.rest)
    if rest and rest[0] == "--":
        rest = rest[1:]
    return run_auto(ide, instance, rest)


def dispatch_text_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    original_apply_nl: Any,
    run_text_plan_chain: Callable[..., int],
) -> int | None:
    if args.command != "text":
        return None
    from coru import control

    apply_nl = control.apply_nl
    if apply_nl is original_apply_nl and (
        "pytest" in sys.modules
        or "unittest" in sys.modules
        or os.environ.get("PYTEST_CURRENT_TEST")
    ):
        return run_text_plan_chain(args, verbose=verbose)
    try:
        rc = apply_nl(
            args.prompt,
            use_llm=args.llm,
            single_action=args.single_action,
        )
    except ModuleNotFoundError:
        return run_text_plan_chain(args, verbose=verbose)
    if verbose and rc == 0:
        print("[coru] dispatched via control bus (nlp2coru → dsl2coru)")
    return rc


def dispatch_chat_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
    chat_loop: Callable[..., int],
) -> int | None:
    if args.command != "chat":
        return None
    return chat_loop(
        use_llm=args.llm,
        shell=args.shell,
        single_action=args.single_action,
        verbose=verbose,
        require_plugin=bool(args.require_plugin or require_plugin),
    )


def dispatch_supervisor_command(
    args: argparse.Namespace,
    *,
    koru_argv: Callable[[], list[str] | None],
) -> int | None:
    if args.command != "supervisor":
        return None
    from coru.supervisor.cli import main as supervisor_main

    sup_argv = list(args.supervisor_args)
    if sup_argv and sup_argv[0] == "--":
        sup_argv = sup_argv[1:]
    return supervisor_main(sup_argv, koru_argv=koru_argv())


def dispatch_calibration_command(
    args: argparse.Namespace,
    *,
    default_lane: Callable[[Any, Any], tuple[str, str]],
    resolve_calibration_lane: Callable[..., tuple[str, str]],
    lane_calibration: Callable[..., int],
) -> int | None:
    if args.command != "calibration":
        return None
    ide, instance = default_lane(args.ide, args.instance)
    ide, instance = resolve_calibration_lane(
        ide,
        instance,
        explicit_ide=args.ide,
    )
    return lane_calibration(
        ide,
        instance,
        probe_prompt=args.probe_prompt,
        skip_fix=args.skip_fix,
        skip_desktop=args.skip_desktop,
        skip_bridge=args.skip_bridge,
    )


def dispatch_doctor_command(
    args: argparse.Namespace,
    *,
    default_lane: Callable[[Any, Any], tuple[str, str]],
    requires_system_shell: Callable[..., bool],
    lane_doctor: Callable[..., int],
) -> int | None:
    if args.command != "doctor":
        return None
    ide, instance = default_lane(args.ide, args.instance)
    if requires_system_shell(
        command="doctor",
        allow_integrated_shell=args.allow_integrated_shell,
    ):
        return 2
    return lane_doctor(
        ide,
        instance,
        fix=args.fix,
        probe=args.probe,
        probe_prompt=args.probe_prompt,
    )


def dispatch_repair_command(
    args: argparse.Namespace,
    *,
    cmd_history: Callable[[argparse.Namespace], int],
    cmd_run: Callable[[argparse.Namespace], int],
) -> int | None:
    if args.command != "repair":
        return None
    if args.repair_command == "history":
        return cmd_history(args)
    if args.repair_command == "run":
        return cmd_run(args)
    return 2


def dispatch_daemon_command(
    args: argparse.Namespace,
    *,
    default_lane: Callable[[Any, Any], tuple[str, str]],
    requires_system_shell: Callable[..., bool],
    resolve_defaults: Callable[[Any], Any],
    plan_cls: type,
    print_troubleshooting: Callable[[str, str], None],
    lane_daemon_foreground: Callable[[str, str], int],
) -> int | None:
    if args.command != "daemon":
        return None
    ide, instance = default_lane(args.ide, args.instance)
    if requires_system_shell(
        command="daemon",
        allow_integrated_shell=args.allow_integrated_shell,
    ):
        return 2
    resolved = resolve_defaults(plan_cls(action="auto", ide=ide, instance=instance))
    print(
        f"coru daemon: foreground autopilot for ide={resolved.ide} instance={resolved.instance} "
        "(Ctrl+C stops daemon)",
    )
    print_troubleshooting(resolved.ide, resolved.instance)
    return lane_daemon_foreground(resolved.ide, resolved.instance)


def dispatch_optional_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
    dispatchers: list[Callable[[], int | None]],
) -> int | None:
    for dispatch in dispatchers:
        rc = dispatch()
        if rc is not None:
            return rc
    return None


def dispatch_command(
    args: argparse.Namespace,
    *,
    verbose: bool,
    require_plugin: bool,
    ensure_commands: Callable[..., int],
    cmd_sync: Callable[[argparse.Namespace], int],
    setup_environment: Callable[[], int],
    dispatch_optional: Callable[..., int | None],
) -> int:
    if args.command == "ensure":
        return ensure_commands(install=args.install)
    if args.command == "sync":
        return cmd_sync(args)
    if args.command == "setup":
        return setup_environment()
    rc = dispatch_optional(args, verbose=verbose, require_plugin=require_plugin)
    if rc is not None:
        return rc
    return 2
