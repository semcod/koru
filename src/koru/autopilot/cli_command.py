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
    text = str(args.prompt).strip() if args.prompt is not None else " ".join(args.text).strip()
    if not text:
        print(
            "koru autopilot drive: missing text — pass words after `drive`, "
            "or use --prompt / -p '...'",
            file=sys.stderr,
        )
        return 2
    project = getattr(args, "project", None) or Path.cwd()
    shell_command(
        project,
        corr="cli-drive",
        argv=_drive_command_argv(args, text),
        cwd=str(project.resolve()),
        actor="operator",
        replayable=not args.dry_run,
    )
    if args.direct:
        rc, _payload = _run_direct_drive(args, text, emit_payload=True)
        return rc
    client = _client(args)
    if not client.is_running():
        print(
            "koru autopilot drive: daemon not running. "
            f"{_daemon_start_hint(args)}",
            file=sys.stderr,
        )
        return 2
    if args.dry_run:
        print(f"[dry-run] would send {len(text)} chars to daemon ide={args.ide}")
        return 0
    try:
        reply = client.drive(
            text,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1
    if _should_fallback_to_direct(args, reply):
        print(
            "koru autopilot drive: daemon could not open/focus chat input; "
            "falling back to local --direct injection",
            file=sys.stderr,
        )
        rc, direct_payload = _run_direct_drive(args, text, emit_payload=False)
        if direct_payload is None:
            print(json.dumps(reply, indent=2, sort_keys=True))
            return 1
        direct_payload = dict(direct_payload)
        direct_payload["daemon_fallback"] = {
            "ok": reply.get("ok"),
            "message": reply.get("message"),
            "opened": reply.get("opened"),
            "submitted": reply.get("submitted"),
        }
        print(json.dumps(direct_payload, indent=2, sort_keys=True))
        return rc
    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


def _drive_command_argv(args: argparse.Namespace, text: str) -> list[str]:
    argv = ["koru", "autopilot", "drive", "--ide", str(args.ide)]
    if not args.submit:
        argv.append("--no-submit")
    if args.require_plugin:
        argv.append("--require-plugin")
    if args.direct:
        argv.append("--direct")
    if args.dry_run:
        argv.append("--dry-run")
    if args.os_profile:
        argv.extend(["--os-profile", str(args.os_profile)])
    if args.delay_seconds:
        argv.extend(["--delay-seconds", str(args.delay_seconds)])
    argv.extend(["--prompt", text])
    return argv


def _action_status(args: argparse.Namespace) -> int:
    client = _client(args)
    if not client.is_running():
        print(f"koru autopilot: daemon is NOT running on {client.socket_path}")
        print(f"hint: {_daemon_start_hint(args)}")
        return 1
    try:
        info = client.status()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot status: {exc}", file=sys.stderr)
        return 1
    import json

    print(json.dumps(info, indent=2, sort_keys=True))
    plugins = info.get("plugins") if isinstance(info, dict) else []
    if args.explain and isinstance(plugins, list) and not plugins:
        from koru.ide_adapters.bridge import evaluate_bridge, format_bridge_text
        from koruide.plugin_installer import resolve_target_ide

        instance = os.environ.get("KORU_AUTOPILOT_INSTANCE", "").strip()
        ide = normalize_ide_id(instance) if instance else resolve_target_ide("auto")
        ide = ide or "cursor"
        socket = getattr(client, "socket_path", None)
        if socket is not None:
            bridge = evaluate_bridge(
                ide=ide,
                socket_path=socket,
                project=getattr(args, "project", Path.cwd()),
                plugins=plugins,
            )
            print("\n--- explain ---", file=sys.stderr)
            print(format_bridge_text(bridge, explain=True), file=sys.stderr)
            print(f"hint: koru ide doctor --ide {ide} --fix", file=sys.stderr)
    return 0


def _action_shutdown(args: argparse.Namespace) -> int:
    return daemon_cli.action_shutdown(args, client_fn=_client)


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
    from koru.autopilot.install_manager import (
        collect_install_manager_report,
        format_install_manager_report,
        repair_installation,
    )

    report = (
        repair_installation(ide=args.ide, socket_path=args.socket, dry_run=args.dry_run)
        if args.fix
        else collect_install_manager_report(ide=args.ide, socket_path=args.socket)
    )
    if args.output_format == "json":
        print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    else:
        print(format_install_manager_report(report))
    return 0 if report.ok else 1


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


def _build_brief(project: Path) -> str:
    """Build the koru markdown brief for ``project``.

    Imported lazily so ``autopilot doctor`` / ``ide-list`` don't drag
    in the heavy ``context`` stack on every CLI invocation.
    """
    from koru.context import build_context, render_markdown_handoff

    ctx = build_context(project=project)
    return render_markdown_handoff(ctx)


def _action_handoff(args: argparse.Namespace) -> int:
    """P2.5: build the koru brief and pipe it through ``drive``."""
    project = args.project.resolve()
    try:
        brief = _build_brief(project)
    except Exception as exc:  # pragma: no cover — surfaces context errors
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        return 1
    if not brief.strip():
        print("koru autopilot handoff: empty brief, refusing to drive", file=sys.stderr)
        return 1
    if args.dry_run:
        print(brief)
        return 0
    client = _client(args)
    if not client.is_running():
        print(
            "koru autopilot handoff: daemon not running. Start it with `koru autopilot daemon`.",
            file=sys.stderr,
        )
        return 2
    try:
        reply = client.drive(
            brief,
            submit=args.submit,
            ide=args.ide,
            require_plugin=args.require_plugin,
        )
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot handoff: {exc}", file=sys.stderr)
        return 1
    summary = {
        "ok": reply.get("ok", False),
        "chars": len(brief),
        "ide": args.ide,
        "submit": args.submit,
        "backend": reply.get("backend") or ("plugin" if reply.get("delivered") else "?"),
    }
    print(json.dumps(summary, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


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
