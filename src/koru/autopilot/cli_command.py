"""``koru autopilot`` subcommand wiring.

Kept in its own module to keep ``koru.cli`` digestible. The single
public entrypoint is :func:`autopilot_main` which mirrors the
``_task_main`` / ``_scan_main`` style used elsewhere.
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import Any

from koru.autopilot import (
    calibrate_cli,
    daemon_cli,
    doctor_cli,
    install_plugin_cli,
    systemd_cli,
    tail_cli,
)
from koru.autopilot.client import AutopilotClient
from koru.autopilot.ide import (
    detect_focused_ide_id,
    detect_running_ides,
    resolve_drive_target,
)
from koru.autopilot.injector import Injector, InjectorError
from koru.autopilot.utils.client_helpers import call_daemon_method


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


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="koru autopilot",
        description=(
            "Drive an IDE's LLM chat panel from the terminal. "
            "Run `koru autopilot daemon` once in a background terminal, "
            "then `koru autopilot drive '<text>'` from anywhere to type "
            "into the focused IDE."
        ),
    )
    parser.add_argument(
        "--socket",
        type=Path,
        default=None,
        help=(
            "Unix-socket path (default from KORU_AUTOPILOT_SOCKET / "
            "KORU_AUTOPILOT_INSTANCE / XDG_RUNTIME_DIR — see koru autopilot docs)."
        ),
    )
    sub = parser.add_subparsers(dest="action", required=True)

    daemon = sub.add_parser("daemon", help="Run the autopilot broker.")
    daemon.add_argument(
        "--idempotent",
        action="store_true",
        help="If a healthy daemon already runs, exit 0 instead of failing.",
    )
    daemon.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the koru brief on session.ended (default: cwd).",
    )
    handoff_group = daemon.add_mutually_exclusive_group()
    handoff_group.add_argument(
        "--handoff",
        dest="handoff",
        action="store_true",
        default=True,
        help="On session.ended from a plugin, type the koru brief back into the chat (default).",
    )
    handoff_group.add_argument(
        "--no-handoff",
        dest="handoff",
        action="store_false",
        help="Disable auto-handoff; just ack session events.",
    )
    daemon.add_argument(
        "--handoff-cooldown",
        type=float,
        default=2.0,
        help="Seconds to wait after typing before reacting to session.ended (anti-loop).",
    )

    drive = sub.add_parser("drive", help="Type text into the active IDE chat.")
    drive.add_argument(
        "text",
        nargs="*",
        default=[],
        help="Text to type (joined with spaces). Omit when using --prompt.",
    )
    drive.add_argument(
        "--prompt",
        "-p",
        default=None,
        metavar="TEXT",
        help="Full prompt string (alternative to positional words; avoids quoting issues).",
    )
    drive.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help=(
            "Target IDE for keyboard fallback (default: auto). "
            "With --direct and without --os-profile, this is also the OS-injector "
            "profile key in ide-os-injector.json."
        ),
    )
    drive.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Do not press the submit key after typing.",
    )
    drive.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be typed and exit without touching the keyboard.",
    )
    drive.add_argument(
        "--require-plugin",
        action="store_true",
        help=(
            "Require a connected IDE plugin; fail instead of falling back to global "
            "keyboard injection."
        ),
    )
    drive.add_argument(
        "--direct",
        action="store_true",
        help="Bypass the daemon and inject directly via local backends.",
    )
    drive.add_argument(
        "--project",
        type=Path,
        default=None,
        metavar="DIR",
        help=(
            "With --direct, include DIR/.koru/ide-os-injector.json first in OS-injector "
            "profile search (default: cwd-only + home; same order as the daemon when "
            "given --project)."
        ),
    )
    drive.add_argument(
        "--os-profile",
        default=None,
        metavar="IDE",
        help=(
            "With --direct, force OS-injector profile id in ide-os-injector.json "
            "(e.g. windsurf). When unset, the profile key matches --ide (including auto-detect)."
        ),
    )
    drive.add_argument(
        "--delay-seconds",
        type=float,
        default=0.0,
        metavar="SECONDS",
        help=("With --direct, wait before injection so you can focus the target IDE window."),
    )

    calibrate = sub.add_parser(
        "calibrate",
        help=(
            "Capture chat input coordinates after a short delay and save an OS-injector profile."
        ),
    )
    calibrate.add_argument(
        "--ide",
        default="auto",
        metavar="IDE",
        help=(
            "Profile id (windsurf, vscode, cursor, …). Default auto: same detection as "
            "`drive --direct --ide auto` (focused IDE when known, else first running)."
        ),
    )
    calibrate.add_argument(
        "--delay-seconds",
        type=float,
        default=5.0,
        metavar="SECONDS",
        help="Seconds to wait before capturing the mouse position (default: 5).",
    )
    calibrate.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional ide-os-injector.json path (default: ~/.koru/ide-os-injector.json).",
    )
    calibrate.add_argument(
        "--prompt",
        default=None,
        metavar="TEXT",
        help="Optional smoke prompt injected immediately after saving the profile.",
    )

    session_start = sub.add_parser(
        "session-start",
        help="Calibrate one or more IDE profiles in sequence and optionally send a smoke prompt.",
    )
    session_start.add_argument(
        "--ides",
        default="auto",
        metavar="LIST",
        help="Comma-separated ids or 'auto' for all running IDE ids (default: auto).",
    )
    session_start.add_argument(
        "--delay-seconds",
        type=float,
        default=6.0,
        metavar="SECONDS",
        help="Delay before each capture (default: 6).",
    )
    session_start.add_argument(
        "--config",
        type=Path,
        default=None,
        metavar="FILE",
        help="Optional ide-os-injector.json path (default: ~/.koru/ide-os-injector.json).",
    )
    session_start.add_argument(
        "--prompt",
        default=None,
        metavar="TEXT",
        help="Optional smoke prompt after each profile is saved.",
    )

    status = sub.add_parser("status", help="Print daemon health + connected plugins.")
    status.add_argument(
        "--json",
        action="store_true",
        help=argparse.SUPPRESS,
    )
    sub.add_parser("shutdown", help="Ask a running daemon to stop.")

    sub.add_parser("ide-list", help="List currently running IDEs (process scan).")
    doctor = sub.add_parser("doctor", help="Report which injection backends are available.")
    doctor.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    doctor.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Show guided remediation and next commands (including optional package auto-install)."
        ),
    )

    setup_host = sub.add_parser(
        "setup-host",
        help=(
            "Probe injector tools, list apt install hints, and optional apt install "
            "(Debian/Ubuntu). Separates automated steps from human (uinput, IDE plugin)."
        ),
    )
    setup_host.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    setup_host.add_argument(
        "--install",
        action="store_true",
        help="Run sudo apt-get install -y for missing xdotool/wtype/ydotool (requires apt).",
    )
    setup_host.add_argument(
        "--dry-run",
        dest="install_dry_run",
        action="store_true",
        help="With --install, print the apt-get command but do not run it.",
    )

    manage = sub.add_parser(
        "manage",
        help=(
            "Inventory and repair the autopilot installation: koru binary, daemon, "
            "socket, IDE plugin and VSIX version."
        ),
    )
    manage.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "pycharm"),
        help="IDE to inspect or repair (default: auto-detect).",
    )
    manage.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    manage.add_argument(
        "--fix",
        action="store_true",
        help=(
            "Best-effort repair: install/reassert the current plugin and stop the daemon "
            "so the IDE can reconnect cleanly."
        ),
    )
    manage.add_argument(
        "--dry-run",
        action="store_true",
        help="With --fix, show the planned plugin install without executing it.",
    )

    install_plugin = sub.add_parser(
        "install-plugin",
        help=(
            "Install the koru autopilot editor extension for the current IDE "
            "(auto-detect from terminal/focus/running IDEs)."
        ),
    )
    install_plugin.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "pycharm"),
        help="Target editor CLI (default: auto-detect current IDE).",
    )
    install_plugin.add_argument(
        "--vsix",
        type=Path,
        default=None,
        help=(
            "Path to .vsix package (default: newest plugins/koru-autopilot-vscode/"
            "koru-autopilot-*.vsix)."
        ),
    )
    install_plugin.add_argument(
        "--force",
        action="store_true",
        help="Pass --force to the editor extension installer.",
    )
    install_plugin.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved install command without executing it.",
    )
    install_plugin.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )

    install_plugin_jetbrains = sub.add_parser(
        "install-plugin-jetbrains",
        help=(
            "Build the JetBrains plugin package (ZIP) and print installation hint "
            "for PyCharm/IntelliJ."
        ),
    )
    install_plugin_jetbrains.add_argument(
        "--plugin-dir",
        type=Path,
        default=None,
        help=(
            "Path to plugins/koru-autopilot-jetbrains directory "
            "(default: repository copy)."
        ),
    )
    install_plugin_jetbrains.add_argument(
        "--gradle-bin",
        default="gradle",
        help="Gradle executable to use (default: gradle).",
    )
    install_plugin_jetbrains.add_argument(
        "--gradle-task",
        default="buildPlugin",
        help="Gradle task used to build plugin package (default: buildPlugin).",
    )
    install_plugin_jetbrains.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the resolved Gradle command without executing it.",
    )
    install_plugin_jetbrains.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )

    handoff = sub.add_parser(
        "handoff",
        help="Build the koru brief for --project and type it into the IDE chat.",
    )
    handoff.add_argument(
        "--project",
        type=Path,
        default=Path.cwd(),
        help="Project root used to build the brief (default: cwd).",
    )
    handoff.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help="Target IDE (default: auto-detect the focused one).",
    )
    handoff.add_argument(
        "--no-submit",
        dest="submit",
        action="store_false",
        help="Type the brief but do not press the submit key.",
    )
    handoff.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the brief and exit; do not contact the daemon.",
    )
    handoff.add_argument(
        "--require-plugin",
        action="store_true",
        help=(
            "Require a connected IDE plugin; fail instead of falling back to global "
            "keyboard injection."
        ),
    )

    install_unit = sub.add_parser(
        "install-unit",
        help="Install the systemd --user service unit (P2.6).",
    )
    install_unit.add_argument(
        "--dest",
        type=Path,
        default=None,
        help=(
            "Override destination (default: $XDG_CONFIG_HOME/systemd/user/koru-autopilot.service)."
        ),
    )
    install_unit.add_argument(
        "--force",
        action="store_true",
        help="Overwrite an existing unit file.",
    )
    install_unit.add_argument(
        "--print",
        dest="print_only",
        action="store_true",
        help="Print the rendered unit to stdout instead of writing.",
    )

    tail = sub.add_parser(
        "tail",
        help="Pretty-print the persistent audit log (P2.7/P2.8).",
    )
    tail.add_argument(
        "-n",
        "--lines",
        type=int,
        default=20,
        help="Number of trailing entries to show (default: 20).",
    )
    tail.add_argument(
        "--log",
        type=Path,
        default=None,
        help=f"Log file path (default: {tail_cli.default_log_path()}).",
    )
    tail.add_argument(
        "--format",
        dest="output_format",
        choices=("text", "json"),
        default="text",
        help="Output format (default: text).",
    )
    return parser


def _client(args: argparse.Namespace) -> AutopilotClient:
    return AutopilotClient(socket_path=args.socket)


# ----- action handlers ------------------------------------------------------


_action_daemon = daemon_cli.action_daemon


def _auto_direct_fallback_enabled() -> bool:
    raw = os.environ.get("KORU_AUTOPILOT_DRIVE_AUTO_DIRECT", "").strip().lower()
    if not raw:
        return True
    return raw not in {"0", "false", "no", "off"}


def _should_fallback_to_direct(args: argparse.Namespace, reply: dict[str, Any]) -> bool:
    if args.require_plugin:
        return False
    if not _auto_direct_fallback_enabled():
        return False
    if bool(reply.get("ok", True)):
        return False
    message = str(reply.get("message") or "").lower()
    if "chat input is not focused/open" in message:
        return True
    return bool(reply.get("opened") is False and reply.get("submitted") is False)


def _print_drive_delay_message(delay_seconds: float) -> None:
    """Print delay message before direct injection."""
    print(
        f"koru autopilot drive: waiting {delay_seconds:.1f}s "
        "before direct injection (focus the target IDE now)...",
        file=sys.stderr,
    )
    time.sleep(delay_seconds)


def _handle_os_injector_fallback(
    args: argparse.Namespace, profile_id: str, injector: Injector
) -> tuple[int, dict[str, Any] | None]:
    """Handle fallback when OS injector is unavailable."""
    if args.os_profile:
        print(
            "koru autopilot drive: requested --os-profile but os-injector path is unavailable. "
            "Run `koru autopilot calibrate --ide <id>` first, or install xdotool.",
            file=sys.stderr,
        )
        return 2, None
    if injector.session == "wayland":
        print(
            "koru autopilot drive: no OS-injector profile for "
            f"{profile_id!r}; using ydotool/wtype (keystrokes go only to the "
            "currently focused window — click the IDE chat first, or run "
            "`koru autopilot calibrate --ide auto`).",
            file=sys.stderr,
        )
    return None, None


def _run_direct_drive(
    args: argparse.Namespace,
    text: str,
    *,
    emit_payload: bool = True,
) -> tuple[int, dict[str, Any] | None]:
    from koru.autopilot import os_injector as oi

    injector = Injector()
    target_id, profile_id, selection = resolve_drive_target(
        args.ide,
        args.os_profile,
        project=args.project,
    )
    raw_ide = (args.ide or "").strip().lower()
    if raw_ide in ("", "auto") and not (args.os_profile or "").strip():
        print(
            f"koru autopilot drive: auto-selected {profile_id} ({selection})",
            file=sys.stderr,
        )

    try:
        if float(args.delay_seconds) > 0:
            _print_drive_delay_message(float(args.delay_seconds))
        os_res = oi.try_drive_with_profile(
            tool_id=profile_id,
            text=text,
            submit=args.submit,
            project=args.project,
            cli_dry_run=args.dry_run,
        )
        if os_res is not None:
            if emit_payload:
                print(json.dumps(os_res, indent=2, sort_keys=True))
            return 0, os_res
        fallback_rc, _ = _handle_os_injector_fallback(args, profile_id, injector)
        if fallback_rc is not None:
            return fallback_rc, None
        result = injector.type_text(
            text,
            ide=target_id,
            submit=args.submit,
            dry_run=args.dry_run,
        )
    except oi.OsInjectorError as exc:
        if args.os_profile:
            print(
                f"koru autopilot drive: os-injector failed for requested profile "
                f"{profile_id!r}: {exc}",
                file=sys.stderr,
            )
            return 1, None
        print(
            f"koru autopilot drive: os-injector failed; falling back to keyboard injector: {exc}",
            file=sys.stderr,
        )
        try:
            result = injector.type_text(
                text,
                ide=target_id,
                submit=args.submit,
                dry_run=args.dry_run,
            )
        except InjectorError as inner_exc:
            print(f"koru autopilot drive: {inner_exc}", file=sys.stderr)
            return 1, None
    except InjectorError as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1, None

    payload = result.to_dict()
    if emit_payload:
        print(json.dumps(payload, indent=2, sort_keys=True))
    return 0, payload


def _action_drive(args: argparse.Namespace) -> int:
    text = str(args.prompt).strip() if args.prompt is not None else " ".join(args.text).strip()
    if not text:
        print(
            "koru autopilot drive: missing text — pass words after `drive`, "
            "or use --prompt / -p '...'",
            file=sys.stderr,
        )
        return 2
    if args.direct:
        rc, _payload = _run_direct_drive(args, text, emit_payload=True)
        return rc
    client = _client(args)
    if not client.is_running():
        print(
            "koru autopilot drive: daemon not running. "
            "Start it with `koru autopilot daemon`, or pass --direct "
            "to inject from this terminal.",
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


def _action_status(args: argparse.Namespace) -> int:
    client = _client(args)
    return call_daemon_method(client, "status", "koru autopilot status", not_running_return_code=1)


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
}


def autopilot_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    handler = _ACTIONS[args.action]
    return handler(args)


__all__ = ["autopilot_main"]
