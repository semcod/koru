"""``koru autopilot`` subcommand wiring.

Kept in its own module to keep ``koru.cli`` digestible. The single
public entrypoint is :func:`autopilot_main` which mirrors the
``_task_main`` / ``_scan_main`` style used elsewhere.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from . import default_socket_path
from .client import AutopilotClient
from .daemon import AutopilotDaemon
from .ide import detect_running_ides
from .injector import Injector, InjectorError


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
        help=f"Unix-socket path (default: {default_socket_path()}).",
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
    drive.add_argument("text", nargs="+", help="Text to type. Multiple args are joined with spaces.")
    drive.add_argument(
        "--ide",
        default="auto",
        choices=("auto", "windsurf", "vscode", "cursor", "jetbrains", "zed"),
        help="Target IDE (default: auto-detect the focused one).",
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
        "--direct",
        action="store_true",
        help="Bypass the daemon and inject directly via local backends.",
    )

    sub.add_parser("status", help="Print daemon health + connected plugins.")
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
    return parser


def _client(args: argparse.Namespace) -> AutopilotClient:
    return AutopilotClient(socket_path=args.socket)


# ----- action handlers ------------------------------------------------------

def _action_daemon(args: argparse.Namespace) -> int:
    socket_path = args.socket or default_socket_path()
    if args.idempotent:
        probe = AutopilotClient(socket_path=socket_path, timeout=0.5)
        if probe.is_running():
            print(f"koru autopilot: daemon already running on {socket_path}")
            return 0
    project = args.project.resolve() if args.handoff else None
    daemon = AutopilotDaemon(
        socket_path=socket_path,
        log=print,
        project=project,
        handoff_cooldown=args.handoff_cooldown,
    )
    try:
        daemon.start()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot daemon: {exc}", file=sys.stderr)
        return 1
    if args.handoff:
        print(f"koru autopilot daemon: handoff enabled for project={project}")
    else:
        print("koru autopilot daemon: handoff disabled (--no-handoff)")
    try:
        daemon.serve_forever()
    except KeyboardInterrupt:
        print()
        print("koru autopilot daemon: interrupted")
    return 0


def _action_drive(args: argparse.Namespace) -> int:
    text = " ".join(args.text)
    if args.direct:
        injector = Injector()
        try:
            result = injector.type_text(
                text,
                ide="default" if args.ide == "auto" else args.ide,
                submit=args.submit,
                dry_run=args.dry_run,
            )
        except InjectorError as exc:
            print(f"koru autopilot drive: {exc}", file=sys.stderr)
            return 1
        print(json.dumps(result.to_dict(), indent=2, sort_keys=True))
        return 0
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
        reply = client.drive(text, submit=args.submit, ide=args.ide)
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot drive: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(reply, indent=2, sort_keys=True))
    return 0 if reply.get("ok", True) else 1


def _action_status(args: argparse.Namespace) -> int:
    client = _client(args)
    if not client.is_running():
        print("koru autopilot: daemon is NOT running")
        return 1
    try:
        info = client.status()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot status: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


def _action_shutdown(args: argparse.Namespace) -> int:
    client = _client(args)
    if not client.is_running():
        print("koru autopilot: daemon is not running")
        return 0
    try:
        info = client.shutdown()
    except (OSError, RuntimeError) as exc:
        print(f"koru autopilot shutdown: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(info, indent=2, sort_keys=True))
    return 0


def _action_ide_list(_args: argparse.Namespace) -> int:
    ides = detect_running_ides()
    if not ides:
        print("koru autopilot: no IDE processes detected")
        return 0
    for ide in ides:
        print(f"  {ide.id:<10} pid={ide.pid:<7} {ide.label}  ({ide.exe})")
    return 0


def _action_doctor(args: argparse.Namespace) -> int:
    injector = Injector()
    statuses = injector.probe()
    selected = injector.select_backend()
    if args.output_format == "json":
        print(json.dumps(
            {
                "session": injector.session,
                "selected_backend": selected,
                "backends": [s.to_dict() for s in statuses],
                "ides": [i.to_dict() for i in detect_running_ides()],
            },
            indent=2, sort_keys=True,
        ))
        return 0
    print(f"session: {injector.session or 'unknown'}")
    print(f"selected backend: {selected or '(none — install xdotool/wtype/ydotool)'}")
    print("backends:")
    for s in statuses:
        mark = "✓" if s.available else "✗"
        print(f"  {mark} {s.name:<10} {s.reason}")
    ides = detect_running_ides()
    print(f"running IDEs ({len(ides)}):")
    for ide in ides:
        print(f"  · {ide.label} (pid={ide.pid})")
    return 0 if selected else 1


_ACTIONS = {
    "daemon": _action_daemon,
    "drive": _action_drive,
    "status": _action_status,
    "shutdown": _action_shutdown,
    "ide-list": _action_ide_list,
    "doctor": _action_doctor,
}


def autopilot_main(argv: list[str]) -> int:
    args = _build_parser().parse_args(argv)
    handler = _ACTIONS[args.action]
    return handler(args)


__all__ = ["autopilot_main"]
